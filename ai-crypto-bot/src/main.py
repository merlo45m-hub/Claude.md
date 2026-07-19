from __future__ import annotations

import asyncio
import logging
import time

import pandas as pd
from datetime import datetime, timezone

from src.alerts import create_alert_channels
from src.config import load_config
from src.data.store import DataStore
from src.exchange.client import ExchangeClient
from src.persistence import SQLitePersistence
from src.strategy.factory import StrategyFactory
from src.trading.paper import PaperTrader

logger = logging.getLogger(__name__)


def _trade_message(symbol: str, side: str, price: float, pnl: float | None = None, confidence: int | None = None) -> str:
    base = f"<b>{symbol}</b> {side.upper()} @ ${price:.2f}"
    if confidence is not None:
        base += f" [conf={confidence}]"
    if pnl is not None:
        emoji = "\U0001f7e2" if pnl >= 0 else "\U0001f534"
        base += f" | PnL: {emoji} ${pnl:.2f}"
    return base


def _compute_equity(trader: PaperTrader, prices: dict[str, float]) -> float:
    equity = trader.balance
    for symbol, pos in trader.positions.items():
        price = prices.get(symbol)
        if price is None:
            continue
        if pos.direction == "long":
            equity += pos.size * price
        else:
            equity -= pos.size * price
    return equity


async def run_cycle(
    config,
    exchange: ExchangeClient,
    store: DataStore,
    strategy,
    trader: PaperTrader,
    alert_channels: list,
    persistence: SQLitePersistence | None,
) -> list[dict]:
    prices: dict[str, float] = {}
    signals: list[dict] = []
    last_alert: dict[str, float] = {}

    # ---- Multi-timeframe: fetch higher TF data for trend bias ----
    tf = config.trading.timeframe
    higher_tf = config.trading.higher_tf
    trend_bias_cache: dict[str, str] = {}
    regime_cache: dict[str, str] = {}
    atr_cache: dict[str, float] = {}

    for symbol in config.trading.symbols:
        try:
            # Lower timeframe for signals
            df = await exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200)
            if df is None or df.empty:
                logger.warning("No data for %s", symbol)
                continue
            store.set(symbol, df)

            current_price = float(df["close"].iloc[-1])
            prices[symbol] = current_price
            if persistence:
                row = df.iloc[-1]
                ts = row.name
                if isinstance(ts, pd.Timestamp):
                    ts = ts.isoformat()
                persistence.save_ohlc(symbol, {
                    "timestamp": ts,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                })

            # Higher timeframe for trend bias
            if higher_tf and higher_tf != tf:
                df_higher = await exchange.fetch_ohlcv(
                    symbol, timeframe=higher_tf, limit=config.trading.higher_tf_limit
                )
                if df_higher is not None and not df_higher.empty:
                    trend_bias = strategy.get_trend_bias(df_higher)
                    trend_bias_cache[symbol] = trend_bias
                else:
                    trend_bias_cache[symbol] = "neutral"
            else:
                trend_bias_cache[symbol] = "neutral"

            # Regime detection (on trading timeframe)
            regime = strategy.get_regime(df)
            regime_cache[symbol] = regime

            # ATR for position sizing
            atr = strategy.get_current_atr(df)
            if atr > 0:
                atr_cache[symbol] = atr

        except Exception:
            logger.warning("Failed to fetch data for %s", symbol, exc_info=True)
            continue

    # ---- Signal generation & trade execution ----
    for symbol in config.trading.symbols:
        df = store.get(symbol)
        if df is None or df.empty:
            continue

        current_price = prices.get(symbol)
        if current_price is None:
            continue

        try:
            signal = strategy.evaluate(df)
            confidence = 0
            signals.append({
                "symbol": symbol, "signal": signal,
                "price": current_price, "confidence": confidence,
            })

            # Multi-timeframe filter: skip signals against the higher TF trend
            trend_bias = trend_bias_cache.get(symbol, "neutral")
            regime = regime_cache.get(symbol, "ranging")
            if signal == "buy" and trend_bias == "bearish":
                logger.debug("%s: skipping buy (HTF bias=bearish)", symbol)
                continue
            if signal == "sell" and trend_bias == "bullish":
                logger.debug("%s: skipping sell (HTF bias=bullish)", symbol)
                continue

            # Regime filter: reduce position aggressiveness in ranging markets
            if regime == "ranging" and signal != "hold":
                logger.debug("%s: %s in ranging market — reducing aggression", symbol, signal)

            # Debounce alerts
            now = time.time()
            last = last_alert.get(symbol, 0)
            if signal != "hold" and now - last < 120:
                logger.debug("%s: %s debounced", symbol, signal)
                continue

            if signal != "hold":
                atr = atr_cache.get(symbol)
                if trader.execute(symbol, signal, atr=atr):
                    logger.info("%s: %s executed (conf=%d, regime=%s, bias=%s)",
                                symbol, signal.upper(), confidence, regime, trend_bias)
                    msg = _trade_message(symbol, signal, current_price, confidence=confidence)
                    for ch in alert_channels:
                        await ch.safe_send(msg)
                    if persistence:
                        persistence.save_alert_log(msg)
                    last_alert[symbol] = now
                else:
                    logger.debug("%s: %s skipped", symbol, signal.upper())
        except Exception:
            logger.warning("Failed to process %s", symbol, exc_info=True)

    # Stop-loss / take-profit checks
    for symbol in list(trader.positions.keys()):
        if symbol in prices:
            current_price = prices[symbol]
        else:
            price_df = store.get(symbol)
            if price_df is None or price_df.empty:
                continue
            current_price = float(price_df["close"].iloc[-1])
            prices[symbol] = current_price
        action = trader.check_stop_loss_take_profit(symbol, current_price)
        if action:
            atr = atr_cache.get(symbol)
            trader.execute(symbol, action, atr=atr)
            logger.info("%s: stop/target triggered — %s", symbol, action)
            msg = _trade_message(symbol, action, current_price)
            for ch in alert_channels:
                await ch.safe_send(msg)
            if persistence:
                persistence.save_alert_log(msg)

    if persistence and prices:
        persistence.save_prices(prices)
        for sym, pr in prices.items():
            persistence.save_price_snapshot(sym, pr)

    if persistence:
        equity = _compute_equity(trader, prices)
        persistence.save_equity_snapshot(equity, trader.balance)

    return signals


async def main() -> None:
    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.info("=" * 60)
    logger.info("AI CRYPTO BOT — AGGRESSIVE MODE")
    logger.info("Exchange: %s | Symbols: %d | Strategy: %s",
                config.exchange.name, len(config.trading.symbols), config.strategy.type)
    logger.info("Capital: $%.2f | Max positions: %d | Interval: %ds",
                config.trading.initial_capital, config.trading.max_open_positions,
                config.trading.loop_interval_seconds)
    logger.info("TF: %s | HTF: %s | ATR stop: %.1fx | R:R = 1:%.1f",
                config.trading.timeframe, config.trading.higher_tf,
                config.trading.atr_multiplier, config.trading.reward_ratio)
    logger.info("Risk: %.1f%%/trade | Regime ADX: %d | EMA: %d/%d",
                config.trading.risk_per_trade_pct * 100,
                config.strategy.adx_trend_threshold,
                config.strategy.fast_period,
                config.strategy.slow_period)
    logger.info("Scale-in: %s (lvl=%d, spacing=%.1f%%)",
                "ON" if config.trading.scale_in_enabled else "OFF",
                config.trading.scale_in_levels, config.trading.scale_in_spacing_pct)
    logger.info("=" * 60)

    alert_channels = create_alert_channels(config)
    if alert_channels:
        logger.info("Alert channels: %d", len(alert_channels))

    store = DataStore()
    exchange = ExchangeClient(config.exchange, timeframe=config.trading.timeframe)
    strategy = StrategyFactory.create(config.strategy.type, config.strategy)

    persistence = None
    if config.trading.db_path:
        import hashlib
        from datetime import date
        config_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:16]
        persistence = SQLitePersistence(config.trading.db_path, config_hash=config_hash)
        persistence.save_initial_capital(config.trading.initial_capital)
        # Init challenge tracking if not already set
        ch = persistence.load_challenge_state()
        if not ch.get('start'):
            persistence.save_challenge_state(0, 0, date.today().isoformat(), config.trading.challenge_target)
            logger.info("Challenge: $%.0f → $%.0f in %d days", config.trading.initial_capital,
                        config.trading.challenge_target, config.trading.challenge_days)
        else:
            logger.info("Challenge: restart #%d, failure #%d, started %s",
                        ch['restarts'], ch['failures'], ch.get('start', '?'))
        logger.info("DB: %s", config.trading.db_path)

    trader = PaperTrader(config.trading, store, persistence)

    if config.web.enabled:
        logger.info("Web: http://%s:%d", config.web.host, config.web.port)

    try:
        interval = config.trading.loop_interval_seconds
        if interval > 0:
            logger.info("Continuous mode — every %ds", interval)
            cycle_count = 0
            while True:
                start = time.monotonic()
                cycle_count += 1
                signals = await run_cycle(config, exchange, store, strategy, trader, alert_channels, persistence)
                elapsed = int((time.monotonic() - start) * 1000)
                summary = trader.summary()
                logger.info("[%d] %s (%dms)", cycle_count, summary, elapsed)

                if persistence:
                    persistence.save_state(trader.balance, {s: {
                        "symbol": s, "direction": p.direction,
                        "price": p.entry_price, "size": p.size,
                        "scale_entries": p.scale_entries,
                    } for s, p in trader.positions.items()})
                    next_run = datetime.fromtimestamp(
                        time.time() + interval, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
                    cycle_id = int(time.time())
                    for sig in signals:
                        persistence.save_signal_log(
                            cycle_id, sig["symbol"], sig["signal"],
                            sig["price"], 0, 0,
                        )
                    persistence.save_heartbeat(next_run)
                    persistence.save_cycle_log(
                        summary=summary,
                        symbols_checked=len(config.trading.symbols),
                        trades_executed=len(trader.trades),
                        errors=0,
                        duration_ms=elapsed,
                        next_run_at=next_run,
                    )

                # $100 → $1000 challenge: detect failure and auto-restart
                if config.trading.challenge_enabled and persistence and prices:
                    equity = _compute_equity(trader, prices)
                    if equity < config.trading.challenge_failure_threshold:
                        ch = persistence.load_challenge_state()
                        ch['failures'] += 1
                        ch['restarts'] += 1
                        from datetime import date
                        ch['start'] = date.today().isoformat()
                        persistence.save_challenge_state(
                            ch['restarts'], ch['failures'], ch['start'],
                            config.trading.challenge_target,
                        )
                        logger.warning("CHALLENGE RESET — equity=$%.2f < $%.0f threshold (restart #%d, failure #%d)",
                                       equity, config.trading.challenge_failure_threshold,
                                       ch['restarts'], ch['failures'])
                        # Reset trader
                        trader.balance = config.trading.initial_capital
                        trader.positions.clear()
                        persistence.save_state(trader.balance, {})
                        persistence.save_initial_capital(config.trading.initial_capital)

                # Dynamic sleep: run every interval, don't drift
                sleep_for = max(1, interval - int(time.monotonic() - start))
                await asyncio.sleep(sleep_for)
        else:
            await run_cycle(config, exchange, store, strategy, trader, alert_channels, persistence)
            logger.info("Status: %s", trader.summary())
    except KeyboardInterrupt:
        logger.info("Shutdown")
    finally:
        await exchange.close()
        if persistence:
            persistence.close()


if __name__ == "__main__":
    asyncio.run(main())
