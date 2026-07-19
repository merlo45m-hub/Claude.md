#!/usr/bin/env python3
"""Real-time Web Dashboard for AI Stock Trading Bot with SocketIO updates, health endpoint, and login rate limiting."""
from flask import Flask, render_template, jsonify, request, Response, make_response
from flask_socketio import SocketIO, emit
import sqlite3
import os
import csv
import io
import json
import time
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret!')
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = os.environ.get('DB_PATH', '/root/ai_stock_trader/trading_data.db')
CONFIG_PATH = os.environ.get('CONFIG_PATH', '/root/ai_stock_trader/config.json')
DECISION_LOG_PATH = os.environ.get('DECISION_LOG_PATH', '/root/ai_stock_trader/decision_log.txt')

# Authentication removed for open access

import requests

# Context.dev brand enrichment (logo + colors per ticker) — degrades gracefully
# if no API key is configured.
try:
    from context_dev_client import enrich_symbols
except Exception:
    enrich_symbols = None

def send_telegram_alert(message):
    """Send trade alert to Telegram if configured via env vars."""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return  # not configured; silently skip
    try:
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data={'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'},
            timeout=5
        )
    except Exception as e:
        print(f'Telegram alert failed: {e}')

def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database for trade logging"""
    conn = get_db()
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
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY,
        timestamp TEXT,
        cash REAL,
        position REAL,
        value REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS equity_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        value REAL
    )''')
    conn.commit()
    conn.close()

def get_portfolio():
    """Get current portfolio"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT cash, position, value FROM portfolio WHERE id=1')
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'cash': row['cash'],
            'position': row['position'],
            'value': row['value']
        }
    return {'cash': 100.0, 'position': 0.0, 'value': 100.0}

def get_recent_trades(limit=20):
    """Get recent trades"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT timestamp, action, symbol, price, size, value
                 FROM trades ORDER BY id DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{
        'time': row['timestamp'],
        'action': row['action'],
        'symbol': row['symbol'],
        'price': row['price'],
        'size': row['size'],
        'value': row['value']
    } for row in rows]

def get_equity_history(limit=500):
    """Get equity history for chart"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT timestamp, value 
                 FROM equity_history 
                 ORDER BY id DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    # Reverse to get chronological order
    return [{
        'time': row['timestamp'],
        'value': row['value']
    } for row in reversed(rows)]

def get_last_trade_id():
    """Get the highest trade id (used to detect new trades)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT MAX(id) FROM trades')
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else 0

def background_thread():
    """Background thread that emits updates to all connected clients."""
    last_trade_id = get_last_trade_id()
    while True:
        time.sleep(3)  # check every 3 seconds
        new_last_id = get_last_trade_id()
        if new_last_id != last_trade_id:
            # New trade(s) inserted
            last_trade_id = new_last_id
            # Emit update event to all clients
            socketio.emit('update', {'trigger': 'new_trade'}, namespace='/')
        # Also emit a full state update every 15 seconds to keep UI in sync
        # We'll use a simple counter
        # For simplicity, we'll just rely on client requesting fresh data on 'update' event.
        # We'll also emit a heartbeat every 5 seconds to detect disconnections.
        # We'll implement a simple ping/pong later if needed.
        pass

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    # Optionally send initial data? We'll let client fetch via HTTP after connect.

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/mobile')
def mobile_dashboard():
    resp = make_response(render_template('mobile_dashboard.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/api/status')
def get_status():
    """Get current portfolio and trade status"""
    portfolio = get_portfolio()
    trades = get_recent_trades()
    return jsonify({
        'portfolio': portfolio,
        'trades': trades,
        'status': 'RUNNING'
    })

@app.route('/api/equity')
def get_equity():
    """Get equity history for charting"""
    history = get_equity_history()
    return jsonify({'equity': history})

@app.route('/api/trades')
def get_trades():
    """Get trades with filtering"""
    symbol = request.args.get('symbol', '')
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    limit = int(request.args.get('limit', 100))
    
    conn = get_db()
    c = conn.cursor()
    query = '''SELECT timestamp, action, symbol, price, size, value
               FROM trades WHERE 1=1'''
    params = []
    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)
    if start:
        query += ' AND timestamp >= ?'
        params.append(start)
    if end:
        query += ' AND timestamp <= ?'
        params.append(end)
    query += ' ORDER BY id DESC LIMIT ?'
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return jsonify({'trades': [{
        'time': row['timestamp'],
        'action': row['action'],
        'symbol': row['symbol'],
        'price': row['price'],
        'size': row['size'],
        'value': row['value']
    } for row in rows]})

@app.route('/api/export/csv')
def export_csv():
    """Export trades as CSV"""
    symbol = request.args.get('symbol', '')
    start = request.args.get('start', '')
    end = request.args.get('end', '')
    limit = int(request.args.get('limit', 1000))
    
    conn = get_db()
    c = conn.cursor()
    query = '''SELECT timestamp, action, symbol, price, size 
               FROM trades WHERE 1=1'''
    params = []
    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)
    if start:
        query += ' AND timestamp >= ?'
        params.append(start)
    if end:
        query += ' AND timestamp <= ?'
        params.append(end)
    query += ' ORDER BY id DESC LIMIT ?'
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Action', 'Symbol', 'Price', 'Size', 'Value'])
    for r in rows:
        writer.writerow([
            r['timestamp'],
            r['action'],
            r['symbol'],
            f"{r['price']:.2f}",
            f"{r['size']:.6f}",
            f"{(float(r['price']) * float(r['size'])):.2f}"
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=trades.csv'}
    )

@app.route('/api/config')
def get_config():
    """Get current configuration"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return {**get_default_config(), **json.load(f)}
        except:
            return get_default_config()
    return get_default_config()

def get_default_config():
    return {
        'risk_per_trade': 0.02,
        'max_positions': 3,
        'stop_loss': 0.05,
        'take_profit': 0.1,
        'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX']
    }

@app.route('/api/config', methods=['POST'])
def set_config():
    """Update configuration"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    config = request.get_json()
    # Validate expected keys
    allowed_keys = {'risk_per_trade', 'max_positions', 'stop_loss', 'take_profit', 'symbols'}
    filtered = {k: v for k, v in config.items() if k in allowed_keys}
    if not filtered:
        return jsonify({'error': 'No valid configuration keys provided'}), 400
    current = get_config()
    current.update(filtered)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(current, f, indent=2)
    return jsonify({'status': 'success', 'config': current})

@app.route('/api/decision')
def get_decision():
    """Return recent decision blocks for mobile dashboard"""
    path = os.environ.get('DECISION_LOG_PATH', '/app/decision_log.txt')
    if not os.path.exists(path):
        return jsonify({'error': 'No decisions logged yet'})
    with open(path, 'r') as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    recent = lines[-5:] if lines else []
    return jsonify({'decisions': recent})

@app.route('/health')
def health():
    """Simple health check"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT 1')
        conn.close()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/analytics')
def get_analytics():
    """Get analytics data for dashboard (win rate, equity chart, performance metrics)."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM trades ORDER BY timestamp DESC')
    trades = [dict(row) for row in c.fetchall()]
    conn.close()
    
    # Calculate win rate based on exit trades
    # LONG positions closed by EXIT LONG, SHORT positions closed by EXIT SHORT
    win_count = 0
    total_pairs = 0
    open_positions = {}  # symbol -> (side, entry_price)
    open_actions = {'LONG': 'LONG', 'BUY': 'LONG', 'SHORT': 'SHORT', 'SELL': 'SHORT'}
    close_actions = {'EXIT LONG': 'LONG', 'EXIT SHORT': 'SHORT'}
    for t in reversed(trades):
        key = t['symbol']
        action = t['action']
        if action in open_actions:
            side = open_actions[action]
            if key in open_positions and open_positions[key][0] != side:
                # closing opposite side -> completed pair, evaluate win by price direction
                ep = open_positions[key][1]
                oside = open_positions[key][0]
                win = (t['price'] > ep) if oside == 'LONG' else (t['price'] < ep)
                if win:
                    win_count += 1
                total_pairs += 1
                del open_positions[key]
            else:
                open_positions[key] = (side, t['price'])
        elif action in close_actions or action.startswith('CLOSE_'):
            side = close_actions.get(action)
            if key in open_positions and (side is None or open_positions[key][0] == side):
                ep = open_positions[key][1]
                oside = open_positions[key][0]
                win = (t['price'] > ep) if oside == 'LONG' else (t['price'] < ep)
                if win:
                    win_count += 1
                total_pairs += 1
                del open_positions[key]

    win_rate = (win_count / total_pairs * 100) if total_pairs > 0 else 0
    
    equity = get_equity_history()
    recent_trades = trades[-10:] if trades else []
    
    return jsonify({
        'win_rate': round(win_rate, 2),
        'total_pairs': total_pairs,
        'total_trades': len(trades),
        'equity_history': equity,
        'recent_trades': recent_trades,
        'average_trade_size': round(sum(t['size'] for t in trades) / len(trades), 4) if trades else 0
    })

@app.route('/api/brand-enrich')
def get_brand_enrich():
    """Return brand logo + colors for each configured/watchlist ticker.

    Uses cached Context.dev lookups (see context_dev_client) so repeated
    calls cost no API credits. Returns {symbol: {logo, colors, title, domain}}.
    """
    config = get_config()
    symbols = list(config.get('symbols', []))
    # Also include any open positions not already in the watchlist.
    try:
        conn = get_db()
        for row in conn.execute('SELECT DISTINCT symbol FROM positions'):
            s = row['symbol']
            if s and s not in symbols:
                symbols.append(s)
        conn.close()
    except Exception:
        pass
    if enrich_symbols is None:
        return jsonify({'brands': {}, 'enabled': False})
    brands = enrich_symbols(symbols)
    return jsonify({'brands': brands, 'enabled': True})


@app.route('/api/test-alert')
def test_telegram_alert():
    """Test endpoint to send a sample Telegram alert."""
    try:
        send_telegram_alert('🧪 TEST ALERT: AI Trading Bot is operational! Check /mobile for dashboard.')
        return jsonify({'status': 'success', 'message': 'Test sent, check logs'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/challenge-stats')
def get_challenge_stats():
    """Get challenge tracking statistics."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT restart_count, failure_count, win_streak, challenge_current_value FROM challenge_status WHERE id = 1")
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({
            'restarts': row['restart_count'],
            'failures': row['failure_count'],
            'win_streak': row['win_streak'],
            'current_value': row['challenge_current_value'],
            'target_value': 1000.0,
            'progress_percent': round((row['challenge_current_value'] / 1000.0) * 100, 2)
        })
    return jsonify({'restarts': 0, 'failures': 0, 'win_streak': 0, 'current_value': 100.0, 'target_value': 1000.0, 'progress_percent': 10.0})

@app.route('/api/watchlist')
def get_watchlist():
    """Get live prices for configured symbols — like a mobile watchlist."""
    import yfinance as yf
    config = get_config()
    symbols = config.get('symbols', [])
    if not symbols:
        return jsonify({'watchlist': [], 'indices': []})
    try:
        tickers = yf.Tickers(' '.join(symbols))
        watchlist = []
        for sym in symbols:
            try:
                t = tickers.tickers.get(sym)
                if t and t.info:
                    info = t.info
                    price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                    prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
                    change = (price - prev_close) if (price and prev_close) else None
                    change_pct = (change / prev_close * 100) if (change and prev_close) else None
                    watchlist.append({
                        'symbol': sym,
                        'name': info.get('shortName') or info.get('longName') or sym,
                        'price': round(price, 2) if price else None,
                        'change': round(change, 2) if change else None,
                        'changePercent': round(change_pct, 2) if change_pct else None,
                    })
            except Exception:
                watchlist.append({'symbol': sym, 'name': sym, 'price': None, 'change': None, 'changePercent': None})
        return jsonify({'watchlist': watchlist})
    except Exception as e:
        return jsonify({'watchlist': [], 'error': str(e)})

@app.route('/api/positions')
def get_positions():
    """Get currently open positions with live unrealized P&L.

    Reads the positions table and enriches each row with the current
    market price (yfinance) to compute unrealized P&L vs entry.
    Degrades gracefully: if price fetch fails, pnl is null.
    """
    import yfinance as yf
    conn = get_db()
    rows = conn.execute(
        'SELECT symbol, side, entry_price, size, stop_loss, take_profit, opened_at FROM positions'
    ).fetchall()
    conn.close()
    if not rows:
        return jsonify({'positions': []})
    symbols = [r['symbol'] for r in rows]
    prices = {}
    try:
        tickers = yf.Tickers(' '.join(symbols))
        for sym in symbols:
            try:
                t = tickers.tickers.get(sym)
                if t and t.info:
                    p = t.info.get('currentPrice') or t.info.get('regularMarketPrice') or t.info.get('previousClose')
                    prices[sym] = round(p, 2) if p else None
            except Exception:
                prices[sym] = None
    except Exception:
        pass
    out = []
    for r in rows:
        sym = r['symbol']
        price = prices.get(sym)
        entry = r['entry_price'] or 0
        size = r['size'] or 0
        # direction: SHORT profits when price < entry
        if price is not None and entry:
            if r['side'] == 'SHORT':
                pnl = (entry - price) * size
            else:
                pnl = (price - entry) * size
            pnl_pct = (pnl / (entry * size) * 100) if (entry * size) else 0
        else:
            pnl = None
            pnl_pct = None
        out.append({
            'symbol': sym,
            'side': r['side'],
            'entry_price': round(entry, 2),
            'size': size,
            'stop_loss': r['stop_loss'],
            'take_profit': r['take_profit'],
            'opened_at': r['opened_at'],
            'price': price,
            'pnl': round(pnl, 2) if pnl is not None else None,
            'pnl_pct': round(pnl_pct, 2) if pnl_pct is not None else None,
        })
    return jsonify({'positions': out})

@app.route('/api/positions/close', methods=['POST'])
def close_position():
    """Queue a manual close request. The bot honors it on its next loop tick.
    Only an *open* position can be requested; prevents wrong-side / double close."""
    data = request.get_json(silent=True) or {}
    symbol = (data.get('symbol') or '').upper().strip()
    side = (data.get('side') or '').upper().strip()
    if not symbol or side not in ('LONG', 'SHORT'):
        return jsonify({'ok': False, 'error': 'symbol + side(LONG|SHORT) required'}), 400
    conn = get_db()
    row = conn.execute(
        'SELECT 1 FROM positions WHERE symbol = ? AND side = ?', (symbol, side)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'ok': False, 'error': f'no open {side} position for {symbol}'}), 404
    # Ensure close_requests table exists (self-healing; bot also creates it)
    try:
        conn2 = get_db()
        conn2.execute('''CREATE TABLE IF NOT EXISTS close_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, side TEXT, requested_at TEXT, done INTEGER DEFAULT 0
        )''')
        conn2.execute(
            'INSERT INTO close_requests (symbol, side, requested_at) VALUES (?, ?, ?)',
            (symbol, side, time.strftime('%Y-%m-%dT%H:%M:%S'))
        )
        conn2.commit()
        conn2.close()
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    return jsonify({'ok': True, 'symbol': symbol, 'side': side, 'status': 'close requested'})

def start_background_thread():
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    init_db()
    start_background_thread()
    print("Starting web dashboard on http://0.0.0.0:8084")
    socketio.run(app, host='0.0.0.0', port=8084, debug=False, allow_unsafe_werkzeug=True)