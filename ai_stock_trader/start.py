#!/usr/bin/env python3
"""
Start both Trading Bot and Web Dashboard
Run this script to launch the complete trading system with web monitoring
"""
import subprocess
import time
import os
import signal
import sys

def main():
    print("=" * 50)
    print("🚀 AI Trading Bot - Launching System")
    print("=" * 50)
    
    # Change to project directory
    os.chdir('/root/ai_stock_trader')
    
    # Activate venv python
    venv_python = '/root/ai_stock_trader/venv/bin/python'
    
    # Start trading bot in background
    print("\n📈 Starting Trading Bot...")
    bot_process = subprocess.Popen(
        [venv_python, 'trader.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Start dashboard server
    print("🌐 Starting Web Dashboard on http://0.0.0.0:8084")
    dashboard_process = subprocess.Popen(
        [venv_python, 'web_dashboard.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    print("\n✅ System Started!")
    print("   - Trading Bot: PID", bot_process.pid)
    print("   - Web Dashboard: http://0.0.0.0:8084")
    print("\n📱 Access dashboard from any browser:")
    print("   - Local: http://localhost:8084")
    print("   - VPS IP: http://<your-vps-ip>:8084")
    print("\n🛑 Press Ctrl+C to stop both services")
    
    # Forward bot output to terminal
    def forward_output():
        while True:
            line = bot_process.stdout.readline()
            if not line:
                break
            print(line.rstrip())
    
    try:
        # Show bot output in real-time
        forward_output()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
        bot_process.terminate()
        dashboard_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()