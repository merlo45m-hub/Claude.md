#!/usr/bin/env python3
import yfinance as yf, pandas as pd, time, datetime, sqlite3, json, os
from threading import Lock

# Database lock to prevent concurrent writes from multiple threads
db_lock = Lock()

def get_db_connection():
    """Get a database connection with proper settings for concurrency."""
    conn = sqlite3.connect('/root/ai_stock_trader/trading_data.db', timeout=20.0)
    # Enable WAL mode for better concurrency
    conn.execute('PRAGMA journal_mode=WAL')
    # Set synchronous to NORMAL for a good balance of safety and speed
    conn.execute('PRAGMA synchronous=NORMAL')
    # Set a busy timeout of 5 seconds
    conn.execute('PRAGMA busy_timeout=5000')
    # Increase cache size
    conn.execute('PRAGMA cache_size=-64000')  # 64MB
    return conn

def write_decision_block(logic, risk, confidence):
    block = {"logic": logic, "risk": risk, "confidence": confidence}
    timestamp = datetime.datetime.utcnow().isoformat()
    path = '/root/ai_stock_trader/decision_log.txt'
    with open(path, 'a') as f:
        f.write(f"{timestamp} {json.dumps(block)}\\n")

# Import the trading functions from trader
import trader

# Override the trader's database functions to use our connection manager
def logged_log_trade(symbol, side, price, quantity, profit=0):
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO trades (timestamp, action, symbol, price, size, value, portfolio_value)
                VALUES (?,?,?,?,?,?,?)
            ''', (timestamp, side, symbol, price, quantity, price*quantity, 100.0))
            conn.commit()
        finally:
            conn.close()

def logged_update_portfolio(cash, position, value):
    with db_lock:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    cash REAL,
                    position REAL,
                    value REAL
                )
            """)
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio (id, timestamp, cash, position, value)
                VALUES (1, ?, ?, ?, ?)
            """, (datetime.datetime.now().isoformat(), cash, position, value))
            # Also insert into equity_history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equity_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    value REAL
                )
            """)
            cursor.execute("""
                INSERT INTO equity_history (timestamp, value)
                VALUES (?, ?)
            """, (datetime.datetime.now().isoformat(), value))
            conn.commit()
        finally:
            conn.close()

# Replace the functions in the trader module
trader.log_trade = logged_log_trade
trader.update_portfolio = logged_update_portfolio

def init_db():
    """Initialize the database tables if they don't exist."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                action TEXT,
                symbol TEXT,
                price REAL,
                size REAL,
                value REAL,
                portfolio_value REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                cash REAL,
                position REAL,
                value REAL
            )
        """)
        # Insert default portfolio if not exists
        cursor.execute("INSERT OR IGNORE INTO portfolio (id, timestamp, cash, position, value) VALUES (1, ?, 100.0, 0.0, 100.0)", (datetime.datetime.now().isoformat(),))
        conn.commit()
    finally:
        conn.close()

DB_PATH   = '/root/ai_stock_trader/trading_data.db'
SYMBOLS   = ['AAPL','MSFT','TSLA','META','AMZN','NVDA','GOOGL']
INTERVAL  = 60
LOOKBACK_DAYS = 60

def _get_close_series(df):
    if df is None or df.empty:
        return None
    # Handle MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.droplevel(1)
    if 'Close' not in df.columns:
        return None
    s = df['Close']
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.astype(float)

def get_daily_close(ticker):
    df = yf.download(ticker, period=f'{LOOKBACK_DAYS}d', interval='1d', progress=False)
    return _get_close_series(df)

def compute_indicators(close_series):
    if len(close_series) < 50:  # Need at least 50 for slow SMA
        return None, None, None
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

def main():
    init_db()  # Ensure tables exist
    print("=" * 60)
    print("  🤖 AI MULTI-SYMBOL TRADER - LONG/SHORT VERSION")
    print("=" * 60)

    # Initialize positions tracking
    positions = {symbol: None for symbol in SYMBOLS}  # None, 'LONG', or 'SHORT'
    entry_prices = {symbol: 0.0 for symbol in SYMBOLS}

    while True:
        for symbol in SYMBOLS:
            try:
                close_series = get_daily_close(symbol)
                if close_series is None or len(close_series) < 50:
                    print(f"[{symbol}] Insufficient data")
                    continue

                sma_fast, sma_slow, rsi = compute_indicators(close_series)
                if sma_fast is None or sma_slow is None or rsi is None:
                    print(f"[{symbol}] Could not compute indicators")
                    continue

                price = close_series.iloc[-1]
                print(f"[{symbol}] Price: {price:.2f}, SMA10: {sma_fast:.2f}, SMA50: {sma_slow:.2f}, RSI: {rsi:.2f}")
                print(f"[{symbol}] DEBUG: sma_fast={sma_fast:.2f}, sma_slow={sma_slow:.2f}, rsi={rsi:.2f}")
                print(f"[{symbol}] DEBUG: bullish={sma_fast > sma_slow and rsi < 70}, bearish={sma_fast < sma_slow and rsi > 30}")

                # Trading logic
                if sma_fast > sma_slow and rsi < 70:  # Bullish
                    if positions[symbol] != 'LONG':
                        # Close short if open
                        if positions[symbol] == 'SHORT':
                            # Close the short position
                            # We don't have the original size, so we'll use a fixed size for closing
                            # In a real system, we'd track the size
                            pass  # Simplified for now

                        # Open long
                        cash = 100.0  # This is simplified - in reality we'd get from portfolio
                        size = cash / price  # Allow fractional shares
                        if size > 0:
                            print(f"[{symbol}] DECISION: LONG | Price: {price:.2f} | Size: {size:.4f} | RSI: {rsi:.2f}")
                            write_decision_block(f"SMA Cross Up + RSI < 70", 0.02, 0.7)
                            # Log the trade
                            from trader import log_trade
                            trader.log_trade(symbol, 'LONG', price, size)
                            positions[symbol] = 'LONG'
                            entry_prices[symbol] = price

                elif sma_fast < sma_slow and rsi > 30:  # Bearish
                    if positions[symbol] != 'SHORT':
                        # Close long if open
                        if positions[symbol] == 'LONG':
                            # Close the long position
                            pass  # Simplified for now

                        # Open short
                        cash = 100.0  # This is simplified
                        size = cash / price  # Allow fractional shares
                        if size > 0:
                            print(f"[{symbol}] DECISION: SHORT | Price: {price:.2f} | Size: {size:.4f} | RSI: {rsi:.2f}")
                            write_decision_block(f"SMA Cross Down + RSI > 30", 0.02, 0.7)
                            # Log the trade
                            from trader import log_trade
                            log_trade(symbol, 'SHORT', price, size)
                            positions[symbol] = 'SHORT'
                            entry_prices[symbol] = price

            except Exception as e:
                print(f"[{symbol}] Error: {e}")
                continue

        print(f"--- Cycle completed at {datetime.datetime.now()} ---")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()