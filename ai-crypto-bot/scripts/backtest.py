#!/usr/bin/env python3
"""CLI entry point for running backtests.

Usage:
    python scripts/backtest.py --symbol BTC/USDT --strategy sma_cross --days 180
    python scripts/backtest.py --strategy rsi --fee 0.001
    python scripts/backtest.py --strategy macd --list
"""

from __future__ import annotations

import argparse

from src.config import load_config
from src.exchange.client import ExchangeClient
from src.strategy.factory import StrategyFactory


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a backtest")
    parser.add_argument("--symbol", default="BTC/USDT", help="Trading pair")
    parser.add_argument("--strategy", default=None, help="Strategy type (default: from config)")
    parser.add_argument("--days", type=int, default=180, help="Days of history")
    parser.add_argument("--timeframe", default="1h", help="OHLCV timeframe")
    parser.add_argument("--fee", type=float, default=0.0, help="Trading fee fraction")
    parser.add_argument("--capital", type=float, default=None, help="Initial capital")
    parser.add_argument("--list", action="store_true", help="List available strategies")
    args = parser.parse_args()

    config = load_config()
    strat_type = args.strategy or config.strategy.type

    if args.list:
        from src.strategy.factory import _registry
        from src.strategy.factory import _lazy_import
        _lazy_import()
        print("Available strategies:", list(_registry.keys()))
        return

    print(f"Fetching {args.days}d of {args.timeframe} data for {args.symbol}...")
    exchange = ExchangeClient(config.exchange)
    try:
        df = await exchange.fetch_ohlcv(args.symbol, timeframe=args.timeframe, limit=args.days * 24)
    finally:
        await exchange.close()

    if df is None or df.empty:
        print("No data returned")
        return

    print(f"Got {len(df)} bars from {df.index[0]} to {df.index[-1]}")

    from src.backtesting.engine import Backtester
    from src.config import TradingConfig

    strat_obj = StrategyFactory.create(strat_type, config.strategy)

    trading_cfg = TradingConfig(
        symbols=[args.symbol],
        initial_capital=args.capital or config.trading.initial_capital,
        position_size_pct=config.trading.position_size_pct,
        max_open_positions=config.trading.max_open_positions,
        atr_multiplier=config.trading.atr_multiplier,
        reward_ratio=config.trading.reward_ratio,
        stop_loss_pct=config.trading.stop_loss_pct,
        take_profit_pct=config.trading.take_profit_pct,
    )

    bt = Backtester(trading_cfg, strat_obj, fee_pct=args.fee)
    result = bt.run(df, symbol=args.symbol)

    print("\n" + "=" * 60)
    print(f"  Backtest: {args.symbol} | {strat_type} | {args.days}d")
    print("=" * 60)
    print(result.summary())
    print(f"  Initial: ${result.initial_balance:.2f}")
    print(f"  Final:   ${result.final_balance:.2f}")
    print(f"  Total PnL: ${result.total_pnl:.2f}")
    print(f"  Return: {result.total_return_pct:+.2f}%")
    print(f"  Buy & Hold: {result.buy_hold_return_pct:+.2f}%")
    print(f"  Win Rate: {result.win_rate:.0%}")
    print(f"  Max Drawdown: {result.max_drawdown:.1%}")
    print(f"  Sharpe: {result.sharpe_ratio:.2f}")
    print(f"  Calmar: {result.calmar_ratio:.2f}")
    print(f"  Trades: {result.n_trades}")
    print(f"  Bars: {result.duration_bars}")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
