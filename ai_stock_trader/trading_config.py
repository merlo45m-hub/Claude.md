"""Configuration management for the autonomous trading bot."""
import os
import yaml
from pathlib import Path

class TradingConfig:
    def __init__(self, config_path=None):
        self.config_path = config_path or Path(__file__).parent / "config.yaml"
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file or create default."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            return self._get_default_config()
    
    def _get_default_config(self):
        """Return default configuration."""
        return {
            'symbols': ['AAPL', 'MSFT', 'TSLA', 'META', 'AMZN', 'NVDA', 'GOOGL'],
            'data_ingestion': {
                'feed_url': 'wss://ws-feed.exchange.com',
                'log_file': 'data_ingestion.log',
                'batch_size': 1000
            },
            'strategy': {
                'indicators': ['sma_fast', 'sma_slow', 'rsi'],
                'strategy_type': 'momentum',
                'risk_per_trade': 0.02,
                'max_drawdown': 0.05
            },
            'execution': {
                'broker': 'alpaca',
                'paper_trading': True,
                'order_size': 100,
                ' slippage_tolerance': 0.001
            },
            'decider': {
                'llm_model': 'qwen3.5:4b',
                'audit_interval_minutes': 15,
                'performance_threshold': 0.6
            },
            'risk_management': {
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.04,
                'max_positions': 5,
                'max_daily_loss': 0.05
            }
        }
    
    def get(self, key, default=None):
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def save(self):
        """Save current config to YAML file."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

def ensure_imports():
    """Ensure required Python packages are available."""
    try:
        import asyncio, pandas, yfinance, requests, psycopg2, yaml
        print("All required packages are available")
        return True
    except ImportError as e:
        print(f"Missing required package: {e}")
        return False

if __name__ == "__main__":
    # Test the configuration module
    config = TradingConfig()
    print(f"Config loaded with keys: {list(config.config.keys())}")
    print(f"Trading symbols: {config.get('symbols')}")
    print(f"Broker: {config.get('execution.broker')}")
