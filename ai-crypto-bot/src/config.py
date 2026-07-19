import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


_env_pattern = re.compile(r"\$\{([^}]+)\}")


def _resolve_env(value: Any) -> Any:
    if isinstance(value, str):
        match = _env_pattern.fullmatch(value)
        if match:
            return os.environ.get(match.group(1), "")
        def _replacer(m: re.Match) -> str:
            return os.environ.get(m.group(1), "")
        return _env_pattern.sub(_replacer, value)
    if isinstance(value, dict):
        return {k: _resolve_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env(v) for v in value]
    return value


def _load_dotenv(path: str = ".env") -> None:
    env_file = Path(path)
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if (val.startswith('"') and val.endswith('"')) or \
           (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        os.environ.setdefault(key, val)


class ExchangeConfig(BaseModel):
    name: str = "kraken"
    api_key: str = ""
    api_secret: str = ""
    sandbox: bool = False
    rate_limit: int = 1200


class StrategyConfig(BaseModel):
    model_config = {"extra": "allow"}
    type: str = "aggressive_momentum"
    fast_period: int = 5
    slow_period: int = 13
    trend_ema_period: int = 34
    # ATR
    atr_period: int = 10
    atr_sl_multiplier: float = 1.2
    # Regime detection
    adx_period: int = 10
    adx_trend_threshold: int = 15
    # Confidence
    min_confidence: int = 1


class TradingConfig(BaseModel):
    symbols: list[str] = Field(default=["BTC/USDT"])
    initial_capital: float = 100.0
    position_size_pct: float = 0.50
    position_weights: dict[str, float] = Field(default_factory=dict)
    max_open_positions: int = 2
    loop_interval_seconds: int = 180
    stop_loss_pct: float = 1.5
    take_profit_pct: float = 5.0
    scale_in_enabled: bool = False
    scale_in_levels: int = 2
    scale_in_spacing_pct: float = 2.0
    db_path: str = "data/trades.db"
    # Slippage and fees
    slippage_bps: float = 5.0
    taker_fee_pct: float = 0.1
    # ATR-based risk management
    atr_period: int = 10
    atr_multiplier: float = 1.2
    reward_ratio: float = 3.0
    risk_per_trade_pct: float = 0.10
    # Timeframes
    timeframe: str = "5m"
    higher_tf: str = "1h"
    higher_tf_limit: int = 100
    # $100 → $1000 challenge
    challenge_enabled: bool = True
    challenge_target: float = 1000.0
    challenge_days: int = 30
    challenge_failure_threshold: float = 10.0  # restart when equity < this


class WebConfig(BaseModel):
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8080
    password: str = ""


class AppConfig(BaseModel):
    exchange: ExchangeConfig = ExchangeConfig()
    strategy: StrategyConfig = StrategyConfig()
    trading: TradingConfig = TradingConfig()
    web: WebConfig = WebConfig()
    alerts: dict[str, Any] = Field(default_factory=dict)
    log_level: str = "INFO"


def load_config(path: str | None = None) -> AppConfig:
    _load_dotenv()
    if path is None:
        for p in ["config/config.yaml", "config/local.yaml"]:
            fp = Path(p)
            if fp.exists():
                path = str(fp)
                break
    if path and Path(path).exists():
        raw = yaml.safe_load(Path(path).read_text())
        raw = _resolve_env(raw)
        return AppConfig.model_validate(raw)
    return AppConfig()
