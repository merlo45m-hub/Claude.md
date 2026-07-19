from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

import pandas as pd


Signal = Literal["buy", "sell", "hold"]
Regime = Literal["trending", "ranging", "volatile"]
TrendBias = Literal["bullish", "bearish", "neutral"]


class BaseStrategy(ABC):
    def __init__(self, config: Any = None) -> None:
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> Signal: ...

    def get_regime(self, df: pd.DataFrame) -> Regime:
        """Classify market regime as trending, ranging, or volatile."""
        return "ranging"

    def get_trend_bias(self, df: pd.DataFrame) -> TrendBias:
        """Determine overall trend bias from higher timeframe data."""
        return "neutral"

    def get_current_atr(self, df: pd.DataFrame) -> float:
        """Return current ATR value for position sizing / stops."""
        return 0.0
