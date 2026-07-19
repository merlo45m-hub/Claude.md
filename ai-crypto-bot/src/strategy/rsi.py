from __future__ import annotations

import pandas as pd

from src.config import StrategyConfig
from src.strategy.base import BaseStrategy, Signal


class RSIStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig) -> None:
        self.period = getattr(config, "rsi_period", 14)
        self.oversold = getattr(config, "oversold_threshold", 30)
        self.overbought = getattr(config, "overbought_threshold", 70)

    def evaluate(self, df: pd.DataFrame) -> Signal:
        if len(df) < self.period + 1:
            return "hold"

        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.rolling(self.period).mean()
        avg_loss = loss.rolling(self.period).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        rsi = 100 - (100 / (1 + rs))

        curr_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]

        if prev_rsi >= self.oversold and curr_rsi < self.oversold:
            return "buy"
        if prev_rsi <= self.overbought and curr_rsi > self.overbought:
            return "sell"
        return "hold"
