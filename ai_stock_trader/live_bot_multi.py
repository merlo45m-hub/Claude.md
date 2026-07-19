#!/usr/bin/env python3
"""Live-paper trading bot: scans multiple tickers using SMA/RSI and trades the best opportunity."""
import sys, time, datetime, sqlite3, yfinance as yf, pandas as pd
from trader import log_trade, update_portfolio

DB_PATH = '/root/ai_stock_trader/trading_data.db'
SYMBOLS = ['AAPL','MSFT','TSLA','META','AMZN','NVDA','GOOGL']
INTERVAL_S = 60

def get_close(ticker):
    try:
        df = yf.download(ticker, period='50d', interval='1m', progress=False)
        if df.empty or 'Close' not in df.columns:
            return None
        return df['Close']
    except Exception:
        return None

def rank_tickers():
    scores = []
    for s in SYMBOLS:
        close = get_close(s)
        if close is None or len(close) < 50:
            continue
        sma_fast = close.rolling(10).mean().iloc[-1]
        sma_slow = close.rolling(50).mean().iloc[-1]
        delta = close.diff()
        up = delta.clip(lower=0).ewm(alpha=1/14).mean()
        down = -delta.clip(upper=0).ewm(alpha=1/14).mean()
        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        bullish = (sma_fast > sma_slow) * (1 - rsi/100)
        scores.append((s, sma_fast, sma_slow, rsi, bullish))
    scores.sort(key=lambda x: x[-1], reverse=True)
    return scores

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, action TEXT, symbol TEXT,
        price REAL, size REAL, portfolio_value REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY,
        timestamp TEXT, cash REAL, position REAL, value REAL)''')
    conn.commit()
    conn.close()

    cash = 100.0
    position = 0
    side = None

    while True:
        try:
            ranked = rank_tickers()
            if not ranked:
                raise RuntimeError('No data')
            best_sym, sma_f, sma_s, rsi, score = ranked[0]

            should_long = sma_f > sma_s and rsi < 70
            should_short = sma_f < sma_s and rsi > 30

            if should_long and side != 'LONG':
                if side == 'SHORT':
                    cash += position * get_close(best_sym)
                    position = 0
                    side = None
                    log_trade(best_sym, 'EXIT SHORT', 0, 0)
                price = get_close(best_sym)
                if price is None:
                    continue
                size = int(cash * 0.10 / price)
                if size > 0:
                    cash -= size * price
                    position = size
                    side = 'LONG'
                    log_trade(best_sym, 'BUY', price, size)
            elif should_short and side != 'SHORT':
                if side == 'LONG':
                    cash += position * get_close(best_sym)
                    position = 0
                    side = None
                    log_trade(best_sym, 'EXIT LONG', 0, 0)
                price = get_close(best_sym)
                if price is None:
                    continue
                size = int(cash * 0.10 / price)
                if size > 0:
                    cash -= size * price
                    position = size
                    side = 'SHORT'
                    log_trade(best_sym, 'SELL', price, size)

            portfolio_value = cash + position * get_close(best_sym) if get_close(best_sym) else cash
            update_portfolio(cash, position, portfolio_value)

            print(f"{datetime.datetime.utcnow().isoformat()} | {best_sym} | score={score:.3f} | cash={cash:.2f} pos={position} side={side}", flush=True)
            time.sleep(INTERVAL_S)

        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(INTERVAL_S)

if __name__ == '__main__':
    main()