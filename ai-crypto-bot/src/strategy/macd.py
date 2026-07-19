from __future__ import annotations

import pandas as pd

from src.config import StrategyConfig
from src.strategy.base import BaseStrategy, Signal


class MACDStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig) -> None:
        self.fast = getattr(config, "macd_fast", 12)
        self.slow = getattr(config, "macd_slow", 26)
        self.signal = getattr(config, "macd_signal", 9)

    def evaluate(self, df: pd.DataFrame) -> Signal:
        if len(df) < self.slow + self.signal:
            return "hold"

        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()

        prev_macd = macd_line.iloc[-2]
        prev_sig = signal_line.iloc[-2]
        curr_macd = macd_line.iloc[-1]
        curr_sig = signal_line.iloc[-1]

        if prev_macd <= prev_sig and curr_macd > curr_sig:
            return "buy"
        if prev_macd >= prev_sig and curr_macd < curr_sig:
            return "sell"
        return "hold"
