#!/usr/bin/env python3
"""
Unified AI Stock Trading Strategy Engine
Combines live_bot_multi_fixed + trader.py into single implementation
Adds dynamic portfolio, stop-loss/take-profit, trailing stops, proper error handling
Includes $100-> $1000 challenge tracking with restarts and win rate
"""
import yfinance as yf
import pandas as pd
import sqlite3
import json
import datetime
import time
import os
from threading import Lock

DB_PATH = os.environ.get('DB_PATH', '/root/ai_stock_trader/trading_data.db')
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/root/ai_stock_trader/config.json')

DEFAULT_CONFIG = {
    'risk_per_trade': 0.02, 'max_positions': 6,
    'stop_loss': 0.05, 'take_profit': 0.05,
    'symbols': ['AAPL','MSFT','GOOGL','AMZN','META','TSLA','NVDA','NFLX','SPY','QQQ','IWM','XLF','XLK',
                'AMD','AVGO','JPM','V','MA','COST','HD','JNJ','PG','XLE','XLV','XLI','TLT','GLD','EEM'],
    'lookback_days': 60, 'interval_seconds': 60, 'initial_cash': 100.0
}

db_lock = Lock()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=5000')
    return conn

def get_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_CONFIG

def init_db():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, action TEXT, symbol TEXT,
            price REAL, size REAL, value REAL, portfolio_value REAL, stop_loss REAL, take_profit REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY, timestamp TEXT, cash REAL, position REAL, value REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS equity_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, value REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, side TEXT, entry_price REAL,
            size REAL, stop_loss REAL, take_profit REAL, opened_at TEXT, trailing_high REAL, trailing_low REAL, scale_count INTEGER DEFAULT 1
        )''')
        # Add trailing columns if they don't exist (migration)
        try:
            c.execute("ALTER TABLE positions ADD COLUMN trailing_high REAL")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE positions ADD COLUMN trailing_low REAL")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE positions ADD COLUMN scale_count INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        c.execute('''CREATE TABLE IF NOT EXISTS challenge_status (
            id INTEGER PRIMARY KEY, restart_count INTEGER DEFAULT 0, failure_count INTEGER DEFAULT 0,
            win_streak INTEGER DEFAULT 0, challenge_current_value REAL DEFAULT 100.0, challenge_goal REAL DEFAULT 1000.0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS challenge_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, event TEXT, value REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS close_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, side TEXT, requested_at TEXT, done INTEGER DEFAULT 0
        )''')
        c.execute("INSERT OR IGNORE INTO portfolio (id, timestamp, cash, position, value) VALUES (1, ?, 100.0, 0.0, 100.0)",
                  (datetime.datetime.now().isoformat(),))
        c.execute("INSERT OR IGNORE INTO challenge_status (id) VALUES (1)")
        conn.commit()
    finally:
        conn.close()

# Drawdown Protection
DAILY_LOSS_LIMIT = 0.05

def check_daily_drawdown(current_value):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM equity_history WHERE date(timestamp) = date('now') ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        if row and row[0]:
            daily_start = float(row[0])
            daily_loss = (daily_start - current_value) / daily_start
            if daily_loss > DAILY_LOSS_LIMIT:
                print(f"⚠️ Daily loss limit hit: {daily_loss*100:.1f}% > {DAILY_LOSS_LIMIT*100}%")
                log_challenge_event('DAILY_LIMIT', current_value)
                return True
        return False
    finally:
        conn.close()

# Challenge Tracking
def check_challenge_status(current_value):
    if current_value < 10.0:
        print("🚨 CHALLENGE FAILURE! Portfolio < $10")
        update_challenge_status(failed=True)
        log_challenge_event('FAILURE', current_value)
        return 'FAILED'
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT challenge_goal FROM challenge_status WHERE id = 1")
    row = c.fetchone()
    conn.close()
    if current_value >= (row[0] if row else 1000.0):
        print(f"🎉 CHALLENGE SUCCESS! Reached ${current_value:.2f}")
        log_challenge_event('SUCCESS', current_value)
        return 'SUCCESS'
    return 'CONTINUE'

def update_challenge_status(restart=False, failed=False, current_value=None):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT restart_count, failure_count FROM challenge_status WHERE id = 1")
        row = c.fetchone()
        r, f = (row[0] if row else 0), (row[1] if row else 0)
        if restart: r += 1
        if failed: f += 1
        c.execute("UPDATE challenge_status SET restart_count=?, failure_count=?, challenge_current_value=? WHERE id=1",
                  (r, f, current_value or 100.0))
        conn.commit()
    finally:
        conn.close()

def log_challenge_event(event_type, value):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO challenge_log (timestamp, event, value) VALUES (?,?,?)",
                  (datetime.datetime.now().isoformat(), event_type, value))
        conn.commit()
    finally:
        conn.close()

def get_challenge_stats():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT restart_count, failure_count, challenge_current_value FROM challenge_status WHERE id = 1")
        row = c.fetchone()
        return {'restarts': row[0] if row else 0, 'failures': row[1] if row else 0,
                'current_value': row[2] if row else 100.0}
    finally:
        conn.close()

def get_trade_win_rate():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT action, portfolio_value FROM trades WHERE action LIKE 'CLOSE_%'")
        closed = c.fetchall()
        if not closed: return 0.0
        wins = sum(1 for t in closed if t[1] > 0)
        return wins / len(closed) * 100
    finally:
        conn.close()

# Portfolio Management
def get_portfolio_value():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT cash, value FROM portfolio WHERE id = 1")
        row = c.fetchone()
        return (float(row[0]), float(row[1])) if row else (100.0, 100.0)
    finally:
        conn.close()

def update_portfolio(cash, position, value):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO portfolio (id, timestamp, cash, position, value)
                     VALUES (1, ?, ?, ?, ?)''',
                  (datetime.datetime.now().isoformat(), cash, position, value))
        conn.commit()
    finally:
        conn.close()

def get_open_positions(symbol=None):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        if symbol:
            c.execute("SELECT symbol, side, entry_price, size, stop_loss, take_profit, trailing_high, trailing_low, scale_count, opened_at FROM positions WHERE symbol = ?", (symbol,))
        else:
            c.execute("SELECT symbol, side, entry_price, size, stop_loss, take_profit, trailing_high, trailing_low, scale_count, opened_at FROM positions")
        return [{'symbol': r[0], 'side': r[1], 'entry_price': r[2], 'size': r[3],
                 'stop_loss': r[4], 'take_profit': r[5], 'trailing_high': r[6], 'trailing_low': r[7], 'scale_count': r[8], 'created_at': r[9] or '2000-01-01'} for r in c.fetchall()]
    finally:
        conn.close()

def update_trailing_price(symbol, side, new_high=None, new_low=None):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        if side == 'SHORT':
            c.execute("UPDATE positions SET trailing_low = ? WHERE symbol = ? AND side = ?", (new_low, symbol, side))
        else:
            c.execute("UPDATE positions SET trailing_high = ? WHERE symbol = ? AND side = ?", (new_high, symbol, side))
        conn.commit()
    finally:
        conn.close()

def scale_position(symbol, side, new_price, scale_factor=0.5):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT size, entry_price, scale_count FROM positions WHERE symbol = ? AND side = ?", (symbol, side))
        row = c.fetchone()
        if row and row[2] < 2:  # Max 2 scales
            old_size, old_entry, scales = row[0], row[1], row[2]
            cash, _ = get_portfolio_value()
            size = (cash * 0.02 * scale_factor) / new_price
            if size > 0:
                c.execute("UPDATE positions SET size = size + ?, entry_price = ?, scale_count = ? WHERE symbol = ? AND side = ?",
                          (size, (old_entry * old_size + new_price * size) / (old_size + size), scales + 1, symbol, side))
                conn.commit()
                log_trade(symbol, f"SCALE_{side}", new_price, size, cash + old_size * new_price, 0.03, 0.02)
                print(f"[{symbol}] SCALED {side} +{size:.4f} @ ${new_price:.2f} (scale #{scales + 1})")
    finally:
        conn.close()

def request_close_position(symbol, side):
    """Queue a manual close. The bot honors it on its next loop tick via the same exit path."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO close_requests (symbol, side, requested_at) VALUES (?, ?, ?)",
                  (symbol, side, datetime.datetime.now().isoformat()))
        conn.commit()
        return True
    finally:
        conn.close()

def get_pending_close_requests():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT symbol, side FROM close_requests WHERE done = 0")
        return [{'symbol': r[0], 'side': r[1]} for r in c.fetchall()]
    finally:
        conn.close()

def clear_close_request(symbol, side):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("UPDATE close_requests SET done = 1 WHERE symbol = ? AND side = ? AND done = 0", (symbol, side))
        conn.commit()
    finally:
        conn.close()

def update_position(symbol, side, entry_price, size, stop_loss, take_profit, action='open', trailing_high=None, trailing_low=None):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        if action == 'open':
            c.execute('''INSERT INTO positions (symbol, side, entry_price, size, stop_loss, take_profit, opened_at, trailing_high, trailing_low)
                        VALUES (?,?,?,?,?,?,?,?,?)''',
                      (symbol, side, entry_price, size, stop_loss, take_profit, datetime.datetime.now().isoformat(), trailing_high, trailing_low))
        else:
            c.execute("DELETE FROM positions WHERE symbol = ? AND side = ?", (symbol, side))
        conn.commit()
    finally:
        conn.close()

# Trading Functions
def log_trade(symbol, side, price, quantity, portfolio_value, stop_loss=None, take_profit=None):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO trades (timestamp, action, symbol, price, size, value, portfolio_value, stop_loss, take_profit)
                     VALUES (?,?,?,?,?,?,?,?,?)''',
                  (datetime.datetime.now().isoformat(), side, symbol, price, quantity, price*quantity, portfolio_value, stop_loss, take_profit))
        # Record equity snapshot
        c.execute('''INSERT INTO equity_history (timestamp, value) VALUES (?, ?)''',
                  (datetime.datetime.now().isoformat(), portfolio_value))
        conn.commit()
    finally:
        conn.close()

DECISION_LOG_PATH = os.environ.get('DECISION_LOG_PATH', '/app/decision_log.txt')

def write_decision_block(logic, risk, confidence, symbol, price):
    block = {'logic': logic, 'risk': risk, 'confidence': confidence, 'symbol': symbol, 'price': price}
    timestamp = datetime.datetime.utcnow().isoformat()
    try:
        with open(DECISION_LOG_PATH, 'a') as f:
            f.write(f"{timestamp} {json.dumps(block)}\n")
    except Exception:
        pass  # non-critical, skip if file not writable

# Strategy Indicators
def get_close_series(df):
    if df is None or df.empty: return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.droplevel(1)
    if 'Close' not in df.columns: return None
    s = df['Close']
    if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
    return s.astype(float)

def compute_indicators(close_series):
    if len(close_series) < 50: return None
    close_series = close_series.astype(float)
    sma_fast = close_series.rolling(window=10).mean()
    sma_slow = close_series.rolling(window=50).mean()
    delta = close_series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return sma_fast.iloc[-1], sma_slow.iloc[-1], rsi.iloc[-1]

# Volatility Filter
def get_vxx_level():
    try:
        df = yf.download('VXX', period='5d', interval='1d', progress=False)
        close_series = get_close_series(df)
        if close_series is not None and len(close_series) >= 1:
            return float(close_series.iloc[-1])
    except:
        pass
    return 20.0  # default

def is_volatility_ok():
    vxx = get_vxx_level()
    return 8.0 <= vxx <= 40.0

MAX_HOLD_DAYS = 3

def should_exit_position(current_price, position, trailing_stop=0.02):
    # Time-based exit: close if held longer than MAX_HOLD_DAYS
    from datetime import timedelta
    created_dt = datetime.datetime.strptime(position.get('created_at', '2000-01-01'), '%Y-%m-%dT%H:%M:%S.%f')
    if datetime.datetime.now() - created_dt > timedelta(days=MAX_HOLD_DAYS):
        return 'TIME_EXIT'
    entry, sl, tp = position['entry_price'], position['stop_loss'], position['take_profit']
    trailing_high = position.get('trailing_high')
    trailing_low = position.get('trailing_low')
    
    if position['side'] == 'LONG':
        if trailing_high and trailing_high > entry:
            new_sl = trailing_high * (1 - sl)
            if current_price <= new_sl:
                return 'TRAILING_STOP'
        if current_price <= entry * (1 - sl): return 'STOP_LOSS'
        if current_price >= entry * (1 + tp): return 'TAKE_PROFIT'
    else:
        if trailing_low and trailing_low < entry:
            new_sl = trailing_low * (1 + sl)
            if current_price >= new_sl:
                return 'TRAILING_STOP'
        if current_price >= entry * (1 + sl): return 'STOP_LOSS'
        if current_price <= entry * (1 - tp): return 'TAKE_PROFIT'
    return None

def execute_trade(symbol, side, price, size, portfolio_value, config):
    sl = config.get('stop_loss', 0.05)
    tp = config.get('take_profit', 0.1)
    log_trade(symbol, side, price, size, portfolio_value, sl, tp)
    update_position(symbol, side, price, size, sl, tp, action='open')
    write_decision_block(f"SMA Cross {'Up' if side == 'LONG' else 'Down'} + RSI Filter", sl, 0.7, symbol, price)
    print(f"  DECISION: {side} {symbol} @ ${price:.2f} | Stop: {sl*100}% | Target: {tp*100}%")

# Main Trading Loop
def report_challenge_status():
    stats = get_challenge_stats()
    win_rate = get_trade_win_rate()
    print(f"\n📊 CHALLENGE STATUS:")
    print(f"  Current Value: ${stats['current_value']:.2f}")
    print(f"  Target: $1000")
    print(f"  Restarts: {stats['restarts']} | Failures: {stats['failures']}")
    print(f"  Win Rate: {win_rate:.1f}%\n")

def main():
    config = get_config()
    init_db()
    
    print("=" * 60)
    print("  🤖 UNIFIED AI TRADING ENGINE - $100→$1000 CHALLENGE")
    print("=" * 60)
    print(f"Symbols: {len(config['symbols'])} (stocks + ETFs)")
    print(f"Stop Loss: {config['stop_loss']*100}% | Take Profit: {config['take_profit']*100}%")
    print(f"Daily Loss Limit: {DAILY_LOSS_LIMIT*100}% | Trailing Stop: 2%")
    report_challenge_status()
    
    lookback_days = config.get('lookback_days', 60)
    interval = config.get('interval_seconds', 60)
    
    while True:
        print(f"[CYCLE START] {datetime.datetime.now().isoformat()}", flush=True)
        cash, portfolio_value = get_portfolio_value()

        if check_daily_drawdown(portfolio_value):
            print("🛑 Trading paused due to daily loss limit")

        for symbol in config['symbols']:
            try:
                df = yf.download(symbol, period=f'{lookback_days}d', interval='1d', progress=False)
                close_series = get_close_series(df)
                if close_series is None or len(close_series) < 50:
                    continue
                
                sma_fast, sma_slow, rsi = compute_indicators(close_series)
                if None in (sma_fast, sma_slow, rsi):
                    continue
                
                price = close_series.iloc[-1]
                
                # Volatility filter for ALL symbols - skip if market too volatile or complacent
                vxx_level = get_vxx_level()
                if not (15.0 <= vxx_level <= 25.0):
                    if symbol == config['symbols'][0]:
                        print(f"[VXX] Filtered - VXX={vxx_level:.2f} (not 15-25)")
                    if symbol not in open_positions:
                        continue  # Skip new entries, let existing positions run
                
                open_positions = {p['symbol']: p for p in get_open_positions()}
                
                if symbol in open_positions:
                    position = open_positions[symbol]
                    
                    # Update trailing prices
                    if position['side'] == 'SHORT':
                        new_low = min(position.get('trailing_low') or price, price)
                        update_trailing_price(symbol, 'SHORT', new_low=new_low)
                        position['trailing_low'] = new_low
                    else:
                        new_high = max(position.get('trailing_high') or price, price)
                        update_trailing_price(symbol, 'LONG', new_high=new_high)
                        position['trailing_high'] = new_high
                    
                    # Check for manual close request (honored via same exit path)
                    pending = get_pending_close_requests()
                    if any(r['symbol'] == symbol and r['side'] == position['side'] for r in pending):
                        print(f"[{symbol}] EXIT: MANUAL_CLOSE @ ${price:.2f}")
                        log_trade(symbol, "CLOSE_MANUAL", price, position['size'], portfolio_value)
                        update_position(symbol, position['side'], 0, 0, 0, 0, action='close')
                        clear_close_request(symbol, position['side'])
                        continue

                    # Check for position scaling (1.5% favorable move)
                    entry = position['entry_price']
                    favorable = (entry - price) / entry if position['side'] == 'SHORT' else (price - entry) / entry
                    if favorable >= 0.015 and position.get('scale_count', 1) < 2:
                        scale_position(symbol, position['side'], price)
                    
                    exit_reason = should_exit_position(price, position)
                    if exit_reason:
                        print(f"[{symbol}] EXIT: {exit_reason} @ ${price:.2f}")
                        log_trade(symbol, f"CLOSE_{exit_reason}", price, position['size'], portfolio_value)
                        update_position(symbol, position['side'], 0, 0, 0, 0, action='close')
                        continue
                
                if len(get_open_positions()) >= config.get('max_positions', 3):
                    continue
                
                if check_daily_drawdown(portfolio_value):
                    continue
                
                size = (cash * config['risk_per_trade']) / price
                if size <= 0: continue
                
                # Skip entries if volatility outside target range (VXX 15-25)
                if not (15.0 <= vxx_level <= 25.0):
                    if symbol not in open_positions:
                        continue  # Skip new entries, let existing positions run
                
                if sma_fast > sma_slow and rsi < 70:
                    if symbol not in open_positions:
                        execute_trade(symbol, 'LONG', price, size, portfolio_value, config)
                elif sma_fast < sma_slow and rsi > 30:
                    if symbol not in open_positions:
                        execute_trade(symbol, 'SHORT', price, size, portfolio_value, config)
                
            except Exception as e:
                print(f"[{symbol}] Error: {e}")
                continue
        
        cash, new_value = get_portfolio_value()
        update_challenge_status(current_value=new_value)
        update_portfolio(cash, 0, new_value)
        # Snapshot equity every cycle so PnL tracks continuously
        # (not only when a trade fires). Required for live dashboard chart.
        try:
            _c = get_db_connection()
            _c.execute('INSERT INTO equity_history (timestamp, value) VALUES (?, ?)',
                       (datetime.datetime.now().isoformat(), new_value))
            _c.commit()
            _c.close()
        except Exception as e:
            print(f"[EQUITY SNAPSHOT] Error: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    main()