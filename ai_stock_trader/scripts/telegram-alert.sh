#!/bin/bash
# Send alert message via Telegram bot.
# The token lives in ~/.hermes/.env (TELEGRAM_BOT_TOKEN) — never hardcode it.
set -euo pipefail

[ -f "$HOME/.hermes/.env" ] && . "$HOME/.hermes/.env"
TOKEN="${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN not set}"
CHAT_ID="${TELEGRAM_CHAT_ID:-8382253048}"
LEVEL="${1:-INFO}"
MSG="${2:-No message}"

curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
  -d "chat_id=$CHAT_ID" \
  -d "text=[$LEVEL] ai-stock-trader: $MSG" \
  -d "parse_mode=Markdown" \
  -o /dev/null -w "%{http_code}" 2>/dev/null || echo "failed"
