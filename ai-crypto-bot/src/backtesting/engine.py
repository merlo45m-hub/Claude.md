from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.config import TradingConfig
from src.data.store import DataStore
from src.strategy.base import BaseStrategy
from src.trading.paper import PaperTrader, Trade


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    initial_balance: float = 0.0
    final_balance: float = 0.0
    total_pnl: float = 0.0
    total_return_pct: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0
    n_trades: int = 0
    buy_hold_return_pct: float = 0.0
    symbol: str = ""
    duration_bars: int = 0

    def summary(self) -> str:
        return (
            f"{self.symbol}: Trades={self.n_trades} Return={self.total_return_pct:+.2f}% "
            f"PnL=${self.total_pnl:.2f} Win={self.win_rate:.0%} "
            f"MaxDD={self.max_drawdown:.1%} Sharpe={self.sharpe_ratio:.2f} "
            f"B&H={self.buy_hold_return_pct:+.2f}%"
        )


class Backtester:
    def __init__(
        self,
        config: TradingConfig,
        strategy: BaseStrategy,
        fee_pct: float = 0.0,
    ) -> None:
        self.config = config
        self.strategy = strategy
        self.fee_pct = fee_pct

    def _min_periods(self) -> int:
        return max(
            getattr(self.strategy, "slow", 30),
            getattr(self.strategy, "period", 30),
            getattr(self.strategy, "signal", 9) + getattr(self.strategy, "slow", 26),
            30,
        )

    def run(self, df: pd.DataFrame, symbol: str = "BACKTEST") -> BacktestResult:
        store = DataStore()
        config = self.config.model_copy(update={"db_path": ""})
        trader = PaperTrader(config, store)
        initial_balance = trader.balance

        min_periods = self._min_periods()
        equity_curve: list[float] = [initial_balance]

        for i in range(min_periods + 1, len(df)):
            window = df.iloc[:i]
            store.set(symbol, window)

            # Pass ATR for position sizing
            atr = self.strategy.get_current_atr(window)
            atr_arg = atr if atr > 0 else None

            signal = self.strategy.evaluate(window)
            if signal != "hold":
                trader.execute(symbol, signal, atr=atr_arg)

            current_price = float(df["close"].iloc[i])

            # Stop-loss / take-profit check (same as live)
            action = trader.check_stop_loss_take_profit(symbol, current_price)
            if action:
                trader.execute(symbol, action, atr=atr_arg)

            # Apply trading fee
            if self.fee_pct > 0:
                trader.balance -= trader.balance * self.fee_pct

            equity = self._compute_equity(trader, current_price)
            equity_curve.append(equity)

        for sym in list(trader.positions.keys()):
            pos = trader.positions[sym]
            close_side = "sell" if pos.direction == "long" else "buy"
            trader.execute(sym, close_side)

        first_price = float(df["close"].iloc[0])
        last_price = float(df["close"].iloc[-1])
        buy_hold_return = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0.0

        return self._build_result(trader, initial_balance, equity_curve, buy_hold_return, symbol, len(df))

    def _compute_equity(self, trader: PaperTrader, current_price: float) -> float:
        equity = trader.balance
        for pos in trader.positions.values():
            if pos.direction == "long":
                equity += pos.size * current_price
            else:
                equity -= pos.size * current_price
        return equity

    def _build_result(
        self,
        trader: PaperTrader,
        initial_balance: float,
        equity_curve: list[float],
        buy_hold_return_pct: float,
        symbol: str,
        duration_bars: int,
    ) -> BacktestResult:
        trades = trader.trades
        final_balance = trader.balance
        total_pnl = sum(t.pnl for t in trades)
        n_trades = len(trades)
        total_return_pct = (
            ((final_balance - initial_balance) / initial_balance) * 100
            if initial_balance > 0
            else 0.0
        )
        win_rate = sum(1 for t in trades if t.pnl > 0) / n_trades if n_trades > 0 else 0.0

        max_dd = 0.0
        peak = equity_curve[0] if equity_curve else initial_balance
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        returns = [
            equity_curve[i] / equity_curve[i - 1] - 1
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1] > 0
        ]
        avg_return = sum(returns) / len(returns) if returns else 0.0
        variance = (
            sum((r - avg_return) ** 2 for r in returns) / len(returns)
            if returns
            else 0.0
        )
        std_return = variance**0.5
        sharpe = (avg_return / std_return * (252**0.5)) if std_return > 0 else 0.0
        calmar = (total_return_pct / (max_dd * 100)) if max_dd > 0 else 0.0

        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            initial_balance=initial_balance,
            final_balance=final_balance,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            win_rate=win_rate,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            calmar_ratio=calmar,
            n_trades=n_trades,
            buy_hold_return_pct=buy_hold_return_pct,
            symbol=symbol,
            duration_bars=duration_bars,
        )
