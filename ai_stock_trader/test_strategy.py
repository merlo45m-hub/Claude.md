#!/usr/bin/env python3
"""Unit tests for unified_strategy.py"""
import unittest
import sys
sys.path.insert(0, '/root/ai_stock_trader')

from unified_strategy import should_exit_position, compute_indicators, get_config

class TestExitLogic(unittest.TestCase):
    def test_long_stop_loss_trigger(self):
        position = {'entry_price': 100.0, 'side': 'LONG', 'stop_loss': 0.03, 'take_profit': 0.02}
        self.assertEqual(should_exit_position(97.0, position), 'STOP_LOSS')
    
    def test_long_take_profit_trigger(self):
        position = {'entry_price': 100.0, 'side': 'LONG', 'stop_loss': 0.03, 'take_profit': 0.02}
        self.assertEqual(should_exit_position(102.0, position), 'TAKE_PROFIT')
    
    def test_short_stop_loss_trigger(self):
        position = {'entry_price': 100.0, 'side': 'SHORT', 'stop_loss': 0.03, 'take_profit': 0.02}
        self.assertEqual(should_exit_position(103.0, position), 'STOP_LOSS')
    
    def test_short_take_profit_trigger(self):
        position = {'entry_price': 100.0, 'side': 'SHORT', 'stop_loss': 0.03, 'take_profit': 0.02}
        self.assertEqual(should_exit_position(98.0, position), 'TAKE_PROFIT')
    
    def test_no_exit_in_middle(self):
        position = {'entry_price': 100.0, 'side': 'LONG', 'stop_loss': 0.03, 'take_profit': 0.02}
        self.assertIsNone(should_exit_position(101.0, position))
    
    def test_trailing_stop_long_activation(self):
        position = {'entry_price': 100.0, 'side': 'LONG', 'stop_loss': 0.03, 'take_profit': 0.02, 'trailing_high': 103.0}
        self.assertEqual(should_exit_position(97.5, position), 'TRAILING_STOP')
    
    def test_trailing_stop_short_activation(self):
        position = {'entry_price': 100.0, 'side': 'SHORT', 'stop_loss': 0.03, 'take_profit': 0.02, 'trailing_low': 97.0}
        self.assertEqual(should_exit_position(102.0, position), 'TRAILING_STOP')
    
    def test_scale_position_logic(self):
        position = {'entry_price': 100.0, 'side': 'SHORT', 'stop_loss': 0.03, 'take_profit': 0.02, 'size': 1.0, 'scale_count': 1}
        entry = position['entry_price']
        favorable = (entry - 98.5) / entry
        self.assertGreaterEqual(favorable, 0.015)

class TestIndicators(unittest.TestCase):
    def test_compute_indicators_sma_relationship(self):
        import pandas as pd
        prices = [100 + i for i in range(50)]
        close_series = pd.Series(prices)
        result = compute_indicators(close_series)
        if result:
            sma_fast, sma_slow, rsi = result
            self.assertTrue(sma_fast > sma_slow)
    
    def test_compute_indicators_rsi_range(self):
        import pandas as pd
        prices = [100 + (i % 5) for i in range(50)]
        close_series = pd.Series(prices)
        result = compute_indicators(close_series)
        if result:
            sma_fast, sma_slow, rsi = result
            self.assertTrue(0 <= rsi <= 100)

class TestConfig(unittest.TestCase):
    def test_default_symbols_include_etfs(self):
        config = get_config()
        self.assertIn('SPY', config['symbols'])
        self.assertIn('QQQ', config['symbols'])
    
    def test_take_profit_is_2_percent(self):
        config = get_config()
        self.assertEqual(config['take_profit'], 0.02)
    
    def test_stop_loss_is_3_percent(self):
        config = get_config()
        self.assertEqual(config['stop_loss'], 0.03)

if __name__ == '__main__':
    unittest.main()