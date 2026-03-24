"""Bybit DEMO auto-trader (guardrailed)

Runs on Bybit DEMO only.

Strategy (default): EMA(9/21) crossover on 5m closes (BTCUSDT linear perp).

Guardrails (required):
- max_orders_per_day
- max_daily_drawdown_pct (negative number, e.g. -30)
- one position at a time
- min cooldown enforced (>= 15s) even if user requests 0

Usage:
  python scripts/bybit_demo_trader.py --symbol BTCUSDT --leverage 5 --mode auto \
    --max-orders 10 --max-dd -30 --cooldown 0

Stop:
  Ctrl+C

Notes:
- Reads creds from workspace .env: BYBIT_API_KEY, BYBIT_API_SECRET, BYBIT_DEMO=true
"""

from __future__ import annotations

import argparse
import math
import os
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import subprocess


def env_true(name: str) -> bool:
    v = os.getenv(name, "").strip().lower()
    return v in {"1", "true", "yes", "y"}


def ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    out = []
    # seed with SMA
    sma = sum(values[:period]) / period
    out.append(sma)
    for v in values[period:]:
        out.append((v - out[-1]) * k + out[-1])
    return out


def round_step(x: float, step: float) -> float:
    return math.floor(x / step) * step


def now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def notify_telegram(text: str) -> None:
    # Best-effort notification to Phát via OpenClaw CLI.
    try:
        subprocess.run(
            [
                "openclaw",
                "message",
                "send",
                "--channel",
                "telegram",
                "--target",
                "telegram:1914302791",
                "--message",
                text,
                "--silent",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--leverage", type=int, default=5)
    ap.add_argument("--mode", choices=["auto", "dry"], default="auto")
    ap.add_argument("--max-orders", type=int, default=10)
    ap.add_argument("--max-dd", type=float, default=-30.0, help="Max daily drawdown percent (negative)")
    ap.add_argument("--cooldown", type=int, default=0, help="Seconds between trades (min 15s enforced)")
    ap.add_argument("--risk-pct", type=float, default=10.0, help="Position notional as %% of equity")
    ap.add_argument("--tp", type=float, default=0.6, help="Take profit percent (e.g. 0.6 for 0.6%%)")
    ap.add_argument("--sl", type=float, default=0.4, help="Stop loss percent")
    ap.add_argument("--interval", default="5")
    ap.add_argument("--poll", type=int, default=20, help="Seconds between signal checks")
    args = ap.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    if not env_true("BYBIT_DEMO"):
        raise SystemExit("BYBIT_DEMO is not true; refusing to run.")

    key = os.getenv("BYBIT_API_KEY")
    secret = os.getenv("BYBIT_API_SECRET")
    if not key or not secret:
        raise SystemExit("Missing BYBIT_API_KEY/BYBIT_API_SECRET in .env")

    # Enforce sane minimum cooldown
    cooldown = max(int(args.cooldown), 15)

    session = HTTP(
        demo=True,
        api_key=key,
        api_secret=secret,
        recv_window=30000,
    )

    print(f"[{now_local()}] DEMO auto-trader starting | symbol={args.symbol} lev={args.leverage} mode={args.mode}")
    print(f"Guardrails: maxOrders={args.max_orders}/day maxDD={args.max_dd}% cooldown>={cooldown}s onePosition=true")
    notify_telegram(f"[Bybit DEMO] Bot started: {args.symbol} lev={args.leverage} mode={args.mode} | maxOrders={args.max_orders}/day maxDD={args.max_dd}%")

    # Connectivity
    t = session.get_tickers(category="linear", symbol=args.symbol)
    last = float(t["result"]["list"][0]["lastPrice"])
    print(f"[{now_local()}] Connected. lastPrice={last}")

    # Set leverage best-effort
    if args.mode == "auto":
        try:
            session.set_leverage(category="linear", symbol=args.symbol, buyLeverage=str(args.leverage), sellLeverage=str(args.leverage))
            print(f"[{now_local()}] Leverage set to {args.leverage}x")
        except Exception as e:
            # Avoid Windows console encoding issues (e may include unicode arrows, etc.)
            # Ensure message is ASCII-safe for Windows cp1252 console
            msg = str(e).encode("ascii", "backslashreplace").decode("ascii")
            print(f"[{now_local()}] WARN leverage set failed (continuing): {msg}")

    # Starting equity (for daily DD)
    def get_equity() -> float:
        # Demo accounts may vary (UNIFIED / CONTRACT / SPOT). Try a few.
        last_err = None
        for acct in ("UNIFIED", "CONTRACT", "SPOT"):
            try:
                bal = session.get_wallet_balance(accountType=acct, coin="USDT")
                coin = bal["result"]["list"][0]["coin"][0]
                eq = float(coin.get("equity") or coin.get("walletBalance") or 0.0)
                if eq > 0:
                    return eq
            except Exception as e:
                last_err = e
                continue
        raise Exception(f"Failed to read equity from demo wallet (tried UNIFIED/CONTRACT/SPOT). Last error: {last_err}")

    start_equity = get_equity()
    print(f"[{now_local()}] Start equity (USDT): {start_equity}")

    # Daily counters
    day_key = datetime.now().strftime("%Y-%m-%d")
    orders_today = 0
    last_trade_ts = 0.0

    def reset_if_new_day():
        nonlocal day_key, orders_today, start_equity
        dk = datetime.now().strftime("%Y-%m-%d")
        if dk != day_key:
            day_key = dk
            orders_today = 0
            start_equity = get_equity()
            print(f"[{now_local()}] New day reset. start_equity={start_equity}")

    def dd_pct() -> float:
        eq = get_equity()
        if start_equity <= 0:
            return 0.0
        return (eq - start_equity) / start_equity * 100.0

    def has_open_position() -> bool:
        pos = session.get_positions(category="linear", symbol=args.symbol)
        for p in pos["result"]["list"]:
            size = float(p.get("size") or 0)
            if size != 0:
                return True
        return False

    def place_trade(side: str):
        nonlocal orders_today, last_trade_ts

        # Cooldown
        if time.time() - last_trade_ts < cooldown:
            return

        # Guardrails
        if orders_today >= args.max_orders:
            print(f"[{now_local()}] Max orders/day reached. Stopping.")
            raise SystemExit(0)

        cur_dd = dd_pct()
        if cur_dd <= args.max_dd:
            print(f"[{now_local()}] Daily DD limit hit ({cur_dd:.2f}% <= {args.max_dd}%). Stopping.")
            raise SystemExit(0)

        if has_open_position():
            return

        # Price
        t = session.get_tickers(category="linear", symbol=args.symbol)
        price = float(t["result"]["list"][0]["lastPrice"])

        # Size: notional = equity * riskPct * leverage; qty = notional / price
        equity = get_equity()
        notional = equity * (args.risk_pct / 100.0) * args.leverage
        qty = notional / price
        qty = max(round_step(qty, 0.001), 0.001)  # BTC step

        tp = price * (1 + args.tp / 100.0) if side == "Buy" else price * (1 - args.tp / 100.0)
        sl = price * (1 - args.sl / 100.0) if side == "Buy" else price * (1 + args.sl / 100.0)

        if args.mode != "auto":
            print(f"[{now_local()}] [DRY] {side} {args.symbol} qty={qty} price~{price} TP={tp:.1f} SL={sl:.1f}")
            last_trade_ts = time.time()
            return

        msg = f"[Bybit DEMO] PLACE {side} {args.symbol} qty={qty} price~{price:.1f} TP={tp:.1f} SL={sl:.1f}"
        print(f"[{now_local()}] PLACE {side} {args.symbol} qty={qty} price~{price} TP={tp:.1f} SL={sl:.1f}")
        notify_telegram(msg)
        res = session.place_order(
            category="linear",
            symbol=args.symbol,
            side=side,
            orderType="Market",
            qty=str(qty),
            timeInForce="IOC",
            reduceOnly=False,
        )
        oid = res.get("result", {}).get("orderId")
        print(f"[{now_local()}] OrderId={oid}")
        notify_telegram(f"[Bybit DEMO] Order placed. orderId={oid}")

        # Set TP/SL (best-effort)
        try:
            session.set_trading_stop(
                category="linear",
                symbol=args.symbol,
                takeProfit=str(tp),
                stopLoss=str(sl),
                tpTriggerBy="LastPrice",
                slTriggerBy="LastPrice",
                positionIdx=0,
            )
            print(f"[{now_local()}] TP/SL set")
            notify_telegram("[Bybit DEMO] TP/SL set")
        except Exception as e:
            print(f"[{now_local()}] WARN set TP/SL failed: {e}")
            notify_telegram(f"[Bybit DEMO] WARN: set TP/SL failed: {e}")

        orders_today += 1
        last_trade_ts = time.time()

    # Main loop
    while True:
        reset_if_new_day()

        # Signal calc
        candles = session.get_kline(category="linear", symbol=args.symbol, interval=args.interval, limit=60)
        k = list(reversed(candles["result"]["list"]))  # oldest -> newest
        closes = [float(x[4]) for x in k]

        e9 = ema(closes, 9)
        e21 = ema(closes, 21)
        if not e9 or not e21:
            time.sleep(args.poll)
            continue

        # Align lengths
        # ema list starts after seed; use last two points
        a = e9[-2] - e21[-2]
        b = e9[-1] - e21[-1]

        # Crossover detection
        if a <= 0 and b > 0:
            print(f"[{now_local()}] Signal: BUY crossover")
            place_trade("Buy")
        elif a >= 0 and b < 0:
            print(f"[{now_local()}] Signal: SELL crossover")
            place_trade("Sell")

        # Heartbeat
        if int(time.time()) % 300 < args.poll:
            try:
                print(f"[{now_local()}] status ordersToday={orders_today} dd={dd_pct():.2f}% openPos={has_open_position()}")
            except Exception:
                pass

        time.sleep(args.poll)


if __name__ == "__main__":
    main()
