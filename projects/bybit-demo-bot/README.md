# Bybit Demo Memecoin Bot (OpenClaw workspace)

This is a **demo-only** trading bot scaffold for Bybit Unified Trading (V5) using `pybit`.

## Safety
- Create a Bybit API key with **Read + Trade only**.
- **Disable withdrawals**.
- Prefer **IP whitelist**.
- Run in **DEMO** first.

## Setup
Set env vars (PowerShell):
```powershell
setx BYBIT_API_KEY "..."
setx BYBIT_API_SECRET "..."
setx BYBIT_DEMO "true"
```
Re-open terminal after `setx`.

## Run
```powershell
cd "C:\Users\ADMIN\.openclaw\workspace\projects\bybit-demo-bot"
python .\bot.py
```

## What it does
- Picks a liquid, high-volatility **USDT perpetual** symbol (excluding majors).
- Trend filter on **15m EMA(50/200)**
- Entry trigger on **1m RSI**
- Cooldown: max **1 entry per 15 minutes**
- One position at a time
- Sets leverage (default 50x)
- Sets TP/SL immediately using `set_trading_stop`

> No profit guarantees. This is a testing harness.
