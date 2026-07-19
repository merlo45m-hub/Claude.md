from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from src.config import TradingConfig
from src.data.store import DataStore

logger = logging.getLogger(__name__)

Side = Literal["buy", "sell"]
Direction = Literal["long", "short"]


@dataclass
class Trade:
    symbol: str
    side: Side
    direction: Direction
    price: float
    size: float
    pnl: float = 0.0
    entry_price: float | None = None
    scale_entries: list[float] = field(default_factory=list)
    atr_at_entry: float = 0.0


@dataclass
class PaperTrader:
    config: TradingConfig
    store: DataStore
    persistence: Any = None
    balance: float = 0.0
    positions: dict[str, Trade] = field(default_factory=dict)
    trades: list[Trade] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.persistence:
            loaded_balance, loaded_positions = self.persistence.load_state()
            self.balance = loaded_balance if loaded_balance > 0 else self.config.initial_capital
            for sym, pos_data in loaded_positions.items():
                if isinstance(pos_data, dict):
                    # Ensure 'side' field exists; infer from direction if missing
                    if 'side' not in pos_data:
                        pos_data['side'] = 'buy' if pos_data.get('direction') == 'long' else 'sell'
                    self.positions[sym] = Trade(**pos_data)
        else:
            self.balance = self.config.initial_capital

    def _get_price(self, symbol: str) -> float | None:
        df = self.store.get(symbol)
        if df is None or df.empty:
            return None
        return float(df["close"].iloc[-1])

    def _apply_slippage(self, price: float, side: str) -> float:
        slippage = price * (self.config.slippage_bps / 10_000)
        return price + slippage if side == "buy" else price - slippage

    def _apply_fees(self, amount: float) -> float:
        return amount * (1 - self.config.taker_fee_pct / 100)

    def execute(self, symbol: str, side: str, atr: float | None = None) -> bool:
        if side not in ("buy", "sell"):
            return False
        price = self._get_price(symbol)
        if price is None:
            return False

        price = self._apply_slippage(price, side)

        if side == "buy":
            existing = self.positions.get(symbol)
            if existing is not None and existing.direction == "short":
                return self._close_short(symbol, existing, price)
            if existing is not None and existing.direction == "long":
                if self.config.scale_in_enabled:
                    return self._scale_in_long(symbol, existing, price)
                return False
            if self._at_position_limit():
                return False
            return self._open_long(symbol, price, atr)

        if side == "sell":
            existing = self.positions.get(symbol)
            if existing is not None and existing.direction == "long":
                return self._close_long(symbol, existing, price)
            if existing is not None and existing.direction == "short":
                if self.config.scale_in_enabled:
                    return self._scale_in_short(symbol, existing, price)
                return False
            if self._at_position_limit():
                return False
            return self._open_short(symbol, price, atr)

        return False

    def _scale_in_long(self, symbol: str, pos: Trade, price: float) -> bool:
        avg_entry = pos.price
        levels = self.config.scale_in_levels
        spacing = self.config.scale_in_spacing_pct / 100
        max_scales = levels - 1
        if len(pos.scale_entries) >= max_scales:
            return False
        last_entry = pos.scale_entries[-1] if pos.scale_entries else (avg_entry or 0.0)  # Ensures no None values
        if last_entry is None or last_entry == 0.0:
            logger.warning("Skipping scale-in: Invalid last_entry for %s", symbol)
            return False
        target_price = last_entry * (1 - spacing)
        if price > target_price:
            return False
        capital = self.balance * self._position_pct(symbol)
        add_size = capital / price
        pos.size += add_size
        pos.price = (pos.price * pos.size + price * add_size) / (pos.size + add_size)
        pos.scale_entries.append(price)
        self.balance -= capital
        logger.info("%s: scaled IN long at %.2f (avg=%.2f, size=%.4f, scales=%d/%d)",
                     symbol, price, pos.price, pos.size, len(pos.scale_entries), max_scales)
        self._save_state()
        return True

    def _scale_in_short(self, symbol: str, pos: Trade, price: float) -> bool:
        avg_entry = pos.price
        levels = self.config.scale_in_levels
        spacing = self.config.scale_in_spacing_pct / 100
        max_scales = levels - 1
        if len(pos.scale_entries) >= max_scales:
            return False
        last_entry = pos.scale_entries[-1] if pos.scale_entries else avg_entry
        target_price = last_entry * (1 + spacing)
        if price < target_price:
            return False
        capital = self.balance * self._position_pct(symbol)
        add_size = capital / price
        pos.size += add_size
        pos.price = (pos.price * pos.size + price * add_size) / (pos.size + add_size)
        pos.scale_entries.append(price)
        self.balance += capital
        logger.info("%s: scaled IN short at %.2f (avg=%.2f, size=%.4f, scales=%d/%d)",
                     symbol, price, pos.price, pos.size, len(pos.scale_entries), max_scales)
        self._save_state()
        return True

    def check_stop_loss_take_profit(
        self, symbol: str, current_price: float
    ) -> str | None:
        position = self.positions.get(symbol)
        if position is None:
            return None

        # entry price may be stored as .price or .entry_price — handle both
        entry = position.price or getattr(position, "entry_price", None)
        if entry is None:
            logger.warning("Skipping stop-loss/take-profit check: Missing price for %s", symbol)
            return None

        # ATR-based stops (preferred when ATR data is available)
        atr = position.atr_at_entry
        if atr > 0 and self.config.atr_multiplier > 0:
            stop_distance = atr * self.config.atr_multiplier
            tp_distance = stop_distance * self.config.reward_ratio

            if position.direction == "long":
                stop_price = entry - stop_distance
                target_price = entry + tp_distance
                if current_price >= target_price:
                    return "sell"
                if current_price <= stop_price:
                    return "sell"
            elif position.direction == "short":
                stop_price = entry + stop_distance
                target_price = entry - tp_distance
                if current_price <= target_price:
                    return "buy"
                if current_price >= stop_price:
                    return "buy"
            return None

        # Fallback: fixed percentage stops
        sl = self.config.stop_loss_pct / 100
        tp = self.config.take_profit_pct / 100

        if position.direction == "long":
            pnl_pct = (current_price - entry) / entry
            if tp > 0 and pnl_pct >= tp:
                return "sell"
            if sl > 0 and pnl_pct <= -sl:
                return "sell"
        elif position.direction == "short":
            pnl_pct = (entry - current_price) / entry
            if tp > 0 and pnl_pct >= tp:
                return "buy"
            if sl > 0 and pnl_pct <= -sl:
                return "buy"
        return None

    def _at_position_limit(self) -> bool:
        return len(self.positions) >= self.config.max_open_positions

    def _save_state(self) -> None:
        if self.persistence is None:
            return
        positions_dict: dict[str, dict[str, Any]] = {}
        for sym, trade in self.positions.items():
            positions_dict[sym] = asdict(trade)
        self.persistence.save_state(self.balance, positions_dict)

    def _position_pct(self, symbol: str) -> float:
        return self.config.position_weights.get(symbol, self.config.position_size_pct)

    def _open_long(self, symbol: str, price: float, atr: float | None = None) -> bool:
        # Cap single position to configured % of balance
        max_capital = self.balance * self._position_pct(symbol)
        if atr and atr > 0 and self.config.atr_multiplier > 0:
            risk_amount = self.balance * self.config.risk_per_trade_pct
            stop_distance = atr * self.config.atr_multiplier
            size = risk_amount / stop_distance
            capital = size * price
            # Cap by both total balance and position size %
            if capital > self.balance:
                capital = self.balance
                size = capital / price
            if capital > max_capital:
                capital = max_capital
                size = capital / price
            if size <= 0:
                return False
        else:
            capital = max_capital
            size = capital / price

        fee = capital * (1 - self._apply_fees(1.0))
        trade = Trade(
            symbol=symbol, side="buy", direction="long", price=price, size=size,
            entry_price=price, atr_at_entry=atr or 0.0,
        )
        self.positions[symbol] = trade
        self.balance -= capital
        logger.info("%s: OPEN long at %.2f (size=%.6f, balance=%.2f, fee=%.4f, atr=%s)",
                     symbol, price, size, self.balance, fee, f"{atr:.2f}" if atr else "N/A")
        self._save_state()
        return True

    def _close_long(self, symbol: str, pos: Trade, price: float) -> bool:
        self.positions.pop(symbol)
        if pos.price is None:
            logger.warning("Skipping position close: Missing price for %s", symbol)
            return False
        proceeds = pos.size * price
        proceeds_after_fee = self._apply_fees(proceeds)
        pos.pnl = proceeds_after_fee - (pos.size * pos.price)
        pos.entry_price = pos.price
        pos.price = price
        self.balance += proceeds_after_fee
        self.trades.append(pos)
        logger.info("%s: CLOSE long at %.2f (pnl=%.2f, balance=%.2f, fee=%.4f)",
                     symbol, price, pos.pnl, self.balance, proceeds - proceeds_after_fee)
        if self.persistence:
            self.persistence.save_trade(pos)
            self._save_state()
        return True

    def _open_short(self, symbol: str, price: float, atr: float | None = None) -> bool:
        max_capital = self.balance * self._position_pct(symbol)
        if atr and atr > 0 and self.config.atr_multiplier > 0:
            risk_amount = self.balance * self.config.risk_per_trade_pct
            stop_distance = atr * self.config.atr_multiplier
            size = risk_amount / stop_distance
            capital = size * price
            if capital > self.balance:
                capital = self.balance
                size = capital / price
            if capital > max_capital:
                capital = max_capital
                size = capital / price
            if size <= 0:
                return False
        else:
            capital = max_capital
            size = capital / price

        fee = capital * (1 - self._apply_fees(1.0))
        trade = Trade(
            symbol=symbol, side="sell", direction="short", price=price, size=size,
            entry_price=price, atr_at_entry=atr or 0.0,
        )
        self.positions[symbol] = trade
        self.balance += capital
        logger.info("%s: OPEN short at %.2f (size=%.6f, balance=%.2f, atr=%s)",
                     symbol, price, size, self.balance, f"{atr:.2f}" if atr else "N/A")
        self._save_state()
        return True

    def _close_short(self, symbol: str, pos: Trade, price: float) -> bool:
        self.positions.pop(symbol)
        cost = pos.size * price
        cost_after_fee = self._apply_fees(cost)
        pos.pnl = (pos.price - price) * pos.size - (cost - cost_after_fee)
        pos.entry_price = pos.price
        pos.price = price
        self.balance -= cost_after_fee
        self.trades.append(pos)
        logger.info("%s: CLOSE short at %.2f (pnl=%.2f, balance=%.2f, fee=%.4f)",
                     symbol, price, pos.pnl, self.balance, cost - cost_after_fee)
        if self.persistence:
            self.persistence.save_trade(pos)
            self._save_state()
        return True

    def summary(self) -> str:
        total_pnl = sum(t.pnl for t in self.trades)
        n_trades = len(self.trades)
        win_rate = 0
        if n_trades:
            wins = sum(1 for t in self.trades if t.pnl > 0)
            win_rate = wins / n_trades * 100
        open_dirs = ", ".join(
            f"{s}: {p.direction}" for s, p in self.positions.items()
        ) or "none"
        return (
            f"Trades: {n_trades} | Win: {win_rate:.0f}% | PnL: ${total_pnl:.2f} | "
            f"Balance: ${self.balance:.2f} | Open: {open_dirs}"
        )
