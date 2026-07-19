from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.config import StrategyConfig
from src.strategy.base import BaseStrategy


_registry: dict[str, type[Any]] = {}


def register(name: str) -> Callable[[type[BaseStrategy]], type[BaseStrategy]]:
    def decorator(cls: type[BaseStrategy]) -> type[BaseStrategy]:
        _registry[name] = cls
        return cls
    return decorator


class StrategyFactory:
    @staticmethod
    def create(type_name: str, config: StrategyConfig) -> BaseStrategy:
        if not _registry:
            _lazy_import()
        cls = _registry.get(type_name)
        if cls is None:
            raise ValueError(
                f"Unknown strategy type: {type_name!r}. "
                f"Available: {list(_registry.keys())}"
            )
        return cls(config)


def _lazy_import() -> None:
    from src.strategy.sma_cross import SMACrossStrategy
    register("sma_cross")(SMACrossStrategy)
    from src.strategy.rsi import RSIStrategy
    register("rsi")(RSIStrategy)
    from src.strategy.macd import MACDStrategy
    register("macd")(MACDStrategy)
    from src.strategy.aggressive_momentum import AggressiveMomentumStrategy
    register("aggressive_momentum")(AggressiveMomentumStrategy)
