#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$SCRIPT_DIR/data/health-monitor.log"
mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }
alert() {
  local msg="$1"; log "ALERT: $msg"
  /root/ai_stock_trader/scripts/telegram-alert.sh "CRITICAL" "crypto-bot: $msg" 2>/dev/null || true
}

# Check bot process
BOT_PID=$(pgrep -f "src.main" 2>/dev/null || true)
if [ -z "$BOT_PID" ]; then
  log "Bot process dead, restarting..."
  cd "$SCRIPT_DIR" && nohup .venv/bin/python -m src.main > /tmp/crypto-bot.log 2>&1 &
  sleep 5
  if pgrep -f "src.main" > /dev/null 2>&1; then
    log "Bot recovered (PID $(pgrep -f 'src.main'))"
  else
    alert "bot failed to restart — manual intervention needed"
  fi
fi

# Check web server
WEB_PID=$(pgrep -f "src.web.server" 2>/dev/null || true)
if [ -z "$WEB_PID" ]; then
  log "Web server dead, restarting..."
  cd "$SCRIPT_DIR" && nohup .venv/bin/python -m src.web.server > /tmp/crypto-web.log 2>&1 &
  sleep 3
  if pgrep -f "src.web.server" > /dev/null 2>&1; then
    log "Web server recovered"
  else
    alert "web server failed to restart"
  fi
fi

# Check web API responds
if ! curl -sf --max-time 5 http://localhost:8080/api/summary > /dev/null 2>&1; then
  alert "dashboard API not responding"
fi

# Check recent heartbeat — if no cycle in 10min, something is stuck
LAST_CYCLE=$(sqlite3 "$SCRIPT_DIR/data/trades.db" "SELECT MAX(timestamp) FROM cycle_log;" 2>/dev/null || echo "never")
if [ -n "$LAST_CYCLE" ] && [ "$LAST_CYCLE" != "never" ]; then
  NOW=$(date +%s)
  CYCLE_EPOCH=$(date -d "$LAST_CYCLE" +%s 2>/dev/null || echo 0)
  if [ "$CYCLE_EPOCH" -gt 0 ] && [ $((NOW - CYCLE_EPOCH)) -gt 600 ]; then
    log "WARNING: No cycle in 10min (last: $LAST_CYCLE)"
  fi
fi

log "Health check passed"
