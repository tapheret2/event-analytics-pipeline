from __future__ import annotations

import os
import sys
import time
import json
import signal
import subprocess
from pathlib import Path
from typing import Optional

import psutil

from pybit.unified_trading import HTTP

BOT_DIR = Path(r"C:\Users\ADMIN\.openclaw\workspace\projects\bybit-demo-bot")
BOT_PATH = BOT_DIR / "bot_btc15m_v3.py"
RUNTIME_LOG = BOT_DIR / "bot_v3_runtime.log"


def read_hkcu_env(name: str) -> Optional[str]:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
            val, _typ = winreg.QueryValueEx(k, name)
            if isinstance(val, str) and val:
                return val
    except Exception:
        return None
    return None


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    # Prefer registry (setx) over current process env.
    v = read_hkcu_env(name)
    if v:
        return v
    v = os.environ.get(name)
    return v if v else default


def find_bot_procs() -> list[psutil.Process]:
    procs: list[psutil.Process] = []
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = p.info.get("cmdline") or []
            if not cmd:
                continue
            # match exact script path in cmdline
            if any(str(BOT_PATH).lower() == str(part).strip('"').lower() for part in cmd):
                procs.append(p)
        except Exception:
            pass
    return procs


def bybit_session() -> HTTP:
    api = get_env("BYBIT_API_KEY")
    sec = get_env("BYBIT_API_SECRET")
    demo = (get_env("BYBIT_DEMO", "true") or "true").lower() in ("1", "true", "yes", "y")
    testnet = (get_env("BYBIT_TESTNET", "false") or "false").lower() in ("1", "true", "yes", "y")
    if not api or not sec:
        raise RuntimeError("Missing BYBIT_API_KEY/BYBIT_API_SECRET")
    s = HTTP(api_key=api, api_secret=sec, demo=demo, testnet=testnet, recv_window=10_000, timeout=20)
    return s


def get_btc_position_text() -> str:
    try:
        s = bybit_session()
        res = s.get_positions(category="linear", symbol="BTCUSDT")
        lst = (res.get("result", {}) or {}).get("list", [])
        if not lst:
            return "POS: (no list)"
        p = lst[0]
        size = float(p.get("size", 0) or 0)
        if size == 0:
            return "POS: FLAT"
        return (
            f"POS: {p.get('side')} size={p.get('size')} avg={p.get('avgPrice')} "
            f"uPnL={p.get('unrealisedPnl')} TP={p.get('takeProfit')} SL={p.get('stopLoss')}"
        )
    except Exception as e:
        return f"POS: ERROR {str(e)[:200]}"


def start_bot() -> subprocess.Popen:
    if not BOT_PATH.exists():
        raise RuntimeError(f"Bot file not found: {BOT_PATH}")

    # Start bot detached from this console, but we will kill it when controller exits.
    # Redirect output to a log file.
    logf = open(RUNTIME_LOG, "a", encoding="utf-8")

    # CREATE_NEW_PROCESS_GROUP lets us send CTRL_BREAK_EVENT on Windows if needed.
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    p = subprocess.Popen(
        [sys.executable, "-u", str(BOT_PATH)],
        cwd=str(BOT_DIR),
        stdout=logf,
        stderr=logf,
        creationflags=creationflags,
    )
    return p


def stop_bot_pids(pids: list[int]):
    for pid in pids:
        try:
            p = psutil.Process(pid)
            p.terminate()
        except Exception:
            pass

    gone, alive = psutil.wait_procs([psutil.Process(pid) for pid in pids if psutil.pid_exists(pid)], timeout=5)
    for p in alive:
        try:
            p.kill()
        except Exception:
            pass


def main():
    # Basic banner
    print("Bybit Bot v3 Controller")
    print("- If bot is not running: start it")
    print("- If bot is running: show status")
    print("- Close this window to stop bot")
    print("")

    managed_pids: list[int] = []
    started_proc: Optional[subprocess.Popen] = None

    # Adopt existing bot if present
    existing = find_bot_procs()
    if existing:
        managed_pids = [p.pid for p in existing]
        print(f"BOT: running (pids={managed_pids})")
    else:
        print("BOT: not running -> starting...")
        started_proc = start_bot()
        managed_pids = [started_proc.pid]
        time.sleep(2)
        print(f"BOT: started (pid={started_proc.pid})")

    # Status loop
    try:
        while True:
            # refresh pids (in case it respawned)
            procs = find_bot_procs()
            pids = [p.pid for p in procs]
            print("")
            print(time.strftime("%Y-%m-%d %H:%M:%S"), "BOT_PIDS:", pids if pids else "(none)")
            print(get_btc_position_text())
            print(f"Runtime log: {RUNTIME_LOG}")
            print("(Close this window to stop bot)")
            time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        # Stop bot on exit
        # If bot existed before, we still stop it (user asked close tab to stop).
        pids = [p.pid for p in find_bot_procs()]
        if pids:
            print("\nStopping bot...", pids)
            stop_bot_pids(pids)
        print("Stopped.")


if __name__ == "__main__":
    main()
