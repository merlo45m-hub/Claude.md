#!/usr/bin/env python3
"""
AI Stock Trading Bot - Live Dashboard Monitor
Shows real-time portfolio value, trades, and strategy status
"""
import time
import os
import json
import datetime
import threading

class TradingDashboard:
    def __init__(self):
        self.running = True
        self.stats = {
            'portfolio_value': 100.0,
            'cash': 100.0,
            'position': 0,
            'last_trade': None,
            'total_trades': 0,
            'profit_loss': 0.0,
            'status': 'INITIALIZED'
        }
        self.update_interval = 2  # seconds
        self.log_file = '/root/ai_stock_trader/trading.log'
        
    def clear_screen(self):
        os.system('clear' if os.name != 'nt' else 'cls')
        
    def load_stats(self):
        """Load stats from log file or default"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        # Parse format: TIMESTAMP|KEY1=VALUE1|KEY2=VALUE2
                        if '|' in last_line:
                            parts = last_line.split('|')
                            for part in parts[1:]:
                                if '=' in part:
                                    k, v = part.split('=')
                                    if k in self.stats:
                                        # Convert numeric values
                                        if k in ['portfolio_value', 'cash', 'position', 'total_trades', 'profit_loss']:
                                            self.stats[k] = float(v)
                                        else:
                                            self.stats[k] = v
        except Exception as e:
            print(f"Stat load error: {e}")
    
    def display(self):
        while self.running:
            self.clear_screen()
            
            # Header
            print("=" * 55)
            print("           📊 AI STOCK TRADING DASHBOARD")
            print("=" * 55)
            
            # Status line
            status_color = {
                'RUNNING': '\033[92m',  # Green
                'STOPPED': '\033[91m',  # Red
                'INITIALIZED': '\033[93m'  # Yellow
            }.get(self.stats['status'], '\033[0m')
            
            print(f"{status_color} ● STATUS: {self.stats['status']}\033[0m")
            print("=" * 55)
            
            # Portfolio section
            print(f"💰 PORTFOLIO VALUE: ${self.stats['portfolio_value']:.2f}")
            print(f"💵 CASH: ${self.stats['cash']:.2f}")
            print(f"📈 POSITION: {int(self.stats['position'])} shares")
            
            # Performance
            pnl = self.stats['profit_loss']
            pnl_color = '\033[92m' if pnl >= 0 else '\033[91m'
            print(f"{pnl_color}📊 P&L: ${pnl:.2f} ({pnl/100*100:.1f}%)\033[0m")
            
            # Trade stats
            print("-" * 55)
            print(f"🔄 TOTAL TRADES: {int(self.stats['total_trades'])}")
            if self.stats['last_trade']:
                print(f"📝 LAST TRADE: {self.stats['last_trade']}")
            
            # Footer
            print("-" * 55)
            print(f"⏰ LAST UPDATE: {datetime.datetime.now().strftime('%H:%M:%S')}")
            print(f"🔄 REFRESH: {self.update_interval}s")
            print("=" * 55)
            
            # Auto-reload stats
            self.load_stats()
            
            # Wait for next update
            time.sleep(self.update_interval)
    
    def start(self):
        print("Starting trading dashboard...")
        print("Press Ctrl+C to exit")
        
        # Start display thread
        display_thread = threading.Thread(target=self.display, daemon=True)
        display_thread.start()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.running = False
            print("\nDashboard stopped.")


if __name__ == "__main__":
    dashboard = TradingDashboard()
    dashboard.start()