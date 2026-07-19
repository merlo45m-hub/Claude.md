from __future__ import annotations

import ccxt.async_support as ccxt
import pandas as pd

from src.config import ExchangeConfig


class ExchangeClient:
    _SUPPORTED_EXCHANGES = frozenset({
        "binance", "coinbase", "coinbasepro", "kraken", "krakenfutures",
        "bybit", "okx", "bitget", "gate", "kucoin", "kucoinfutures",
        "bitmex", "deribit", "gemini", "cryptocom", "bitfinex",
        "bitstamp", "poloniex", "bittrex", "ascendex", "mexc",
        "huobi", "htx", "woo", "bitmart", "lbank", "phemex",
        "coinex", "whitebit", "probit", "digifinex",
    })

    def __init__(self, config: ExchangeConfig, timeframe: str = "15m") -> None:
        name = config.name.lower().replace(" ", "")
        if name not in self._SUPPORTED_EXCHANGES:
            raise ValueError(
                f"Unsupported exchange: {config.name!r}. "
                f"Supported: {sorted(self._SUPPORTED_EXCHANGES)}"
            )
        exchange_class = getattr(ccxt, name)
        self._exchange = exchange_class({
            "apiKey": config.api_key,
            "secret": config.api_secret,
            "enableRateLimit": True,
            "rateLimit": config.rate_limit,
        })
        if config.sandbox:
            self._exchange.set_sandbox_mode(True)
        self.timeframe = timeframe

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str | None = None,
        limit: int = 200,
    ) -> pd.DataFrame:
        tf = timeframe or self.timeframe
        raw = await self._exchange.fetch_ohlcv(symbol, tf, limit=limit)
        df = pd.DataFrame(
            raw,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    async def close(self) -> None:
        await self._exchange.close()
