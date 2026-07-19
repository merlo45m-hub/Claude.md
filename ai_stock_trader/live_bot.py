#!/usr/bin/env python3
"""Live‑paper trading bot for the Demo AI Stock Trader.

All logic is implemented directly in this script so that the
process does not depend on the backtrader back‑testing framework.
It keeps a rolling window of the last N daily candles, calculates
SMAs and RSI, and decides whether to go long (buy) or stay flat.
The bot logs every trade to the SQLite store that the Flask UI
consumes, and it updates the portfolio table so the UI can report
value, cash, and position.

The service is run by systemd and auto‑restarts on failure.
"""

import sys
import time
import datetime
import yfinance as yf
import pandas as pd
from trader import log_trade, update_portfolio

SYMBOL = "AAPL"
START_DAYS = 200    # days of history to keep in the rolling window
LOOKBACK_DAYS = 50  # number of days used to calculate SMAs
RSI_PERIOD = 14
RISK_CAP = 0.10  # trade 10% of cash each time
INTERVAL_S = 60   # how often to check the market (seconds)

def build_initial_data():
    """Return DataFrame with the last START_DAYS of daily OHLCV data.
    If download fails after a few attempts, use a small dummy dataset.
    """
    max_retries = 3
    attempt = 0
    while attempt < max_retries:
        try:
            attempt += 1
            print(f"build_initial_data: attempt {attempt}")
            end = datetime.datetime.utcnow()
            start = end - datetime.timedelta(days=START_DAYS)
            df = yf.download(SYMBOL, start=start, end=end, progress=False, interval="1d")
            print(f"Download rows: {len(df)}")
            if df.empty:
                raise RuntimeError("Empty download")
            # Flatten MultiIndex columns if present (yfinance multi-ticker format)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = [str(c).lower() for c in df.columns]
            df = df.dropna()
            return df
        except Exception as e:
            print(f"build_initial_data failure: {e}")
            print("Falling back to dummy data (forced)")
            sys.stdout.flush()
            time.sleep(10)
    # fallback dummy data
    print("Falling back to dummy data")
    dummy = pd.DataFrame({
        'open': [100]*START_DAYS,
        'high': [110]*START_DAYS,
        'low': [95]*START_DAYS,
        'close': [105]*START_DAYS,
        'volume': [1000]*START_DAYS
    }, index=range(START_DAYS))
    return dummy

def calculate_sma(series, period):
    return series.rolling(window=period).mean()

def calculate_rsi(series, period):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(alpha=1/period, adjust=False).mean()
    ema_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def main():
    # Keep trying to get initial data until we succeed
    print("=== live_bot.py started ===")
    sys.stdout.flush()
    while True:
        try:
            history = build_initial_data()
            break
        except Exception as e:
            print(f"Failed to load initial data: {e}. Retrying in 30s...")
            time.sleep(30)

    cash = 100.0
    position = 0  # number of shares
    side = None  # "LONG" or None

    while True:
        try:
            # 1. get current price using daily data (consistent with history)
            current = yf.download(SYMBOL, period="2d", interval="1d", progress=False)
            if current.empty:
                raise RuntimeError("No recent quote data")
            if isinstance(current.columns, pd.MultiIndex):
                current.columns = current.columns.get_level_values(0)
            price = current['Close'].iloc[-1]

            # 2. update rolling history with daily data
            new_row = pd.Series(
                {"open": price, "high": price, "low": price, "close": price, "volume": 1},
                index=history.columns,
            )
            history = pd.concat([history, new_row.to_frame().T])
            history = history.tail(START_DAYS)

            # 3. compute indicators using only the most recent data block of LOOKBACK_DAYS
            df = history.tail(LOOKBACK_DAYS)
            sma_fast = calculate_sma(df["close"], 10).iloc[-1]
            sma_slow = calculate_sma(df["close"], 50).iloc[-1]
            rsi = calculate_rsi(df["close"], RSI_PERIOD).iloc[-1]

            # 4. decision logic (mirrors AdvancedStrategy but simplified)
            trade_executed = False
            if sma_fast is None or sma_slow is None or pd.isna(rsi):
                pass  # insufficient data
            else:
                if sma_fast > sma_slow and rsi < 70:
                    if side != "LONG" and cash > 0:
                        size = int(cash * RISK_CAP / price)
                        if size > 0:
                            cash -= size * price
                            position += size
                            side = "LONG"
                            log_trade(SYMBOL, "BUY", price, size)
                            trade_executed = True
                elif sma_fast < sma_slow and rsi > 30:
                    if side == "LONG" and position > 0:
                        cash += position * price
                        log_trade(SYMBOL, "SELL", price, position)
                        position = 0
                        side = None
                        trade_executed = True

            # 5. update portfolio table for UI
            portfolio_value = cash + position * price
            update_portfolio(cash, position, portfolio_value)

            # 6. simple log output
            if trade_executed:
                print(
                    f"{datetime.datetime.utcnow().isoformat()} executed trade: "
                    f"side={side} price={price:.2f} cash={cash:.2f} pos={position}"
                )
            else:
                print(
                    f"{datetime.datetime.utcnow().isoformat()} no trade "
                    f"price={price:.2f} cash={cash:.2f} pos={position}"
                )
            sys.stdout.flush()

            # 7. wait until next interval
            time.sleep(INTERVAL_S)

        except Exception as exc:
            print(f"Exception in live bot: {exc}")
            time.sleep(INTERVAL_S)
            continue

if __name__ == "__main__":
    main()
