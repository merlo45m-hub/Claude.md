#!/usr/bin/env python3
"""
Context.dev brand-enrichment client for the AI Stock Trader dashboard.

Enriches holding/watchlist tickers with brand logo + brand colors via the
Context.dev Web Context API (https://api.context.dev/v1/brand/retrieve).

Security note: the API key is NEVER read from chat or hardcoded. It is loaded
from (in order):
  1. CONTEXT_DEV_API_KEY environment variable
  2. /root/.config/context-dev/credentials.json  (field "api_key")
If neither is present, the client degrades gracefully (returns empty enrichment)
instead of crashing the dashboard.

Cost control: each /brand/retrieve call costs 10 Context.dev credits. We cache
results to a local JSON file (default 7-day TTL) so the dashboard does not burn
credits on every page load. Plan had ~234 credits at integration time.
"""
import os
import json
import time
import threading
import requests

API_BASE = "https://api.context.dev/v1"
CACHE_PATH = os.environ.get(
    "CONTEXT_DEV_CACHE_PATH",
    "/root/ai_stock_trader/.context_dev_brand_cache.json",
)
CACHE_TTL = int(os.environ.get("CONTEXT_DEV_CACHE_TTL", "604800"))  # 7 days
DEFAULT_CREDS = "/root/.config/context-dev/credentials.json"

_lock = threading.Lock()
_mem_cache = {}  # symbol -> {brand data, cached_at}


def _load_api_key():
    key = os.environ.get("CONTEXT_DEV_API_KEY")
    if key:
        return key
    try:
        if os.path.exists(DEFAULT_CREDS):
            with open(DEFAULT_CREDS) as f:
                return json.load(f).get("api_key")
    except Exception:
        return None
    return None


def _load_disk_cache():
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_disk_cache(cache):
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _logo_url(brand):
    """Pick a display-ready logo (light mode icon preferred)."""
    logos = brand.get("logos") or []
    for lg in logos:
        if lg.get("mode") == "light" and lg.get("type") == "icon":
            return lg.get("url")
    for lg in logos:
        if lg.get("url"):
            return lg.get("url")
    return None


def enrich_symbol(symbol):
    """
    Return brand enrichment for a single ticker symbol, or None on any failure.
    Shape: {domain, title, logo, colors:[{hex,name}], description}
    """
    api_key = _load_api_key()
    if not api_key:
        return None

    now = time.time()
    with _lock:
        disk = _load_disk_cache()
        cached = disk.get(symbol)
        if cached and (now - cached.get("cached_at", 0)) < CACHE_TTL:
            return cached.get("data")

    try:
        resp = requests.post(
            f"{API_BASE}/brand/retrieve",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"type": "by_ticker", "ticker": symbol},
            timeout=15,
        )
        if resp.status_code != 200:
            # Don't cache failures; allow retry later.
            return None
        brand = resp.json().get("brand") or {}
        data = {
            "domain": brand.get("domain"),
            "title": brand.get("title"),
            "logo": _logo_url(brand),
            "colors": [
                {"hex": c.get("hex"), "name": c.get("name")}
                for c in (brand.get("colors") or [])
                if c.get("hex")
            ],
            "description": brand.get("description"),
        }
        with _lock:
            disk = _load_disk_cache()
            disk[symbol] = {"cached_at": now, "data": data}
            _save_disk_cache(disk)
        return data
    except Exception:
        return None


def enrich_symbols(symbols):
    """Batch enrich. Returns {symbol: data|None}."""
    return {sym: enrich_symbol(sym) for sym in symbols}


if __name__ == "__main__":
    # Smoke test
    import sys
    syms = sys.argv[1:] or ["AAPL", "NVDA"]
    out = enrich_symbols(syms)
    print(json.dumps(out, indent=2))
