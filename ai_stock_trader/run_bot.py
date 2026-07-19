#!/usr/bin/env python3
import json
import os
import datetime
import time
import pandas as pd
import yfinance as yf
import backtrader as bt
import trader

def load_params():
    default = {'fast': 10, 'slow': 50, 'symbol': 'AAPL'}
    path = os.path.join(os.path.dirname(__file__), 'params.json')
    if os.path.exists(path):
        try:
            with open(path) as f:
                default.update(json.load(f))
        except Exception:
            pass
    return default

def main():
    trader.init_db()
    params = load_params()
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(1000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addstrategy(trader.AdvancedStrategy, **params)
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=100)
    df = yf.download(params.get('symbol', 'AAPL'), start=start, end=end, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    required = ['open', 'high', 'low', 'close', 'volume']
    for col in required:
        if col not in df.columns:
            df[col] = df['close']
    df = df[required].dropna()
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    start_val = cerebro.broker.getvalue()
    cerebro.run()
    final_val = cerebro.broker.getvalue()
    profit = final_val - start_val
    pct = profit / start_val * 100
    print(f"RESULTS: start={start_val:.2f} final={final_val:.2f} profit={profit:.2f} ({pct:.1f}%)")
    with open('/root/ai_stock_trader/results.txt', 'a') as f:
        ts = datetime.datetime.now().isoformat()
        f.write(f"{ts} start={start_val:.2f} final={final_val:.2f} profit={profit:.2f} ({pct:.1f}%)\n")
        
if __name__ == '__main__':
    while True:
        main()
        time.sleep(3600)