#!/bin/bash
# Daily cleanup script for AI Stock Trading Bot
# Removes old trades and portfolio data to maintain database size

DB_PATH="/root/ai_stock_trader/trading_data.db"

if [ -f "$DB_PATH" ]; then
    # Delete trades older than 30 days
    sqlite3 "$DB_PATH" "DELETE FROM trades WHERE timestamp < datetime('now', '-30 days')"
    echo "Cleaned trades older than 30 days at $(date)"
    
    # Delete portfolio data older than 90 days (if needed)
    sqlite3 "$DB_PATH" "DELETE FROM portfolio WHERE timestamp < datetime('now', '-90 days')"
    echo "Cleaned portfolio data older than 90 days at $(date)"
    
    # Show stats
    trades_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM trades")
    echo "Remaining trades: $trades_count"
else
    echo "Database not found at $DB_PATH" >&2
fi