#!/usr/bin/env python3
"""
Context.dev brand-enrichment client for the AI Crypto Bot dashboard.

Enriches held/monitored crypto pairs (e.g. BTC/USDT) with brand logo + colors
via the Context.dev Web Context API. Crypto pairs have no stock ticker, so we
map the base asset to its common name (Bitcoin, Ethereum, Solana, ...) and look
it up with type=by_name. Unknown assets fall back to by_name of the base ticker.

Security: API key loaded from CONTEXT_DEV_API_KEY env or
/root/.config/context-dev/credentials.json. Never hardcoded.

Cost control: each lookup costs 10 Context.dev credits; results cached to a local
JSON file (7-day TTL) so the dashboard does not burn credits on every reload.
"""
import os
import json
import time
import threading
import requests

API_BASE = "https://api.context.dev/v1"
CACHE_PATH = os.environ.get(
    "CONTEXT_DEV_CACHE_PATH",
    "/root/ai-crypto-bot/.context_dev_brand_cache.json",
)
CACHE_TTL = int(os.environ.get("CONTEXT_DEV_CACHE_TTL", "604800"))  # 7 days
DEFAULT_CREDS = "/root/.config/context-dev/credentials.json"

# base asset -> brand lookup name (Context.dev by_name)
COIN_NAMES = {
    "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "BNB": "Binance",
    "XRP": "Ripple", "DOGE": "Dogecoin", "TRX": "TRON", "HYPE": "Hyperliquid",
    "ZEC": "Zcash", "XLM": "Stellar", "XMR": "Monero", "LINK": "Chainlink",
    "ADA": "Cardano", "USDT": "Tether", "USDC": "USD Coin", "AVAX": "Avalanche",
    "MATIC": "Polygon", "DOT": "Polkadot", "LTC": "Litecoin", "ATOM": "Cosmos",
    "UNI": "Uniswap", "ARB": "Arbitrum", "OP": "Optimism", "NEAR": "NEAR Protocol",
    "APT": "Aptos", "SUI": "Sui", "TON": "Toncoin", "PEPE": "Pepe",
    "SHIB": "Shiba Inu", "WIF": "dogwifhat", "INJ": "Injective",
}

_lock = threading.Lock()

# Last-resort fallback: stable public logo URLs + iconic brand color per coin.
# Used when the Context.dev API returns nothing (e.g. no credits) so the
# dashboard still shows logos. Keyed by base asset.
FALLBACK_BRANDS = {
    "BTC":  ("https://assets.coingecko.com/coins/images/1/small/bitcoin.png",      "#f7931a", "Bitcoin"),
    "ETH":  ("https://assets.coingecko.com/coins/images/279/small/ethereum.png",   "#627eea", "Ethereum"),
    "SOL":  ("https://assets.coingecko.com/coins/images/4128/small/solana.png",    "#14f195", "Solana"),
    "BNB":  ("https://assets.coingecko.com/coins/images/825/small/bnb-icon2_2x.png","#f0b90b", "BNB"),
    "XRP":  ("https://assets.coingecko.com/coins/images/44/small/xrp-symbol-white-128.png", "#23292f", "XRP"),
    "DOGE": ("https://assets.coingecko.com/coins/images/5/small/dogecoin.png",      "#c2a633", "Dogecoin"),
    "TRX":  ("https://assets.coingecko.com/coins/images/1094/small/tron-logo.png",  "#eb0029", "TRON"),
    "HYPE": ("https://assets.coingecko.com/coins/images/50882/small/hyperliquid.jpg","#97fce4", "Hyperliquid"),
    "ZEC":  ("https://assets.coingecko.com/coins/images/486/small/circle-zcash-color.png", "#f4b728", "Zcash"),
    "XLM":  ("https://assets.coingecko.com/coins/images/100/small/Stellar_symbol_black_RGB.png", "#000000", "Stellar"),
    "XMR":  ("https://assets.coingecko.com/coins/images/69/small/monero_logo.png",  "#ff6600", "Monero"),
    "LINK": ("https://assets.coingecko.com/coins/images/877/small/chainlink-new-logo.png", "#2a5ada", "Chainlink"),
    "ADA":  ("https://assets.coingecko.com/coins/images/975/small/cardano.png",     "#0033ad", "Cardano"),
}


def _fallback(symbol):
    base = _base_asset(symbol)
    fb = FALLBACK_BRANDS.get(base)
    if not fb:
        return None
    url, color, title = fb
    return {"domain": None, "title": title, "logo": url,
            "colors": [{"hex": color, "name": f"{title} brand"}],
            "description": None}


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


def _base_asset(symbol):
    """BTC/USDT -> BTC ; strip quote currency."""
    return symbol.split("/")[0].split("-")[0].upper()


def _lookup_name(symbol):
    base = _base_asset(symbol)
    return COIN_NAMES.get(base, base)


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
    logos = brand.get("logos") or []
    for lg in logos:
        if lg.get("mode") == "light" and lg.get("type") == "icon":
            return lg.get("url")
    for lg in logos:
        if lg.get("url"):
            return lg.get("url")
    return None


_api_disabled = False  # set once the key is exhausted/unauthorized this process


def _cache_and_return(symbol, data, now):
    if data:
        with _lock:
            disk = _load_disk_cache()
            disk[symbol] = {"cached_at": now, "data": data}
            _save_disk_cache(disk)
    return data


def enrich_symbol(symbol):
    """Return {domain, title, logo, colors} for a crypto pair, or None.

    Order: fresh disk cache -> live API (unless disabled/no key) -> fallback.
    A 401/exhausted key disables the API for this process so we never pay the
    per-call timeout again; fallback logos are cached so repeats are instant.
    """
    global _api_disabled
    api_key = _load_api_key()
    now = time.time()
    with _lock:
        cached = _load_disk_cache().get(symbol)
    if cached and (now - cached.get("cached_at", 0)) < CACHE_TTL:
        return cached.get("data")
    if not api_key or _api_disabled:
        return _cache_and_return(symbol, _fallback(symbol), now)
    try:
        resp = requests.post(
            f"{API_BASE}/brand/retrieve",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"type": "by_name", "name": _lookup_name(symbol)},
            timeout=15,
        )
        if resp.status_code != 200:
            if resp.status_code in (401, 402, 429):
                _api_disabled = True
            return _cache_and_return(symbol, _fallback(symbol), now)
        brand = resp.json().get("brand") or {}
        data = {
            "domain": brand.get("domain"),
            "title": brand.get("title") or _lookup_name(symbol),
            "logo": _logo_url(brand),
            "colors": [
                {"hex": c.get("hex"), "name": c.get("name")}
                for c in (brand.get("colors") or [])
                if c.get("hex")
            ],
            "description": brand.get("description"),
        }
        return _cache_and_return(symbol, data if data.get("logo") else (_fallback(symbol) or data), now)
    except Exception:
        return _cache_and_return(symbol, _fallback(symbol), now)


def enrich_symbols(symbols):
    return {sym: enrich_symbol(sym) for sym in symbols}


if __name__ == "__main__":
    import sys
    syms = sys.argv[1:] or ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    print(json.dumps(enrich_symbols(syms), indent=2))
