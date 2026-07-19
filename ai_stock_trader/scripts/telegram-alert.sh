#!/bin/bash
# Send alert message via Telegram bot
# Uses overseer's telegram_token from profile config
set -euo pipefail

TOKEN="8635156326:AAF3TjbCOijbvMnzwRlIJYmbZRguidZS5PE"
CHAT_ID="8382253048"
LEVEL="${1:-INFO}"
MSG="${2:-No message}"

curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
  -d "chat_id=$CHAT_ID" \
  -d "text=[$LEVEL] ai-stock-trader: $MSG" \
  -d "parse_mode=Markdown" \
  -o /dev/null -w "%{http_code}" 2>/dev/null || echo "failed"
