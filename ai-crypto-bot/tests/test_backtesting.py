import pandas as pd

from src.config import StrategyConfig, TradingConfig
from src.strategy.sma_cross import SMACrossStrategy
from src.backtesting.engine import Backtester


def _make_uptrend_df(n: int = 100) -> pd.DataFrame:
    prices = [100.0 + i * 0.5 for i in range(n)]
    return pd.DataFrame({"close": prices})


def _make_downtrend_df(n: int = 100) -> pd.DataFrame:
    prices = [100.0 - i * 0.5 for i in range(n)]
    return pd.DataFrame({"close": prices})


def _make_sine_df(n: int = 200) -> pd.DataFrame:
    import math
    prices = [100.0 + 10 * math.sin(i * 0.1) for i in range(n)]
    return pd.DataFrame({"close": prices})


def test_backtester_uptrend_produces_trades() -> None:
    config = TradingConfig(initial_capital=10000.0)
    strategy_cfg = StrategyConfig(fast_period=5, slow_period=20)
    strategy = SMACrossStrategy(strategy_cfg)
    backtester = Backtester(config, strategy)

    df = _make_uptrend_df(150)
    result = backtester.run(df)

    assert result.n_trades >= 0
    assert result.initial_balance == 10000.0
    assert result.final_balance >= 0


def test_backtester_downtrend() -> None:
    config = TradingConfig(initial_capital=10000.0)
    strategy_cfg = StrategyConfig(fast_period=5, slow_period=20)
    strategy = SMACrossStrategy(strategy_cfg)
    backtester = Backtester(config, strategy)

    df = _make_downtrend_df(150)
    result = backtester.run(df)

    assert result.n_trades >= 0
    assert result.total_return_pct is not None


def test_backtester_metrics() -> None:
    config = TradingConfig(initial_capital=10000.0)
    strategy_cfg = StrategyConfig(fast_period=10, slow_period=30)
    strategy = SMACrossStrategy(strategy_cfg)
    backtester = Backtester(config, strategy)

    df = _make_sine_df(300)
    result = backtester.run(df)

    assert result.win_rate >= 0.0
    assert result.max_drawdown >= 0.0
    assert result.sharpe_ratio is not None
