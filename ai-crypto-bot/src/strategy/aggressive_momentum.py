from __future__ import annotations

import pandas as pd

from src.config import StrategyConfig
from src.strategy.base import BaseStrategy, Regime, Signal, TrendBias


class AggressiveMomentumStrategy(BaseStrategy):
    """Aggressive momentum strategy for small-account 10x challenge.

    Entries:
      - 5 EMA / 13 EMA crossover (fast momentum trigger)
      - ADX > 15 (trending market filter)
      - 34 EMA trend direction
      - Pullback entries to fast EMA
      - Continuation entries in strong trends

    Exits:
      - ATR-based stop loss (1.2x ATR)
      - Take profit (3x reward ratio)
    """

    def __init__(self, config: StrategyConfig) -> None:
        self.fast_ema = getattr(config, "fast_period", 5)
        self.slow_ema = getattr(config, "slow_period", 13)
        self.trend_ema = getattr(config, "trend_ema_period", 34)
        self.atr_period = getattr(config, "atr_period", 10)
        self.atr_multiplier = getattr(config, "atr_sl_multiplier", 1.2)
        self.adx_period = getattr(config, "adx_period", 10)
        self.adx_threshold = getattr(config, "adx_trend_threshold", 15)
        self.min_confidence = getattr(config, "min_confidence", 1)

    # ---- Indicator Calculations ----

    def _compute_ema(self, close: pd.Series, period: int) -> pd.Series:
        return close.ewm(span=period, adjust=False).mean()

    def _compute_atr(self, df: pd.DataFrame) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def _compute_adx(self, df: pd.DataFrame) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        period = self.adx_period
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        up_move = high - high.shift()
        down_move = low.shift() - low
        plus_dm = ((up_move > down_move) & (up_move > 0)).astype(float) * up_move
        minus_dm = ((down_move > up_move) & (down_move > 0)).astype(float) * down_move
        atr = tr.rolling(period).mean()
        plus_di = 100 * plus_dm.rolling(period).mean() / atr.replace(0, float("inf"))
        minus_di = 100 * minus_dm.rolling(period).mean() / atr.replace(0, float("inf"))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("inf"))
        return dx.rolling(period).mean()

    # ---- API ----

    def get_regime(self, df: pd.DataFrame) -> Regime:
        if len(df) < self.adx_period + 5:
            return "ranging"
        adx = self._compute_adx(df)
        current_adx = adx.iloc[-1]
        atr = self._compute_atr(df)
        close = df["close"]
        atr_pct = (atr.iloc[-1] / close.iloc[-1]) if close.iloc[-1] > 0 else 0
        if atr_pct > 0.05 and current_adx > self.adx_threshold:
            return "volatile"
        if current_adx > self.adx_threshold:
            return "trending"
        return "ranging"

    def get_trend_bias(self, df: pd.DataFrame) -> TrendBias:
        if len(df) < self.trend_ema + 5:
            return "neutral"
        trend_ema = self._compute_ema(df["close"], self.trend_ema)
        slope = trend_ema.diff(5).iloc[-1]
        if slope > 0:
            return "bullish"
        if slope < 0:
            return "bearish"
        return "neutral"

    def get_current_atr(self, df: pd.DataFrame) -> float:
        if len(df) < self.atr_period + 2:
            return 0.0
        atr = self._compute_atr(df)
        return float(atr.iloc[-1])

    def evaluate(self, df: pd.DataFrame) -> Signal:
        min_bars = max(self.slow_ema, self.trend_ema, self.adx_period) + 10
        if len(df) < min_bars:
            return "hold"

        close = df["close"]
        volume = df["volume"]

        fast_ema = self._compute_ema(close, self.fast_ema)
        slow_ema = self._compute_ema(close, self.slow_ema)
        trend_ema = self._compute_ema(close, self.trend_ema)
        adx = self._compute_adx(df)
        atr = self._compute_atr(df)

        current_adx = adx.iloc[-1]
        current_atr = atr.iloc[-1]

        # Trend direction
        price_above_trend = close.iloc[-1] > trend_ema.iloc[-1]
        trend_slope_up = trend_ema.diff(5).iloc[-1] > 0

        # EMA crossover check
        prev_fast = fast_ema.iloc[-2]
        prev_slow = slow_ema.iloc[-2]
        curr_fast = fast_ema.iloc[-1]
        curr_slow = slow_ema.iloc[-1]

        bull_cross = prev_fast <= prev_slow and curr_fast > curr_slow
        bear_cross = prev_fast >= prev_slow and curr_fast < curr_slow

        ema_bull = curr_fast > curr_slow
        ema_bear = curr_fast < curr_slow

        # Price momentum
        price_up = close.diff().iloc[-1] > 0
        vol_spike = volume.iloc[-1] > volume.iloc[-5:-1].mean() * 1.3 if len(volume) > 5 else False

        # === ENTRY LOGIC ===

        # Mode 1: Trending market (ADX above threshold) — momentum entries
        if current_adx >= self.adx_threshold:
            # EMA crossover + trend alignment
            if bull_cross and price_above_trend:
                return "buy"
            if bear_cross and not price_above_trend:
                return "sell"

            # Continuation: EMAs already crossed, price keeps pushing
            if ema_bull and price_above_trend and price_up:
                return "buy"
            if ema_bear and not price_above_trend and not price_up:
                return "sell"

            # Pullback to fast EMA within trend
            if current_atr > 0:
                dist_from_fast = abs(close.iloc[-1] - fast_ema.iloc[-1])
                if dist_from_fast < current_atr * 0.8:
                    if ema_bull and price_above_trend and price_up:
                        return "buy"
                    if ema_bear and not price_above_trend and not price_up:
                        return "sell"

        # Mode 2: No clear trend — aggressive mean reversion + breakout
        else:
            # Bollinger-style: big move with volume = breakout attempt
            if current_atr > 0:
                range_5 = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]
                if abs(range_5) > 0.005 and vol_spike:
                    if range_5 > 0 and price_above_trend:
                        return "buy"
                    if range_5 < 0 and not price_above_trend:
                        return "sell"

                # Fast momentum: 3-bar directional push
                if price_up and price_above_trend and close.diff(3).iloc[-1] > 0:
                    return "buy"
                if not price_up and not price_above_trend and close.diff(3).iloc[-1] < 0:
                    return "sell"

        return "hold"
