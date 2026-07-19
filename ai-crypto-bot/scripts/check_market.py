#!/usr/bin/env python3
import asyncio
import ccxt.async_support as ccxt
import pandas as pd

def _compute_adx(df, period=14):
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move
    atr = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr.replace(0, float('inf'))
    minus_di = 100 * minus_dm.rolling(period).mean() / atr.replace(0, float('inf'))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float('inf'))
    return dx.rolling(period).mean()

async def go():
    ex = ccxt.kraken({'enableRateLimit': True})
    for tf in ['1h', '15m']:
        for sym in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'DOGE/USDT']:
            ohlcv = await ex.fetch_ohlcv(sym, tf, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
            close = df['close'].iloc[-1]
            adx = _compute_adx(df)
            ema9 = df['close'].ewm(span=9).mean().iloc[-1]
            ema21 = df['close'].ewm(span=21).mean().iloc[-1]
            ema50 = df['close'].ewm(span=50).mean().iloc[-1]
            cross = "BULL" if ema9 > ema21 else "BEAR"
            print(f"{sym:12s} {tf:4s} ADX={adx.iloc[-1]:5.1f}  ${close:>8.2f}  EMA9/21={cross}  price_vs_50={close>ema50}")
    await ex.close()
asyncio.run(go())
