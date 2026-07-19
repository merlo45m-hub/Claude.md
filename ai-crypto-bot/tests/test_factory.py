import pytest

from src.config import StrategyConfig
from src.strategy.base import BaseStrategy
from src.strategy.factory import StrategyFactory
from src.strategy.sma_cross import SMACrossStrategy


def test_create_sma_cross() -> None:
    config = StrategyConfig(type="sma_cross", fast_period=5, slow_period=15)
    strategy = StrategyFactory.create("sma_cross", config)
    assert isinstance(strategy, BaseStrategy)
    assert isinstance(strategy, SMACrossStrategy)
    assert strategy.fast == 5
    assert strategy.slow == 15


def test_unknown_strategy_raises() -> None:
    config = StrategyConfig(type="nonexistent")
    with pytest.raises(ValueError, match="Unknown strategy type"):
        StrategyFactory.create("nonexistent", config)
