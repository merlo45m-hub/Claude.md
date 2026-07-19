#!/usr/bin/env python3
"""
AI Stock Trading Bot - Advanced Directional Strategy
Goal: Turn $100 into $1,000 via automated Long/Short trading
"""
import backtrader as bt
import yfinance as yf
import datetime
import pandas as pd
import numpy as np
import json
import sqlite3
import os

DB_PATH = '/root/ai_stock_trader/trading_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action TEXT,
        symbol TEXT,
        price REAL,
        size REAL,
        value REAL,
        portfolio_value REAL
    )''')
    conn.commit()
    conn.close()

def log_trade(symbol, side, price, quantity, profit=0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    c.execute('INSERT INTO trades (timestamp, action, symbol, price, size, value, portfolio_value) VALUES (?,?,?,?,?,?,?)',
              (timestamp, side, symbol, price, quantity, price*quantity, 100.0))
    conn.commit()
    conn.close()
    
    # Send Telegram alert
    try:
        import requests
        requests.post('http://localhost:8084/api/test-alert', 
                     json={'message': f'📈 New {side}: {symbol} at ${price:.2f} (size: {quantity:.4f})'},
                     timeout=2)
    except:
        pass  # Silently fail if dashboard not available

def update_portfolio(cash, position, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY,
        timestamp TEXT,
        cash REAL,
        position REAL,
        value REAL
    )''')
    c.execute('''INSERT OR REPLACE INTO portfolio (id, timestamp, cash, position, value)
                 VALUES (1, ?, ?, ?, ?)''',
              (datetime.datetime.now().isoformat(), cash, position, value))
    conn.commit()
    conn.close()

class AdvancedStrategy(bt.Strategy):
    params = (
        ('fast', 10),
        ('slow', 50),
        ('rsi_period', 14),
        ('rsi_upper', 70),
        ('rsi_lower', 30),
        ('symbol', 'AAPL'),
    )
    
    def __init__(self):
        self.close = self.datas[0].close
        self.sma_fast = bt.indicators.SMA(period=self.p.fast)
        self.sma_slow = bt.indicators.SMA(period=self.p.slow)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        self.order = None
        self.entry_price = 0
        self.current_side = None # 'LONG', 'SHORT', None

    def log(self, txt):
        dt = self.datas[0].datetime.date(0).isoformat()
        print(f"[{dt}] {txt}", flush=True)

    def next(self):
        if len(self) < self.p.slow:
            return
        if self.order:
            return

        price = self.close[0]
        
        # Decision Logic
        # 1. Bullish: SMA Cross Up + RSI not overbought -> LONG
        if self.crossover > 0 and self.rsi[0] < self.p.rsi_upper:
            if self.current_side != 'LONG':
                # Close Short if open
                if self.current_side == 'SHORT':
                    self.close()
                
                cash = self.broker.getcash()
                size = int(cash / price)
                if size > 0:
                    self.log(f"DECISION: LONG | Price: {price:.2f} | RSI: {self.rsi[0]:.2f}")
                    self.order = self.buy(size=size)
                    self.current_side = 'LONG'
                    self.entry_price = price
                    log_trade(self.p.symbol, 'LONG', price, size)

        # 2. Bearish: SMA Cross Down + RSI not oversold -> SHORT
        elif self.crossover < 0 and self.rsi[0] > self.p.rsi_lower:
            if self.current_side != 'SHORT':
                # Close Long if open
                if self.current_side == 'LONG':
                    self.close()
                
                cash = self.broker.getcash()
                size = int(cash / price)
                if size > 0:
                    self.log(f"DECISION: SHORT | Price: {price:.2f} | RSI: {self.rsi[0]:.2f}")
                    self.order = self.sell(size=size)
                    self.current_side = 'SHORT'
                    self.entry_price = price
                    log_trade(self.p.symbol, 'SHORT', price, size)

    def notify_order(self, order):
        if order.status == order.Completed:
            if order.isbuy():
                self.log(f"EXECUTION: BOUGHT {order.executed.size} at {order.executed.price:.2f}")
            else:
                self.log(f"EXECUTION: SOLD {order.executed.size} at {order.executed.price:.2f}")
            
            self.order = None
            update_portfolio(self.broker.getcash(), self.position.size, self.broker.getvalue())

def main():
    init_db()
    print("=" * 60)
    print("  🤖 AI DIRECTIONAL TRADER - LONG/SHORT VERSION")
    print("=" * 60)
    
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Optimization would happen here by iterating params
    cerebro.addstrategy(AdvancedStrategy)
    
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=100)
    df = yf.download("AAPL", start=start, end=end, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.columns = [str(c).lower() for c in df.columns]
    required = ['open', 'high', 'low', 'close', 'volume']
    df = df[required].dropna()
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    start_val = cerebro.broker.getvalue()
    cerebro.run()
    final_val = cerebro.broker.getvalue()
    
    print(f"\nFinal Portfolio Value: ${final_val:.2f} | Profit: ${final_val-start_val:.2f}")
    
    with open('/root/ai_stock_trader/results.txt', 'w') as f:
        f.write(f"Final: ${final_val:.2f}\n")

if __name__ == "__main__":
    main()
