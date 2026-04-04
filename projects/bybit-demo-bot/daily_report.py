from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
TRADE_LOG_PATH = BASE_DIR / "trades_v2.log.jsonl"
STATE_PATH = BASE_DIR / "state_v2.json"


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def load_events() -> list[dict[str, Any]]:
    if not TRADE_LOG_PATH.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in TRADE_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start

    events = load_events()
    yesterday_events = []
    for e in events:
        ts = e.get("ts")
        if not ts:
            continue
        try:
            dt = parse_ts(ts)
        except Exception:
            continue
        if yesterday_start <= dt < yesterday_end:
            yesterday_events.append(e)

    opened = [e for e in yesterday_events if e.get("event") == "trade_opened"]
    closed = [e for e in yesterday_events if e.get("event") == "trade_closed"]

    pnl = 0.0
    wins = 0
    losses = 0
    for e in closed:
        trade_pnl = float(e.get("realized_pnl_est") or 0.0)
        pnl += trade_pnl
        if trade_pnl > 0:
            wins += 1
        elif trade_pnl < 0:
            losses += 1

    state = load_state()
    open_trade = state.get("open_trade")
    status = "Đang flat"
    if open_trade:
        status = f"Đang giữ lệnh {open_trade.get('side', '?')} @ {open_trade.get('entry_price', '?')}"

    symbols = Counter(e.get("symbol", "BTCUSDT") for e in opened)
    symbol_text = ", ".join(f"{sym} x{count}" for sym, count in symbols.items()) if symbols else "Không có"

    report = [
        "Bybit bot report hôm qua",
        f"Ngày UTC: {yesterday_start.strftime('%Y-%m-%d')}",
        f"PnL đã đóng: {pnl:+.2f} USDT",
        f"Số lệnh mở: {len(opened)}",
        f"Số lệnh đóng: {len(closed)}",
        f"Win/Loss: {wins}/{losses}",
        f"Symbol: {symbol_text}",
        f"Trạng thái hiện tại: {status}",
    ]

    print("\n".join(report))


if __name__ == "__main__":
    main()
