#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
set -a
source .env
if [ -f /root/.openclaw/workspace/projects/bybit-demo-bot/config.env ]; then
  source /root/.openclaw/workspace/projects/bybit-demo-bot/config.env
fi
set +a
exec /root/.venvs/bybit-bot/bin/python /root/.openclaw/workspace/projects/bybit-demo-bot/bot.py
