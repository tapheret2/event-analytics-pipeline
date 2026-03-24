"""Bybit demo trading bot (starter scaffold)

Safety:
- Designed for DEMO/Testnet only.
- First 5 orders are dry-run by default.
- Reads creds from .env (local file). Never paste keys in chat.

Usage:
  python scripts/bybit_demo_bot.py --symbol BTCUSDT --side Buy --qty 0.001 --market

Notes:
- This is a minimal scaffold; we will add strategy logic after credentials are set.
"""

import argparse
import os
import time


def load_dotenv(path: str = ".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--side", choices=["Buy", "Sell"], required=True)
    ap.add_argument("--qty", type=float, required=True)
    ap.add_argument("--market", action="store_true")
    ap.add_argument("--limit", type=float, default=None)
    ap.add_argument("--dry-run", action="store_true", help="Print order instead of sending")
    args = ap.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    key = os.getenv("BYBIT_API_KEY")
    secret = os.getenv("BYBIT_API_SECRET")
    demo = os.getenv("BYBIT_DEMO", "true").lower() in ("1", "true", "yes")

    if not key or not secret:
        raise SystemExit("Missing BYBIT_API_KEY/BYBIT_API_SECRET. Put them in workspace .env (see .env.example).")
    if not demo:
        raise SystemExit("BYBIT_DEMO is not true. Refusing to run.")

    order = {
        "symbol": args.symbol,
        "side": args.side,
        "qty": args.qty,
        "type": "Market" if args.market else "Limit",
        "price": args.limit,
        "ts": int(time.time() * 1000),
    }

    # For now: always dry-run unless user explicitly removes it in code.
    if args.dry_run or True:
        print("[DRY-RUN] Would place order:")
        print(order)
        print("\nNext step: implement Bybit API call (pybit) after keys are safely stored.")
        return


if __name__ == "__main__":
    main()
