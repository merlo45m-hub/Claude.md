#!/bin/bash
set -e
mkdir -p /root/ai_stock_trader
cd /root/ai_stock_trader
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install yfinance pandas numpy backtrader
echo "Setup complete. Activate with 'source venv/bin/activate'"