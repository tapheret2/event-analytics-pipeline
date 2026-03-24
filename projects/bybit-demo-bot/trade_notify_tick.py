import json, os, sys, datetime
from pathlib import Path

STATE_PATH = Path(r"C:/Users/ADMIN/.openclaw/workspace/projects/bybit-demo-bot/notify_state_btcusdt.json")
SYMBOL = "BTCUSDT"
CATEGORY = "linear"


def now_bkk():
    tz = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz)


def load_state():
    if not STATE_PATH.exists():
        return {"hasPosition": False, "side": None, "size": 0.0, "avgPrice": None, "ts": None}
    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"hasPosition": False, "side": None, "size": 0.0, "avgPrice": None, "ts": None}


def write_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_env_creds():
    key = os.getenv("BYBIT_API_KEY")
    secret = os.getenv("BYBIT_API_SECRET")
    demo = os.getenv("BYBIT_DEMO")

    if (not key or not secret) and os.name == "nt":
        # Try HKCU\\Environment
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
                if not key:
                    try:
                        key = winreg.QueryValueEx(k, "BYBIT_API_KEY")[0]
                    except FileNotFoundError:
                        pass
                if not secret:
                    try:
                        secret = winreg.QueryValueEx(k, "BYBIT_API_SECRET")[0]
                    except FileNotFoundError:
                        pass
                if demo is None:
                    try:
                        demo = winreg.QueryValueEx(k, "BYBIT_DEMO")[0]
                    except FileNotFoundError:
                        pass
        except Exception:
            pass

    if not demo:
        demo = "true"

    if not key or not secret:
        raise RuntimeError("Missing BYBIT_API_KEY/BYBIT_API_SECRET in env or HKCU\\Environment")

    return key, secret, str(demo).lower() in ("1", "true", "yes", "y", "on")


def fetch_position(api_key, api_secret, demo=True):
    # pybit unified_trading
    from pybit.unified_trading import HTTP

    session = HTTP(
        demo=demo,      # Bybit demo environment (api-demo.bybit.com)
        testnet=False,  # keep false unless you explicitly use testnet keys
        api_key=api_key,
        api_secret=api_secret,
    )

    resp = session.get_positions(category=CATEGORY, symbol=SYMBOL)
    # Expected: { 'retCode':0, 'result': {'list':[...]} }
    if not isinstance(resp, dict) or resp.get("retCode") not in (0, "0"):
        raise RuntimeError(f"Bybit get_positions failed: {resp}")

    lst = (((resp.get("result") or {}).get("list")) or [])
    if not lst:
        # treat as flat
        return {"hasPosition": False, "side": None, "size": 0.0, "avgPrice": None}

    # Bybit returns one entry per symbol/positionIdx. For USDT linear, position may exist with size 0.
    # pick the entry with non-zero size if any, else first.
    def parse_entry(e):
        side = e.get("side")
        size = float(e.get("size") or 0)
        avg = e.get("avgPrice")
        try:
            avg_f = float(avg) if avg not in (None, "") else None
        except Exception:
            avg_f = None
        has_pos = size != 0.0 and side in ("Buy", "Sell")
        return has_pos, side if has_pos else None, abs(size), avg_f

    parsed = [parse_entry(e) for e in lst]
    # choose non-flat first
    for has_pos, side, size, avg in parsed:
        if has_pos:
            return {"hasPosition": True, "side": side, "size": size, "avgPrice": avg}

    return {"hasPosition": False, "side": None, "size": 0.0, "avgPrice": None}


def main():
    prev = load_state()
    api_key, api_secret, demo = get_env_creds()

    cur = fetch_position(api_key, api_secret, demo=demo)

    # Determine transitions
    prev_has = bool(prev.get("hasPosition"))
    cur_has = bool(cur.get("hasPosition"))
    prev_side = prev.get("side")
    cur_side = cur.get("side")

    events = []
    if not prev_has and cur_has:
        events.append(("OPEN", cur))
    elif prev_has and not cur_has:
        events.append(("CLOSE", prev))
    elif prev_has and cur_has and prev_side and cur_side and prev_side != cur_side:
        # side flip
        events.append(("CLOSE", prev))
        events.append(("OPEN", cur))

    # Write snapshot regardless
    new_state = {
        "hasPosition": cur_has,
        "side": cur_side,
        "size": float(cur.get("size") or 0.0),
        "avgPrice": cur.get("avgPrice"),
        "ts": now_bkk().isoformat(),
        "demo": bool(demo),
        "symbol": SYMBOL,
        "category": CATEGORY,
    }
    write_state(new_state)

    if not events:
        sys.stdout.write("NO_REPLY")
        return

    t = now_bkk().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    for kind, data in events:
        side = data.get("side")
        size = data.get("size")
        avg = data.get("avgPrice")
        avg_s = f"{avg:.2f}" if isinstance(avg, (int, float)) else (str(avg) if avg is not None else "-")
        size_s = f"{float(size):g}" if size is not None else "-"
        lines.append(f"[{t} BKK] BTCUSDT {kind} ({'DEMO' if demo else 'LIVE'})\nSide: {side}\nSize: {size_s}\nAvgPrice: {avg_s}")

    # Output instructions (do not send directly)
    out = "\n\n".join(lines)
    sys.stdout.write("Send Telegram message to Phát (Telegram):\n" + out)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # fail loudly so cron run shows error
        raise
