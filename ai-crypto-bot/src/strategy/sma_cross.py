from __future__ import annotations

import pandas as pd

from src.config import StrategyConfig
from src.strategy.base import BaseStrategy, Signal


class SMACrossStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig) -> None:
        self.fast = config.fast_period
        self.slow = config.slow_period

    def evaluate(self, df: pd.DataFrame) -> Signal:
        if len(df) < self.slow:
            return "hold"

        fast_sma = df["close"].rolling(self.fast).mean()
        slow_sma = df["close"].rolling(self.slow).mean()

        prev_fast = fast_sma.iloc[-2]
        prev_slow = slow_sma.iloc[-2]
        curr_fast = fast_sma.iloc[-1]
        curr_slow = slow_sma.iloc[-1]

        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return "buy"
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return "sell"
        return "hold"
