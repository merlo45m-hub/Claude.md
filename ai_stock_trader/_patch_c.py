#!/usr/bin/env python3
"""Apply code fixes C1/C2/C3 to ai_stock_trader. Backs up each file to .bak."""
import os

BASE = '/root/ai_stock_trader'

def patch_file(path, replacements):
    """replacements: list of (old, new). old must be unique."""
    with open(path) as f:
        src = f.read()
    bak = path + '.bak'
    if not os.path.exists(bak):
        with open(bak, 'w') as f:
            f.write(src)
    for old, new in replacements:
        cnt = src.count(old)
        if cnt != 1:
            raise SystemExit(f"[{path}] expected 1 match, found {cnt} for:\n{old[:140]}")
        src = src.replace(old, new)
    with open(path, 'w') as f:
        f.write(src)
    print(f"patched {path}")

# ---------- C2a + C1: web_dashboard.py ----------
wd = os.path.join(BASE, 'web_dashboard.py')

# get_recent_trades: include value
wd1_old = """    c.execute('''SELECT timestamp, action, symbol, price, size 
                 FROM trades ORDER BY id DESC LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [{
        'time': row['timestamp'],
        'action': row['action'],
        'symbol': row['symbol'],
        'price': row['price'],
        'size': row['size']
    } for row in rows]"""
wd1_new = """    c.execute('''SELECT timestamp, action, symbol, price, size, value
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
    } for row in rows]"""

# /api/trades: full block incl SELECT + dict (unique tail = return jsonify)
wd2_old = """    query = '''SELECT timestamp, action, symbol, price, size 
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
        'size': row['size']
    } for row in rows]})"""
wd2_new = """    query = '''SELECT timestamp, action, symbol, price, size, value
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
    } for row in rows]})"""

# C1: analytics win_rate pairing (replace the broken block)
wd4_old = """    win_count = 0
    total_pairs = 0
    open_positions = {}
    for t in reversed(trades):
        key = t['symbol']
        action = t['action']
        
        # Entry actions
        if action in ('LONG', 'BUY'):
            if key in open_positions and open_positions[key] == 'SHORT':
                # Exit SHORT position - this is a completed pair
                total_pairs += 1
                del open_positions[key]
            else:
                open_positions[key] = 'LONG'
        elif action in ('SHORT', 'SELL'):
            if key in open_positions and open_positions[key] == 'LONG':
                # Exit LONG position - this is a completed pair
                total_pairs += 1
                del open_positions[key]
            else:
                open_positions[key] = 'SHORT'
        # Exit actions 
        elif action == 'EXIT LONG':
            if key in open_positions and open_positions[key] == 'LONG':
                total_pairs += 1
                del open_positions[key]
        elif action == 'EXIT SHORT':
            if key in open_positions and open_positions[key] == 'SHORT':
                total_pairs += 1
                del open_positions[key]
    
    win_rate = (win_count / total_pairs * 100) if total_pairs > 0 else 0"""
wd4_new = """    win_count = 0
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

    win_rate = (win_count / total_pairs * 100) if total_pairs > 0 else 0"""

patch_file(wd, [(wd1_old, wd1_new), (wd2_old, wd2_new), (wd4_old, wd4_new)])

# ---------- C2b: mobile_dashboard.html ----------
md = os.path.join(BASE, 'templates', 'mobile_dashboard.html')
md_old = """    const trades = t && t.trades ? t.trades : (Array.isArray(t)?t:[]);
    $('#trades').innerHTML = trades.slice(0,15).map(trade => {
      const ts = trade.time ? trade.time.replace('T',' ').slice(0,16) : '';
      const pnlVal = trade.pnl||0;
      const pnlSign = pnlVal>=0?'+':'';
      const pnlColor = pnlVal>=0?'pos':'neg';
      return `<div class="trade"><div><span class="sym">${trade.symbol||'?'}</span><span class="tag ${trade.action}">${trade.action}</span></div><div class="meta">${ts}<br><b class="${pnlColor}">${pnlSign}$${Math.abs(pnlVal).toFixed(2)}</b></div></div>`;
    }).join('');"""
md_new = """    const trades = t && t.trades ? t.trades : (Array.isArray(t)?t:[]);
    $('#trades').innerHTML = trades.slice(0,15).map(trade => {
      const ts = trade.time ? trade.time.replace('T',' ').slice(0,16) : '';
      const px = trade.price!=null ? '$'+Number(trade.price).toFixed(2) : '--';
      const val = trade.value!=null ? '$'+Number(trade.value).toFixed(2) : '--';
      return `<div class="trade"><div><span class="sym">${trade.symbol||'?'}</span><span class="tag ${trade.action}">${trade.action}</span></div><div class="meta">${ts}<br>px ${px} · val ${val}</div></div>`;
    }).join('');"""
patch_file(md, [(md_old, md_new)])

# ---------- C3: unified_strategy.py ----------
us = os.path.join(BASE, 'unified_strategy.py')
us_ins_anchor = """db_lock = Lock()
"""
us_ins_code = """db_lock = Lock()

def safe_download(symbol, period='60d', interval='1d', max_retries=3):
    \"\"\"Download OHLCV with yfinance retry/backoff and a stooq CSV fallback.

    Yahoo frequently rate-limits / blocks datacenter IPs, which left the bot
    spinning with zero trades. stooq.com serves free daily CSV with no auth.
    \"\"\"
    last_err = None
    for attempt in range(max_retries):
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            last_err = e
        time.sleep(2 * (attempt + 1))
    # Fallback: stooq daily CSV (datacenter-IP friendly). Append .us for US ticks.
    try:
        s = symbol.lower() + '.us'
        url = f'https://stooq.com/q/d/l/?s={s}&i=d'
        df = pd.read_csv(url)
        if df is not None and not df.empty and 'Close' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
            return df
    except Exception:
        pass
    print(f"[safe_download] {symbol} failed after retries: {last_err}")
    return None
"""
us_r1_old = "df = yf.download(symbol, period=f'{lookback_days}d', interval='1d', progress=False)"
us_r1_new = "df = safe_download(symbol, period=f'{lookback_days}d', interval='1d')"
us_r2_old = "df = yf.download('VXX', period='5d', interval='1d', progress=False)"
us_r2_new = "df = safe_download('VXX', period='5d', interval='1d')"

with open(us) as f:
    src = f.read()
bak = us + '.bak'
if not os.path.exists(bak):
    with open(bak, 'w') as f:
        f.write(src)
if src.count(us_ins_anchor) != 1:
    raise SystemExit("anchor for safe_download insert not unique")
src = src.replace(us_ins_anchor, us_ins_code, 1)
for old, new in [(us_r1_old, us_r1_new), (us_r2_old, us_r2_new)]:
    if src.count(old) != 1:
        raise SystemExit(f"yf.download replace count !=1: {old}")
    src = src.replace(old, new)
with open(us, 'w') as f:
    f.write(src)
print(f"patched {us}")

print("ALL PATCHES APPLIED")
