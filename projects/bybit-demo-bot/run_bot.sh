#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace
set -a
source .env
set +a
exec /root/.venvs/bybit-bot/bin/python /root/.openclaw/workspace/projects/bybit-demo-bot/bot.py
