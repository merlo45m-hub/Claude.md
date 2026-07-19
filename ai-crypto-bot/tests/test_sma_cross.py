import pandas as pd

from src.config import StrategyConfig
from src.strategy.sma_cross import SMACrossStrategy


def _make_df(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": closes})


def test_buy_signal() -> None:
    cfg = StrategyConfig(fast_period=2, slow_period=3)
    strat = SMACrossStrategy(cfg)
    df = _make_df([10, 10, 10, 10, 9, 9, 12])
    assert strat.evaluate(df) == "buy"


def test_sell_signal() -> None:
    cfg = StrategyConfig(fast_period=2, slow_period=3)
    strat = SMACrossStrategy(cfg)
    df = _make_df([20, 20, 20, 20, 21, 20, 18])
    assert strat.evaluate(df) == "sell"


def test_hold() -> None:
    cfg = StrategyConfig(fast_period=2, slow_period=3)
    strat = SMACrossStrategy(cfg)
    df = _make_df([10, 10, 10, 10, 10])
    assert strat.evaluate(df) == "hold"


def test_insufficient_data() -> None:
    cfg = StrategyConfig(fast_period=10, slow_period=30)
    strat = SMACrossStrategy(cfg)
    df = _make_df([1, 2, 3])
    assert strat.evaluate(df) == "hold"
