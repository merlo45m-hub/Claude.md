from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.config import AppConfig, load_config

# Context.dev brand enrichment (logo + colors per crypto pair). Degrades to {}
# when no API key / credits available.
try:
    from context_dev_client import enrich_symbols
except Exception:
    enrich_symbols = None

app = FastAPI(title="AI Crypto Bot — Dashboard")
_config: AppConfig | None = None

_AUTH_REALM = "AI Crypto Bot"


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"error": "Unauthorized"},
        headers={"WWW-Authenticate": f'Basic realm="{_AUTH_REALM}"'},
    )


def _check_auth(request: Request) -> bool:
    if _config is None or not _config.web.password:
        return True  # no password configured = no auth
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth.removeprefix("Basic ")).decode("utf-8")
        _, password = decoded.split(":", 1)
    except Exception:
        return False
    return password == _config.web.password


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.method != "OPTIONS" and not _check_auth(request):
        return _unauthorized()
    return await call_next(request)


def _get_db() -> sqlite3.Connection | None:
    if _config is None or not _config.trading.db_path:
        return None
    path = _config.trading.db_path
    if not Path(path).exists():
        return None
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _get_cursor():
    db = _get_db()
    if db is None:
        return None
    db.row_factory = sqlite3.Row
    return db


def _compute_position_equity(
    pos: dict, prices: dict[str, float]
) -> dict:
    sym = pos.get("symbol", "")
    price = prices.get(sym)
    if price is None:
        return {"unrealized_pnl": 0.0, "current_value": 0.0, "pnl_pct": 0.0, "current_price": 0.0}
    size = pos.get("size", 0)
    entry = pos.get("price")
    if entry is None:
        return {"unrealized_pnl": 0.0, "current_value": 0.0, "pnl_pct": 0.0, "current_price": round(price, 2)}
    direction = pos.get("direction", "long")
    if direction == "long":
        unrealized = (price - entry) * size
        value = size * price
        pnl_pct = ((price - entry) / entry * 100) if entry else 0.0
    else:
        unrealized = (entry - price) * size
        value = -(size * price)
        pnl_pct = ((entry - price) / entry * 100) if entry else 0.0
    return {
        "unrealized_pnl": round(unrealized, 2),
        "current_value": round(value, 2),
        "pnl_pct": round(pnl_pct, 2),
        "current_price": round(price, 2),
    }


def _load_json_state(db, key: str) -> dict:
    cursor = db.execute("SELECT value FROM state WHERE key = ?", (key,))
    row = cursor.fetchone()
    return json.loads(row["value"]) if row else {}


def _load_float_state(db, key: str, default: float = 0.0) -> float:
    cursor = db.execute("SELECT value FROM state WHERE key = ?", (key,))
    row = cursor.fetchone()
    return float(row["value"]) if row else default


@app.get("/api/summary")
async def summary():
    db = _get_cursor()
    if db is None:
        return {"error": "No database configured"}
    try:
        cursor = db.execute("SELECT COUNT(*), COALESCE(SUM(pnl), 0) FROM trades")
        count, realized_pnl = cursor.fetchone()

        cash = _load_float_state(db, "balance")
        initial_capital = _load_float_state(db, "initial_capital", 1000.0)
        positions_data = _load_json_state(db, "positions")
        prices = _load_json_state(db, "prices")
        open_positions = len(positions_data)

        unrealized_pnl = 0.0
        position_value_sum = 0.0
        for pos in positions_data.values():
            info = _compute_position_equity(pos, prices)
            unrealized_pnl += info["unrealized_pnl"]
            position_value_sum += info["current_value"]

        total_pnl = round(realized_pnl + unrealized_pnl, 2)
        equity = round(cash + position_value_sum, 2)
        total_return_pct = round(
            ((equity - initial_capital) / initial_capital * 100) if initial_capital else 0.0,
            2,
        )

        wins = db.execute("SELECT COUNT(*) FROM trades WHERE pnl > 0").fetchone()[0]
        win_rate = (wins / count * 100) if count > 0 else 0.0

        return {
            "trade_count": count,
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": total_pnl,
            "total_return_pct": total_return_pct,
            "cash": round(cash, 2),
            "equity": equity,
            "initial_capital": round(initial_capital, 2),
            "open_positions": open_positions,
            "win_rate": round(win_rate, 1),
        }
    finally:
        db.close()


@app.get("/api/challenge")
async def challenge():
    db = _get_cursor()
    if db is None:
        return {"restarts": 0, "failures": 0, "start": "", "target": 1000.0, "equity": 0, "progress_pct": 0, "days_left": 30}
    try:
        def _sv(key: str, default='0') -> str:
            row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
            return str(row['value']) if row else default
        restarts = int(_sv('challenge_restarts'))
        failures = int(_sv('challenge_failures'))
        start = _sv('challenge_start', '')
        target = float(_sv('challenge_target', '1000.0'))
        cash = float(_sv('balance', '0'))
        prices = json.loads(_sv('prices', '{}'))
        positions = json.loads(_sv('positions', '{}'))
        pos_value = 0.0
        for sym, pos in positions.items():
            price = prices.get(sym, 0)
            entry = pos.get('price', 0)
            size = pos.get('size', 0)
            direction = pos.get('direction', 'long')
            if direction == 'long':
                pos_value += size * price
            else:
                pos_value -= size * price
        equity = round(cash + pos_value, 2)
        init = float(_sv('initial_capital', '100.0'))
        progress_pct = round((equity / target) * 100, 1) if target else 0
        days_left = 0
        if start:
            from datetime import date, datetime
            try:
                started = datetime.strptime(start, '%Y-%m-%d').date()
                days_left = max(0, 30 - (date.today() - started).days)
            except: pass
        return {
            "restarts": restarts, "failures": failures, "start": start or "",
            "target": target, "equity": equity, "initial": init,
            "progress_pct": progress_pct, "days_left": days_left,
        }
    finally:
        db.close()

@app.get("/api/trades")
async def trades(limit: int = 50):
    db = _get_cursor()
    if db is None:
        return {"trades": []}
    try:
        cursor = db.execute(
            "SELECT * FROM trades ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return {"trades": [dict(r) for r in cursor.fetchall()]}
    finally:
        db.close()


@app.get("/api/positions")
async def positions():
    db = _get_cursor()
    if db is None:
        return {"positions": []}
    try:
        raw = _load_json_state(db, "positions")
        if not raw:
            return {"positions": []}
        prices = _load_json_state(db, "prices")

        enriched = []
        for sym, pos in raw.items():
            info = _compute_position_equity(pos, prices)
            enriched.append({
                "symbol": sym,
                "direction": pos.get("direction"),
                "entry_price": round(pos.get("price", 0), 2),
                "size": round(pos.get("size", 0), 6),
                "current_price": info["current_price"],
                "unrealized_pnl": info["unrealized_pnl"],
                "pnl_pct": info["pnl_pct"],
                "current_value": info["current_value"],
            })

        return {"positions": enriched}
    finally:
        db.close()


@app.get("/api/bot-status")
async def bot_status():
    db = _get_cursor()
    if db is None:
        return {"alive": False, "error": "No database"}
    try:
        cursor = db.execute("SELECT value FROM state WHERE key = 'heartbeat'")
        row = cursor.fetchone()
        heartbeat_str = row["value"] if row else ""
        cursor = db.execute("SELECT value FROM state WHERE key = 'next_run_at'")
        row = cursor.fetchone()
        next_run_at = row["value"] if row else ""
        cursor = db.execute("SELECT * FROM cycle_log ORDER BY id DESC LIMIT 10")
        recent_cycles = [dict(r) for r in cursor.fetchall()]
        return {
            "alive": True,
            "heartbeat": heartbeat_str,
            "next_run_at": next_run_at,
            "recent_cycles": recent_cycles,
        }
    finally:
        db.close()


@app.get("/api/prices")
async def current_prices():
    db = _get_cursor()
    if db is None:
        return {"prices": {}}
    try:
        return {"prices": _load_json_state(db, "prices")}
    finally:
        db.close()


@app.get("/api/market")
async def market():
    db = _get_cursor()
    if db is None:
        return {"signals": []}
    try:
        signals = []
        cursor = db.execute(
            "SELECT * FROM signal_log WHERE cycle_id = "
            "(SELECT MAX(cycle_id) FROM signal_log) ORDER BY symbol",
        )
        for row in cursor.fetchall():
            d = dict(row)
            if d["signal"] == "buy":
                direction = "\U0001f7e2 BUY"
            elif d["signal"] == "sell":
                direction = "\U0001f534 SELL"
            else:
                direction = "\u26aa HOLD"
            d["display"] = direction
            signals.append(d)
        return {"signals": signals}
    finally:
        db.close()


@app.get("/api/ohlc")
async def ohlc(symbol: str = "BTC/USDT", limit: int = 100):
    db = _get_cursor()
    if db is None:
        return {"points": []}
    try:
        cursor = db.execute(
            "SELECT id, timestamp, open, high, low, close, volume FROM ohlc_snapshots "
            "WHERE symbol = ? ORDER BY id ASC LIMIT ?",
            (symbol, limit),
        )
        return {"points": [dict(r) for r in cursor.fetchall()], "symbol": symbol}
    finally:
        db.close()


@app.get("/api/prices/history")
async def price_history(symbol: str = "BTC/USDT", limit: int = 100):
    db = _get_cursor()
    if db is None:
        return {"points": []}
    try:
        cursor = db.execute(
            "SELECT id, timestamp, price FROM price_history "
            "WHERE symbol = ? ORDER BY id ASC LIMIT ?",
            (symbol, limit),
        )
        return {"points": [dict(r) for r in cursor.fetchall()], "symbol": symbol}
    finally:
        db.close()


@app.get("/api/alerts")
async def alerts(limit: int = 20):
    db = _get_cursor()
    if db is None:
        return {"alerts": []}
    try:
        cursor = db.execute(
            "SELECT * FROM alert_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return {"alerts": [dict(r) for r in cursor.fetchall()]}
    finally:
        db.close()


@app.get("/api/equity")
async def equity():
    db = _get_cursor()
    if db is None:
        return {"points": []}
    try:
        cursor = db.execute(
            "SELECT id, timestamp, equity, cash FROM equity_snapshots ORDER BY id ASC",
        )
        snapshots = [dict(r) for r in cursor.fetchall()]

        if not snapshots:
            cursor = db.execute("SELECT value FROM state WHERE key = 'balance'")
            row = cursor.fetchone()
            cash = float(row["value"]) if row else 1000.0
            return {
                "points": [{"equity": round(cash, 2), "cash": round(cash, 2)}],
                "current_equity": round(cash, 2),
            }

        return {
            "points": snapshots,
            "current_equity": snapshots[-1]["equity"],
        }
    finally:
        db.close()


@app.get("/api/strategy")
async def strategy_info():
    """Return latest market regime, ATR, and trend bias from OHLC data."""
    db = _get_cursor()
    if db is None:
        return {"regime": "unknown", "bias": {}, "atr": {}}
    try:
        symbols = _load_json_state(db, "prices").keys()
        if not symbols:
            return {"regime": "unknown", "bias": {}, "atr": {}}

        biases = {}
        atrs = {}
        regimes = set()

        for sym in symbols:
            cursor = db.execute(
                "SELECT open, high, low, close, volume FROM ohlc_snapshots "
                "WHERE symbol = ? ORDER BY id DESC LIMIT 200",
                (sym,),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if len(rows) < 30:
                continue

            closes = [r["close"] for r in rows]
            highs = [r["high"] for r in rows]
            lows = [r["low"] for r in rows]

            # Simple ATR (14-period)
            tr_values = []
            for i in range(1, min(15, len(rows))):
                hl = highs[i] - lows[i]
                hc = abs(highs[i] - closes[i - 1])
                lc = abs(lows[i] - closes[i - 1])
                tr_values.append(max(hl, hc, lc))
            atr = sum(tr_values) / len(tr_values) if tr_values else 0
            atr_pct = (atr / closes[0] * 100) if closes[0] else 0
            atrs[sym] = {"atr": round(atr, 2), "atr_pct": round(atr_pct, 2)}

            # Simple ADX (14-period)
            period = 14
            if len(rows) > period + 5:
                up_moves = []
                dn_moves = []
                tr_vals = []
                for i in range(1, period + 1):
                    up = highs[i] - highs[i - 1]
                    dn = lows[i - 1] - lows[i]
                    up_moves.append(max(up, 0) if up > dn else 0)
                    dn_moves.append(max(dn, 0) if dn > up else 0)
                    hl = highs[i] - lows[i]
                    hc = abs(highs[i] - closes[i - 1])
                    lc = abs(lows[i] - closes[i - 1])
                    tr_vals.append(max(hl, hc, lc))

                avg_tr = sum(tr_vals) / period
                plus_di = 100 * (sum(up_moves) / period) / avg_tr if avg_tr > 0 else 0
                minus_di = 100 * (sum(dn_moves) / period) / avg_tr if avg_tr > 0 else 0
                dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0

                if atr_pct > 5 and dx > 25:
                    regimes.add("volatile")
                elif dx > 25:
                    regimes.add("trending")
                else:
                    regimes.add("ranging")

                # Trend bias
                sma_fast = sum(closes[:5]) / 5
                sma_slow = sum(closes[:15]) / 15
                price_vs_sma = closes[0] > sma_slow
                sma_bull = sma_fast > sma_slow
                if sma_bull and price_vs_sma:
                    biases[sym] = "bullish"
                elif not sma_bull and not price_vs_sma:
                    biases[sym] = "bearish"
                else:
                    biases[sym] = "neutral"

        regime = "trending" if len(regimes) == 1 and "trending" in regimes else \
                 "volatile" if "volatile" in regimes else \
                 "ranging" if "ranging" in regimes else "mixed"

        return {"regime": regime, "biases": biases, "atr": atrs}
    finally:
        db.close()


@app.get("/api/brand-enrich")
async def brand_enrich():
    """Brand logo + colors per configured crypto pair.

    Cached/fallback lookups only (context_dev_client) — no live API cost, no DB
    access, so it never blocks the event loop.
    """
    if enrich_symbols is None:
        return {"brands": {}, "enabled": False}
    symbols = list(_config.trading.symbols) if _config else []
    return {"brands": enrich_symbols(symbols), "enabled": True}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html = Path(__file__).parent / "templates" / "index.html"
    if not html.exists():
        return HTMLResponse("<h1>Dashboard template not found</h1>", status_code=404)
    return HTMLResponse(html.read_text())


def start_server(config: AppConfig) -> None:
    global _config
    _config = config
    import uvicorn
    uvicorn.run(
        app,
        host=config.web.host,
        port=config.web.port,
        log_level="info",
    )


if __name__ == "__main__":
    cfg = load_config()
    start_server(cfg)
