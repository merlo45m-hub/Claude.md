import pytest
import pandas as pd

from src.config import StrategyConfig, TradingConfig
from src.strategy.sma_cross import SMACrossStrategy
from src.trading.paper import PaperTrader
from src.data.store import DataStore


def _make_df(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": closes})


def test_long_buy_then_sell() -> None:
    store = DataStore()
    cfg = StrategyConfig(fast_period=2, slow_period=3)
    strat = SMACrossStrategy(cfg)
    trader = PaperTrader(TradingConfig(initial_capital=1000.0), store)

    store.set("BTC/USDT", _make_df([10, 10, 10, 10, 9, 9, 12]))
    trader.execute("BTC/USDT", strat.evaluate(_make_df([10, 10, 10, 10, 9, 9, 12])))
    assert trader.positions["BTC/USDT"].direction == "long"

    store.set("BTC/USDT", _make_df([20, 20, 20, 20, 21, 20, 18]))
    trader.execute("BTC/USDT", strat.evaluate(_make_df([20, 20, 20, 20, 21, 20, 18])))
    assert "BTC/USDT" not in trader.positions
    assert trader.trades[0].pnl > 0


def test_short_sell_then_buy() -> None:
    store = DataStore()
    cfg = StrategyConfig(fast_period=2, slow_period=3)
    strat = SMACrossStrategy(cfg)
    trader = PaperTrader(TradingConfig(initial_capital=1000.0), store)

    store.set("BTC/USDT", _make_df([20, 20, 20, 20, 21, 20, 18]))
    trader.execute("BTC/USDT", strat.evaluate(_make_df([20, 20, 20, 20, 21, 20, 18])))
    assert trader.positions["BTC/USDT"].direction == "short"

    store.set("BTC/USDT", _make_df([10, 10, 10, 10, 9, 9, 12]))
    trader.execute("BTC/USDT", strat.evaluate(_make_df([10, 10, 10, 10, 9, 9, 12])))
    assert "BTC/USDT" not in trader.positions
    assert trader.trades[0].pnl > 0


def test_short_pnl_positive_when_price_drops() -> None:
    store = DataStore()
    trader = PaperTrader(TradingConfig(initial_capital=1000.0), store)
    store.set("SOL/USDT", _make_df([100, 100, 100, 100, 110, 105, 95]))

    trader.execute("SOL/USDT", "sell")
    assert trader.positions["SOL/USDT"].direction == "short"
    # price reflects 5 bps slippage: 95.0 - 0.0475 = 94.9525
    assert trader.positions["SOL/USDT"].price == pytest.approx(94.95, rel=1e-3)

    store.set("SOL/USDT", _make_df([100, 100, 100, 100, 110, 105, 80]))
    trader.execute("SOL/USDT", "buy")
    assert trader.trades[0].pnl > 0


def test_double_trade_rejected() -> None:
    store = DataStore()
    trader = PaperTrader(TradingConfig(initial_capital=1000.0), store)
    store.set("BTC/USDT", _make_df([50] * 10))

    trader.execute("BTC/USDT", "buy")
    assert trader.execute("BTC/USDT", "buy") is False
    assert trader.positions["BTC/USDT"].direction == "long"

    trader.execute("BTC/USDT", "sell")
    trader.execute("BTC/USDT", "sell")
    assert trader.positions["BTC/USDT"].direction == "short"
