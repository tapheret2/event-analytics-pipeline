from __future__ import annotations

import os
import sys
import time
import math
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from pybit.unified_trading import HTTP

# Console output safety
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ----------------------------
# Windows-friendly env
# ----------------------------

def get_env(name: str) -> str | None:
    r"""Get env var.

    On Windows, prefer HKCU\Environment (setx) because the current agent process
    may have stale environment variables.
    """
    reg_val: str | None = None
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
                val, _typ = winreg.QueryValueEx(k, name)
                if isinstance(val, str) and val:
                    reg_val = val
        except Exception:
            reg_val = None

    if reg_val:
        return reg_val

    v = os.environ.get(name)
    return v if v else None


def load_env_file(path: str):
    if not os.path.exists(path):
        return
    for line in open(path, "r", encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # don't overwrite existing
        if k and k not in os.environ:
            os.environ[k] = v


# ----------------------------
# Indicators
# ----------------------------

def ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        raise ValueError("not enough values for EMA")
    k = 2 / (period + 1)
    out = []
    sma = sum(values[:period]) / period
    out.append(sma)
    for v in values[period:]:
        out.append(out[-1] + k * (v - out[-1]))
    return [out[0]] * (period - 1) + out


def atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float]:
    if len(closes) < period + 1:
        raise ValueError("not enough values for ATR")
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    first = sum(trs[:period]) / period
    out = [first]
    for tr in trs[period:]:
        out.append((out[-1] * (period - 1) + tr) / period)
    return [out[0]] * (period) + out


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_ms() -> int:
    return int(time.time() * 1000)


# ----------------------------
# Bybit helpers
# ----------------------------


def make_session() -> HTTP:
    api_key = get_env("BYBIT_API_KEY")
    api_secret = get_env("BYBIT_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("Missing BYBIT_API_KEY / BYBIT_API_SECRET")

    demo = (get_env("BYBIT_DEMO") or "true").lower() in ("1", "true", "yes", "y")
    testnet = (get_env("BYBIT_TESTNET") or "false").lower() in ("1", "true", "yes", "y")

    s = HTTP(
        api_key=api_key,
        api_secret=api_secret,
        demo=demo,
        testnet=testnet,
        recv_window=10_000,
        timeout=20,
    )

    if demo and "api-demo" not in s.endpoint:
        raise SystemExit(f"Refusing to run: demo=true but endpoint is {s.endpoint}")

    return s


def get_equity_usdt(session: HTTP) -> float:
    resp = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
    item = (resp.get("result", {}) or {}).get("list", [])
    coins = (item[0] or {}).get("coin", []) if item else []
    usdt = next((c for c in coins if c.get("coin") == "USDT"), None)
    if not usdt:
        raise RuntimeError("USDT balance not found")
    v = usdt.get("totalEquity") or usdt.get("equity") or usdt.get("walletBalance")
    return float(v)


def get_klines(session: HTTP, category: str, symbol: str, interval: str, limit: int = 300):
    resp = session.get_kline(category=category, symbol=symbol, interval=interval, limit=limit)
    rows = (resp.get("result", {}) or {}).get("list", [])
    return list(reversed(rows))


def parse_ohlc(rows):
    o, h, l, c = [], [], [], []
    for r in rows:
        o.append(float(r[1])); h.append(float(r[2])); l.append(float(r[3])); c.append(float(r[4]))
    return o, h, l, c


def get_position(session: HTTP, category: str, symbol: str) -> Optional[dict[str, Any]]:
    resp = session.get_positions(category=category, symbol=symbol)
    lst = (resp.get("result", {}) or {}).get("list", [])
    if not lst:
        return None
    p = lst[0]
    size = float(p.get("size", 0) or 0)
    return p if size != 0 else None


def get_limits(session: HTTP, category: str, symbol: str) -> dict[str, float]:
    info = session.get_instruments_info(category=category, symbol=symbol)["result"]["list"][0]
    lot = info.get("lotSizeFilter", {})
    pf = info.get("priceFilter", {})
    lf = info.get("leverageFilter", {})
    return {
        "minOrderQty": float(lot.get("minOrderQty", 0) or 0),
        "maxOrderQty": float(lot.get("maxOrderQty", 0) or 0),
        "maxMktOrderQty": float(lot.get("maxMktOrderQty", 0) or 0),
        "qtyStep": float(lot.get("qtyStep", 0) or 0),
        "minNotionalValue": float(lot.get("minNotionalValue", 0) or 0),
        "tickSize": float(pf.get("tickSize", 0) or 0),
        "maxLeverage": float(lf.get("maxLeverage", 0) or 0),
    }


def _round_down(x: float, step: float) -> float:
    return math.floor(x / step) * step if step > 0 else x


def _round_up(x: float, step: float) -> float:
    return math.ceil(x / step) * step if step > 0 else x


def fmt_price(x: float, tick: float, mode: str) -> str:
    if tick > 0:
        x = _round_down(x, tick) if mode == "down" else _round_up(x, tick)
    return f"{x:.10f}".rstrip("0").rstrip(".")


def set_leverage(session: HTTP, category: str, symbol: str, lev: int, max_lev: float):
    use = min(lev, int(max_lev) if max_lev else lev)
    use = max(1, use)
    session.set_leverage(category=category, symbol=symbol, buyLeverage=str(use), sellLeverage=str(use))
    return use


def place_market(session: HTTP, category: str, symbol: str, side: str, qty: float):
    q = f"{qty:.6f}".rstrip("0").rstrip(".")
    return session.place_order(
        category=category,
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=q,
        timeInForce="IOC",
        reduceOnly=False,
    )


def set_tp_sl(session: HTTP, category: str, symbol: str, side: str, tp: float, sl: float, tick: float):
    # Round safely
    tp_s = fmt_price(tp, tick, mode="down")
    sl_s = fmt_price(sl, tick, mode="up")
    session.set_trading_stop(
        category=category,
        symbol=symbol,
        takeProfit=tp_s,
        stopLoss=sl_s,
        tpTriggerBy="LastPrice",
        slTriggerBy="LastPrice",
    )


# ----------------------------
# Strategy (simple baseline)
# ----------------------------


def decide_side_15m(closes: list[float]) -> str:
    # Trend filter: EMA50 vs EMA200
    e50 = ema(closes, 50)
    e200 = ema(closes, 200)
    return "Buy" if e50[-1] > e200[-1] else "Sell"


# ----------------------------
# Bot
# ----------------------------

@dataclass
class Cfg:
    symbol: str
    interval: str
    analysis_interval_s: int
    leverage: int

    max_risk_pct: float
    max_position_pct: float

    stop_loss_pct: float
    take_profit_pct: float

    atr_len: int
    atr_sl_mult: float
    atr_tp_mult: float

    trailing_trigger_atr: float
    trailing_step_atr: float

    max_daily_loss_pct: float
    max_consecutive_losses: int
    daily_target_pct: float
    max_drawdown_pct: float


def load_cfg() -> Cfg:
    base_dir = os.path.dirname(__file__)
    load_env_file(os.path.join(base_dir, "config.env"))

    return Cfg(
        symbol=os.environ.get("SYMBOL", "BTCUSDT"),
        interval=os.environ.get("TIMEFRAME", "15"),
        analysis_interval_s=int(float(os.environ.get("ANALYSIS_INTERVAL_SECONDS", "60"))),
        leverage=int(float(os.environ.get("LEVERAGE", "20"))),

        max_risk_pct=float(os.environ.get("MAX_RISK_PCT", "1.0")),
        max_position_pct=float(os.environ.get("MAX_POSITION_PCT", "15")),

        stop_loss_pct=float(os.environ.get("STOP_LOSS_PCT", "1.5")),
        take_profit_pct=float(os.environ.get("TAKE_PROFIT_PCT", "2.5")),

        atr_len=14,
        atr_sl_mult=float(os.environ.get("ATR_SL_MULT", "1.6")),
        atr_tp_mult=float(os.environ.get("ATR_TP_MULT", "4.0")),

        trailing_trigger_atr=float(os.environ.get("TRAILING_STOP_ATR", "2.0")),
        trailing_step_atr=float(os.environ.get("TRAILING_STEP_ATR", "1.0")),

        max_daily_loss_pct=float(os.environ.get("MAX_DAILY_LOSS_PCT", "4.0")),
        max_consecutive_losses=int(float(os.environ.get("MAX_CONSECUTIVE_LOSSES", "2"))),
        daily_target_pct=float(os.environ.get("DAILY_TARGET_PCT", "1.2")),
        max_drawdown_pct=float(os.environ.get("MAX_DRAWDOWN_PCT", "15.0")),
    )


def main():
    cfg = load_cfg()
    session = make_session()

    base_dir = os.path.dirname(__file__)
    state_path = os.path.join(base_dir, "state_v3.json")
    log_path = os.path.join(base_dir, "trades_v3.log.jsonl")

    state = {
        "day": datetime.now(timezone.utc).date().isoformat(),
        "day_start_equity": None,
        "peak_equity": None,
        "consecutive_losses": 0,
        "last_candle_close_ms": 0,
        "entry_atr": None,
        "trail_level": 0,
    }
    if os.path.exists(state_path):
        try:
            state.update(json.loads(open(state_path, "r", encoding="utf-8").read()))
        except Exception:
            pass

    limits = get_limits(session, "linear", cfg.symbol)
    try:
        used_lev = set_leverage(session, "linear", cfg.symbol, cfg.leverage, limits.get("maxLeverage", 0))
    except Exception as e:
        # Not fatal; sometimes leverage is already set.
        used_lev = cfg.leverage
        print(f"[{now_iso()}] WARN set_leverage: {e}")

    print(f"[{now_iso()}] endpoint={session.endpoint} symbol={cfg.symbol} tf={cfg.interval} lev={used_lev}x")

    while True:
        try:
            now = datetime.now(timezone.utc)
            today = now.date().isoformat()

            equity = get_equity_usdt(session)

            if state.get("day") != today:
                state["day"] = today
                state["day_start_equity"] = equity
                state["peak_equity"] = equity
                state["consecutive_losses"] = 0

            if state.get("day_start_equity") is None:
                state["day_start_equity"] = equity
            if state.get("peak_equity") is None:
                state["peak_equity"] = equity

            state["peak_equity"] = max(float(state["peak_equity"]), equity)

            day_start = float(state["day_start_equity"])
            peak = float(state["peak_equity"])
            daily_pnl_pct = (equity - day_start) / day_start * 100.0 if day_start else 0.0
            dd_pct = (equity - peak) / peak * 100.0 if peak else 0.0

            # risk stops
            if daily_pnl_pct <= -cfg.max_daily_loss_pct:
                print(f"[{now_iso()}] PAUSE daily loss hit: {daily_pnl_pct:.2f}%")
                time.sleep(cfg.analysis_interval_s)
                continue
            if dd_pct <= -cfg.max_drawdown_pct:
                print(f"[{now_iso()}] PAUSE drawdown hit: {dd_pct:.2f}%")
                time.sleep(cfg.analysis_interval_s)
                continue
            if daily_pnl_pct >= cfg.daily_target_pct:
                print(f"[{now_iso()}] PAUSE daily target hit: {daily_pnl_pct:.2f}%")
                time.sleep(cfg.analysis_interval_s)
                continue
            if int(state.get("consecutive_losses", 0)) >= cfg.max_consecutive_losses:
                print(f"[{now_iso()}] PAUSE consecutive losses hit: {state.get('consecutive_losses')}")
                time.sleep(cfg.analysis_interval_s)
                continue

            pos = get_position(session, "linear", cfg.symbol)

            # trailing stop management
            if pos:
                side = pos.get("side")
                size = float(pos.get("size") or 0)
                avg = float(pos.get("avgPrice") or 0)
                upl = float(pos.get("unrealisedPnl") or 0)
                print(f"[{now_iso()}] HOLD {cfg.symbol} {side} size={size} avg={avg} uPnL={upl}")

                # trailing based on entry ATR
                entry_atr = state.get("entry_atr")
                if entry_atr:
                    entry_atr = float(entry_atr)
                    trail_level = int(state.get("trail_level", 0) or 0)

                    # get last price
                    t = session.get_tickers(category="linear", symbol=cfg.symbol)
                    last = float((t.get("result", {}) or {}).get("list", [{}])[0].get("lastPrice"))

                    if side == "Buy":
                        profit = last - avg
                    else:
                        profit = avg - last

                    profit_atr = profit / entry_atr if entry_atr > 0 else 0

                    # start trailing after trigger
                    if profit_atr >= cfg.trailing_trigger_atr:
                        # desired level: 1 ATR locked, then +1 ATR per step
                        desired_level = 1 + int((profit_atr - cfg.trailing_trigger_atr) // cfg.trailing_step_atr)
                        if desired_level > trail_level:
                            if side == "Buy":
                                new_sl = avg + desired_level * entry_atr
                            else:
                                new_sl = avg - desired_level * entry_atr

                            try:
                                set_tp_sl(session, "linear", cfg.symbol, side, tp=float(pos.get("takeProfit") or 0) or (avg + (entry_atr*cfg.atr_tp_mult) if side=="Buy" else avg - (entry_atr*cfg.atr_tp_mult)), sl=new_sl, tick=limits.get("tickSize", 0))
                                state["trail_level"] = desired_level
                                print(f"[{now_iso()}] TRAIL_SL level={desired_level} new_sl={new_sl}")
                            except Exception as e:
                                print(f"[{now_iso()}] WARN trail failed: {e}")

                with open(state_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(state, ensure_ascii=False, indent=2))

                time.sleep(cfg.analysis_interval_s)
                continue

            # flat: only act on new 15m candle close
            rows = get_klines(session, "linear", cfg.symbol, cfg.interval, limit=260)
            # row[0] is startTime ms
            last_close_ms = int(rows[-1][0])
            if last_close_ms == int(state.get("last_candle_close_ms", 0) or 0):
                time.sleep(cfg.analysis_interval_s)
                continue

            state["last_candle_close_ms"] = last_close_ms

            o, h, l, c = parse_ohlc(rows)
            a = atr(h, l, c, cfg.atr_len)
            atr_now = a[-1]

            side = decide_side_15m(c)

            # latest price
            t = session.get_tickers(category="linear", symbol=cfg.symbol)
            last = float((t.get("result", {}) or {}).get("list", [{}])[0].get("lastPrice"))

            # compute SL/TP distances
            if atr_now and atr_now > 0:
                sl_dist = cfg.atr_sl_mult * atr_now
                tp_dist = cfg.atr_tp_mult * atr_now
            else:
                sl_dist = last * (cfg.stop_loss_pct / 100.0)
                tp_dist = last * (cfg.take_profit_pct / 100.0)

            if side == "Buy":
                sl = last - sl_dist
                tp = last + tp_dist
            else:
                sl = last + sl_dist
                tp = last - tp_dist

            # risk sizing
            risk_usdt = equity * (cfg.max_risk_pct / 100.0)

            # position cap by margin usage
            max_margin = equity * (cfg.max_position_pct / 100.0)
            max_notional = max_margin * used_lev

            stop_dist = abs(last - sl)
            qty_by_risk = risk_usdt / stop_dist if stop_dist > 0 else 0
            qty_cap = max_notional / last if last > 0 else 0
            qty = min(qty_by_risk, qty_cap)

            # apply exchange filters
            step = limits.get("qtyStep", 0)
            max_mkt = limits.get("maxMktOrderQty", 0) or limits.get("maxOrderQty", 0)
            if max_mkt and qty > max_mkt:
                qty = max_mkt
            if step:
                qty = _round_down(qty, step)

            if qty <= 0:
                print(f"[{now_iso()}] SKIP qty<=0")
                time.sleep(cfg.analysis_interval_s)
                continue

            print(f"[{now_iso()}] ENTRY {cfg.symbol} side={side} last={last} qty={qty} SL={sl} TP={tp} atr={atr_now}")

            r_order = place_market(session, "linear", cfg.symbol, side, qty)
            try:
                set_tp_sl(session, "linear", cfg.symbol, side, tp, sl, limits.get("tickSize", 0))
            except Exception as e:
                print(f"[{now_iso()}] WARN set_tp_sl failed: {e}")

            # store entry atr for trailing
            state["entry_atr"] = atr_now
            state["trail_level"] = 0

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": now_iso(), "symbol": cfg.symbol, "side": side, "qty": qty, "entry": last, "sl": sl, "tp": tp, "atr": atr_now, "order": r_order}, ensure_ascii=False) + "\n")

            with open(state_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(state, ensure_ascii=False, indent=2))

            time.sleep(cfg.analysis_interval_s)

        except KeyboardInterrupt:
            print("\nStopped")
            return
        except Exception as e:
            print(f"[{now_iso()}] ERROR: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
