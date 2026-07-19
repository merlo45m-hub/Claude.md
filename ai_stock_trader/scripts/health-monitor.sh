#!/bin/bash
# Health monitor for ai-stock-trader — checks containers, restarts if dead, alerts via hermes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$SCRIPT_DIR/logs/health-monitor.log"
mkdir -p "$(dirname "$LOG")"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}

alert() {
  local msg="$1"
  log "ALERT: $msg"
  # Send via hermes telegram if available
  /root/ai_stock_trader/scripts/telegram-alert.sh "CRITICAL" "$msg"
}

# Check dashboard
if ! curl -sf --max-time 5 http://localhost:8085/api/status > /dev/null 2>&1; then
  log "Dashboard unreachable, attempting restart..."
  docker restart ai-stock-dashboard 2>> "$LOG" || {
    log "Failed to restart dashboard container, attempting docker-compose up..."
    cd "$SCRIPT_DIR" && docker compose up -d web 2>> "$LOG" || alert "dashboard DOWN - manual intervention needed"
  }
  sleep 5
  if curl -sf --max-time 5 http://localhost:8085/api/status > /dev/null 2>&1; then
    log "Dashboard recovered after restart"
  else
    alert "dashboard still down after restart"
  fi
fi

# Check trader
if ! docker ps --format '{{.Names}}' | grep -q '^ai-stock-trader$'; then
  log "Trader container not running, restarting..."
  docker start ai-stock-trader 2>> "$LOG" || {
    cd "$SCRIPT_DIR" && docker compose up -d trader 2>> "$LOG" || alert "trader DOWN - manual intervention needed"
  }
  sleep 5
  if docker ps --format '{{.Names}}' | grep -q '^ai-stock-trader$'; then
    log "Trader recovered"
  else
    alert "trader still down after restart"
  fi
fi

# Quick health: check if trader made trades recently
LAST_TRADE=$(sqlite3 "$SCRIPT_DIR/trading_data.db" "SELECT MAX(timestamp) FROM trades;" 2>/dev/null || echo "never")
if [ -n "$LAST_TRADE" ] && [ "$LAST_TRADE" != "never" ]; then
  NOW_EPOCH=$(date +%s)
  TRADE_EPOCH=$(date -d "$LAST_TRADE" +%s 2>/dev/null || echo 0)
  if [ "$TRADE_EPOCH" -gt 0 ] && [ $((NOW_EPOCH - TRADE_EPOCH)) -gt 3600 ]; then
    log "WARNING: No trades in last hour (last: $LAST_TRADE)"
  fi
fi

log "Health check passed"
