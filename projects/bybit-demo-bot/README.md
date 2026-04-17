# Bybit Demo Bot

Demo bot for Bybit Unified Trading (V5) using `pybit`.

## Run
```bash
cd /root/.openclaw/workspace/projects/bybit-demo-bot
source /root/.venvs/bybit-bot/bin/activate
python bot.py
```

`bybit-demo-bot.service` loads `/root/.openclaw/workspace/.env` first, then `projects/bybit-demo-bot/config.env` to override bot parameters.

## Main behavior
- Uses EMA + RSI + ADX signal from **closed candle** only.
- Blocks overtrading with:
  - `MIN_ENTRY_INTERVAL_SECONDS`
  - `MAX_TRADES_PER_DAY`
  - `LOSS_COOLDOWN_SECONDS`
- Risk sizing by `MAX_RISK_PCT` and `MAX_POSITION_PCT`.
- Auto TP/SL + ATR trailing stop.
- Loss streak now triggers temporary cooldown (auto-resume), not day-long hard pause.
- Daily protection: max loss, max drawdown, daily target stop.
- Trade events are persisted to both:
  - JSONL: `trades_v2.log.jsonl`
  - SQLite: `trades_v2.db` (`trade_events` table)

## Tune quickly (`config.env`)
- Signal quality:
  - `MIN_ADX`, `MIN_EMA_GAP_PCT`
  - `RSI_LONG_FLOOR`, `RSI_LONG_CEILING`
  - `RSI_SHORT_FLOOR`, `RSI_SHORT_CEILING`
- Risk:
  - `MAX_RISK_PCT`, `MAX_POSITION_PCT`
  - `MAX_DAILY_LOSS_PCT`, `MAX_DRAWDOWN_PCT`
- Trading pace:
  - `MIN_ENTRY_INTERVAL_SECONDS`, `MAX_TRADES_PER_DAY`, `LOSS_COOLDOWN_SECONDS`

## Ops
```bash
systemctl status bybit-demo-bot --no-pager
journalctl -u bybit-demo-bot -n 100 --no-pager
tail -f /root/.openclaw/workspace/projects/bybit-demo-bot/bot_v2_runtime.log
sqlite3 /root/.openclaw/workspace/projects/bybit-demo-bot/trades_v2.db "SELECT event_type, COUNT(*) FROM trade_events GROUP BY event_type;"
```

Use demo keys first. Do not enable withdrawals on API key.
