from collections.abc import Sequence

import pandas as pd

from src.config import TradingConfig
from src.trading.paper import PaperTrader
from src.data.store import DataStore


def _make_df(closes: Sequence[float]) -> pd.DataFrame:
    return pd.DataFrame({"close": closes})


def test_max_open_positions_enforced() -> None:
    config = TradingConfig(
        symbols=["BTC/USDT", "ETH/USDT"],
        initial_capital=10000.0,
        max_open_positions=1,
    )
    store = DataStore()
    trader = PaperTrader(config, store)

    store.set("BTC/USDT", _make_df([50] * 10))
    store.set("ETH/USDT", _make_df([100] * 10))

    assert trader.execute("BTC/USDT", "buy") is True
    assert trader.execute("ETH/USDT", "buy") is False
    assert len(trader.positions) == 1
    assert "BTC/USDT" in trader.positions


def test_max_open_positions_allows_close_then_open() -> None:
    config = TradingConfig(
        symbols=["BTC/USDT", "ETH/USDT"],
        initial_capital=10000.0,
        max_open_positions=1,
    )
    store = DataStore()
    trader = PaperTrader(config, store)

    store.set("BTC/USDT", _make_df([50] * 10 + [60]))
    store.set("ETH/USDT", _make_df([100] * 10))

    trader.execute("BTC/USDT", "buy")
    assert len(trader.positions) == 1

    trader.execute("BTC/USDT", "sell")
    assert len(trader.positions) == 0

    assert trader.execute("ETH/USDT", "buy") is True
    assert len(trader.positions) == 1
    assert "ETH/USDT" in trader.positions


def test_stop_loss_long() -> None:
    config = TradingConfig(
        initial_capital=1000.0,
        stop_loss_pct=5.0,
    )
    store = DataStore()
    trader = PaperTrader(config, store)

    store.set("BTC/USDT", _make_df([100] * 10))
    trader.execute("BTC/USDT", "buy")

    action = trader.check_stop_loss_take_profit("BTC/USDT", 94.0)
    assert action == "sell"


def test_stop_loss_not_triggered() -> None:
    config = TradingConfig(
        initial_capital=1000.0,
        stop_loss_pct=5.0,
    )
    store = DataStore()
    trader = PaperTrader(config, store)

    store.set("BTC/USDT", _make_df([100] * 10))
    trader.execute("BTC/USDT", "buy")

    action = trader.check_stop_loss_take_profit("BTC/USDT", 97.0)
    assert action is None


def test_take_profit_long() -> None:
    config = TradingConfig(
        initial_capital=1000.0,
        take_profit_pct=10.0,
    )
    store = DataStore()
    trader = PaperTrader(config, store)

    store.set("BTC/USDT", _make_df([100] * 10))
    trader.execute("BTC/USDT", "buy")

    action = trader.check_stop_loss_take_profit("BTC/USDT", 115.0)
    assert action == "sell"


def test_stop_loss_short() -> None:
    config = TradingConfig(
        initial_capital=1000.0,
        stop_loss_pct=5.0,
    )
    store = DataStore()
    trader = PaperTrader(config, store)

    store.set("BTC/USDT", _make_df([100] * 10))
    trader.execute("BTC/USDT", "sell")

    action = trader.check_stop_loss_take_profit("BTC/USDT", 108.0)
    assert action == "buy"


def test_take_profit_short() -> None:
    config = TradingConfig(
        initial_capital=1000.0,
        take_profit_pct=5.0,
    )
    store = DataStore()
    trader = PaperTrader(config, store)

    store.set("BTC/USDT", _make_df([100] * 10))
    trader.execute("BTC/USDT", "sell")

    action = trader.check_stop_loss_take_profit("BTC/USDT", 93.0)
    assert action == "buy"


def test_execute_invalid_side() -> None:
    store = DataStore()
    trader = PaperTrader(TradingConfig(initial_capital=1000.0), store)
    store.set("BTC/USDT", _make_df([100] * 10))
    assert trader.execute("BTC/USDT", "invalid") is False
