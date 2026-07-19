#!/usr/bin/env python3
"""
Strategy optimizer — backtests parameter combinations, updates live config with best found.
Runs symbol-by-symbol and optimizes for max return + Sharpe-like score.
"""
import json
import datetime
import os

import yfinance as yf
import pandas as pd
import numpy as np

CONFIG_PATH = os.environ.get('CONFIG_PATH', '/root/ai_stock_trader/config.json')
OPTIMIZE_LOG = '/root/ai_stock_trader/optimize_results.json'

DEFAULT_PARAMS = {
    'sma_fast': 10, 'sma_slow': 50, 'rsi_period': 14,
    'rsi_upper': 70, 'rsi_lower': 30,
    'stop_loss': 0.05, 'take_profit': 0.1, 'risk_per_trade': 0.02,
}

def get_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def compute_indicators(close, sma_fast, sma_slow, rsi_period):
    sma_f = close.rolling(window=sma_fast).mean()
    sma_s = close.rolling(window=sma_slow).mean()
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_g = gain.rolling(window=rsi_period).mean()
    avg_l = loss.rolling(window=rsi_period).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return sma_f, sma_s, rsi

def backtest_symbol(symbol, params, period='6mo'):
    df = yf.download(symbol, period=period, interval='1d', progress=False)
    if df is None or df.empty:
        return None

    close = df['Close']
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.astype(float)

    sma_f, sma_s, rsi = compute_indicators(
        close, params['sma_fast'], params['sma_slow'], params['rsi_period'])
    if sma_f is None:
        return None

    cash = 100.0
    pos = 0.0
    pos_side = None
    entry_price = 0.0
    trades = 0
    wins = 0
    equity = [100.0]

    for i in range(params['sma_slow'], len(close)):
        price = float(close.iloc[i])
        pf = float(sma_f.iloc[i])
        ps = float(sma_s.iloc[i])
        r = float(rsi.iloc[i])

        if pos_side and pos > 0 and entry_price > 0:
            ret = (price - entry_price) / entry_price
            if pos_side == 'SHORT':
                ret = -ret
            if ret <= -params['stop_loss'] or ret >= params['take_profit']:
                cash += pos * price
                if ret > 0: wins += 1
                trades += 1
                pos = 0
                pos_side = None
                entry_price = 0.0

        if pos == 0 and not pd.isna(pf) and not pd.isna(ps) and not pd.isna(r):
            size = (cash * params['risk_per_trade']) / price
            if pf > ps and r < params['rsi_upper']:
                pos = size
                pos_side = 'LONG'
                entry_price = price
                cash -= size * price
            elif pf < ps and r > params['rsi_lower']:
                pos = size
                pos_side = 'SHORT'
                entry_price = price
                cash -= size * price

        equity.append(cash + pos * price)

    if pos > 0 and entry_price > 0:
        price = float(close.iloc[-1])
        ret = (price - entry_price) / entry_price
        if pos_side == 'SHORT': ret = -ret
        if ret > 0: wins += 1
        trades += 1
        cash += pos * price

    final = cash
    ret_pct = (final - 100.0) / 100.0
    eq_arr = np.array(equity, dtype=float)
    running_max = np.maximum.accumulate(eq_arr)
    dd = float(np.max(running_max - eq_arr))
    sharpe = float(np.mean(np.diff(eq_arr)) / np.std(np.diff(eq_arr)) * np.sqrt(252)) if np.std(np.diff(eq_arr)) > 0 else 0
    win_rate = wins / trades if trades > 0 else 0

    return {
        'return_pct': round(ret_pct * 100, 2),
        'sharpe': round(sharpe, 3),
        'max_drawdown': round(dd, 2),
        'trades': trades,
        'win_rate': round(win_rate * 100, 1),
        'final_value': round(final, 2),
    }

def load_best():
    try:
        with open(OPTIMIZE_LOG) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'best_score': -999, 'best_params': dict(DEFAULT_PARAMS), 'history': []}

def save_best(best, entry):
    entry['timestamp'] = datetime.datetime.now().isoformat()
    best['history'].append(entry)
    best['best_score'] = entry['score']
    best['best_params'] = entry['params']
    best['history'] = best['history'][-20:]
    best['history'].sort(key=lambda x: x['score'], reverse=True)
    tmp = OPTIMIZE_LOG + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(best, f, indent=2)
    os.replace(tmp, OPTIMIZE_LOG)
    return best

def optimize():
    config = get_config()
    symbols = config.get('symbols', ['SPY'])
    best = load_best()

    sma_fast_vals = [10, 20]
    sma_slow_vals = [50, 100]
    rsi_upper_vals = [70, 75]
    rsi_lower_vals = [25, 30]
    stop_loss_vals = [0.05, 0.07]
    take_profit_vals = [0.08, 0.12]

    best_score = best['best_score']
    param_scores = []

    total_combos = (len(sma_fast_vals) * len(sma_slow_vals) * len(rsi_upper_vals)
                    * len(rsi_lower_vals) * len(stop_loss_vals) * len(take_profit_vals))
    done = 0

    print(f"Optimizing across {total_combos} param combinations, {len(symbols)} symbols...")

    for sf in sma_fast_vals:
        for ss in sma_slow_vals:
            if sf >= ss:
                continue
            for ru in rsi_upper_vals:
                for rl in rsi_lower_vals:
                    if rl >= ru:
                        continue
                    for sl in stop_loss_vals:
                        for tp in take_profit_vals:
                            params = {
                                'sma_fast': sf, 'sma_slow': ss, 'rsi_period': 14,
                                'rsi_upper': ru, 'rsi_lower': rl,
                                'stop_loss': sl, 'take_profit': tp, 'risk_per_trade': 0.02,
                            }

                            results = []
                            for sym in symbols[:1]:
                                r = backtest_symbol(sym, params)
                                if r:
                                    results.append(r)

                            if not results:
                                continue

                            avg_return = np.mean([r['return_pct'] for r in results])
                            avg_sharpe = np.mean([r['sharpe'] for r in results])
                            avg_dd = np.mean([r['max_drawdown'] for r in results])
                            score = avg_return - avg_dd * 0.5 + avg_sharpe * 3

                            param_scores.append({
                                'score': round(score, 2),
                                'avg_return': round(avg_return, 2),
                                'avg_sharpe': round(avg_sharpe, 3),
                                'avg_drawdown': round(avg_dd, 2),
                                'params': params,
                            })
                            done += 1

    if not param_scores:
        print("No results — no valid data downloaded")
        return

    param_scores.sort(key=lambda x: x['score'], reverse=True)
    top5 = param_scores[:5]

    print(f"\nTop 5 param sets (scored from {len(param_scores)} tested):")
    for i, p in enumerate(top5):
        print(f"{i+1}. score={p['score']} ret={p['avg_return']}% sharpe={p['avg_sharpe']} "
              f"dd={p['avg_drawdown']} | SMA({p['params']['sma_fast']},{p['params']['sma_slow']}) "
              f"RSI({p['params']['rsi_lower']},{p['params']['rsi_upper']}) "
              f"SL={p['params']['stop_loss']} TP={p['params']['take_profit']}")

    winner = top5[0]

    if winner['score'] > best_score:
        print(f"\nNEW BEST! Score {winner['score']} > prev {best_score}")
        best['best_params'] = winner['params']
        best['best_score'] = winner['score']
        save_best(best, winner)

        config['stop_loss'] = winner['params']['stop_loss']
        config['take_profit'] = winner['params']['take_profit']
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Updated config.json: stop_loss={winner['params']['stop_loss']}, "
              f"take_profit={winner['params']['take_profit']}")
    else:
        print(f"Current best {best_score} still leads (new best: {winner['score']})")

    print(f"OPTIMIZE_RESULT: best_score={winner['score']} best_return={winner['avg_return']}%")

if __name__ == '__main__':
    optimize()
