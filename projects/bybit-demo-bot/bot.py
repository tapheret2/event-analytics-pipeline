from __future__ import annotations

import os
import sys
import time
import math
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from pybit.unified_trading import HTTP

# Make Windows console output resilient
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ----------------------------
# Secrets / env helpers (Windows-friendly)
# ----------------------------

_LEAKED_KEY = "pTwlMemPdrEyWh5vbx"
_LEAKED_SECRET = "Pad5AQWaTEbXi49uiuTYjexkSizmP3LWbtaa"


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

    proc_val = os.environ.get(name)

    # If registry exists, trust it over process env (stale after setx).
    if reg_val:
        return reg_val

    if proc_val:
        return proc_val

    return None


# ----------------------------
# Config
# ----------------------------

@dataclass
class BotConfig:
    demo: bool = True
    testnet: bool = False

    category: str = "linear"  # USDT perpetual

    leverage: int = 50
    leverage_hard_cap: int = 25  # to avoid Bybit position limit errors on small-caps

    # risk model (demo): fraction of equity you're willing to lose *at stop* per trade
    risk_per_trade: float = 0.20  # 20%

    # extra cap so we don't hit exchange position limits / absurd sizes
    max_notional_per_trade: float = 200_000  # USDT

    # cadence
    cooldown_seconds: int = 0
    poll_seconds: int = 10

    # technicals
    ema_fast: int = 50
    ema_slow: int = 200
    rsi_len: int = 14
    atr_len: int = 14

    sl_atr_mult: float = 1.2
    tp_atr_mult: float = 1.8

    # fee-aware exits (taker fee observed ~0.055% on Bybit demo)
    taker_fee_rate: float = 0.00055
    fee_buffer_mult: float = 3.0  # TP distance >= roundtrip_fee * buffer

    # portfolio behavior
    max_open_positions: int = 5  # user-requested: 5 different coins at once (no scale-in)

    # universe selection
    meme_watchlist: tuple[str, ...] = (
        "DOGEUSDT",
        "1000PEPEUSDT",
        "WIFUSDT",
        "1000BONKUSDT",
        "1000FLOKIUSDT",
        "SHIB1000USDT",
        "BRETTUSDT",
        "1000000MOGUSDT",
        "POPCATUSDT",
        "1000TURBOUSDT",
        "1000000BABYDOGEUSDT",
    )

    exclude_symbols: tuple[str, ...] = (
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "BNBUSDT",
        "XRPUSDT",
    )
    # turnover thresholds
    min_turnover_watchlist: float = 1_000_000   # 1M USDT (for meme watchlist symbols)
    min_turnover_24h: float = 50_000_000        # 50M USDT (for non-watchlist symbols)

    max_symbols_considered: int = 80

    # anti-bug safety (not a PnL-based daily max loss)
    max_entries_per_hour: int = 60


# ----------------------------
# Helpers: indicators
# ----------------------------


def ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        raise ValueError("not enough values for EMA")
    k = 2 / (period + 1)
    out = []
    # seed with SMA
    sma = sum(values[:period]) / period
    out.append(sma)
    for v in values[period:]:
        out.append(out[-1] + k * (v - out[-1]))
    return [out[0]] * (period - 1) + out


def rsi(values: list[float], period: int) -> list[float]:
    if len(values) < period + 1:
        raise ValueError("not enough values for RSI")
    gains = []
    losses = []
    for i in range(1, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))

    # initial avg
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    out = [50.0] * (period)  # align to values length-1; we'll pad later
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else float("inf")
        val = 100 - (100 / (1 + rs))
        out.append(val)

    # pad to same length as values
    return [50.0] + out


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

    # Wilder smoothing
    out = []
    first = sum(trs[:period]) / period
    out.append(first)
    for tr in trs[period:]:
        out.append((out[-1] * (period - 1) + tr) / period)

    return [out[0]] * (period) + out  # align to closes length


def utc_ms() -> int:
    return int(time.time() * 1000)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------
# Bybit wrappers
# ----------------------------


def make_session() -> HTTP:
    api_key = get_env("BYBIT_API_KEY")
    api_secret = get_env("BYBIT_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("Missing BYBIT_API_KEY / BYBIT_API_SECRET (env or HKCU\\Environment)")

    # Refuse to run with a leaked key that was pasted in chat.
    if api_key == _LEAKED_KEY or api_secret == _LEAKED_SECRET:
        raise SystemExit("Refusing to run: current BYBIT_API_KEY/SECRET match a leaked key. Rotate the key and set it again.")

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

    # sanity check: demo endpoint should contain api-demo
    if demo and "api-demo" not in s.endpoint:
        raise SystemExit(f"Refusing to run: demo=true but endpoint is {s.endpoint}")

    return s


def get_equity_usdt(session: HTTP) -> float:
    # unified account balance
    resp = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
    item = (resp.get("result", {}) or {}).get("list", [])
    if not item:
        raise RuntimeError("No wallet balance returned")
    coins = (item[0] or {}).get("coin", [])
    usdt = next((c for c in coins if c.get("coin") == "USDT"), None)
    if not usdt:
        raise RuntimeError("USDT balance not found")
    # prioritize totalEquity
    for k in ("totalEquity", "equity", "walletBalance"):
        v = usdt.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    raise RuntimeError("Could not parse equity")


def list_candidate_symbols(session: HTTP, cfg: BotConfig) -> list[dict[str, Any]]:
    resp = session.get_tickers(category=cfg.category)
    tickers = (resp.get("result", {}) or {}).get("list", [])

    out = []
    for t in tickers:
        sym = t.get("symbol")
        if not sym or not sym.endswith("USDT"):
            continue
        if sym in cfg.exclude_symbols:
            continue
        # filter on turnover
        try:
            turnover = float(t.get("turnover24h", 0) or 0)
        except Exception:
            turnover = 0
        if turnover < cfg.min_turnover_24h:
            continue
        # filter on lastPrice
        try:
            last = float(t.get("lastPrice", 0) or 0)
        except Exception:
            last = 0
        if last <= 0:
            continue
        out.append({
            "symbol": sym,
            "turnover24h": turnover,
            "lastPrice": last,
            "price24hPcnt": float(t.get("price24hPcnt", 0) or 0),
        })

    # sort by abs daily move, then turnover
    out.sort(key=lambda x: (abs(x["price24hPcnt"]), x["turnover24h"]), reverse=True)
    return out[: cfg.max_symbols_considered]


def choose_symbol(session: HTTP, cfg: BotConfig, *, exclude: set[str]) -> str | None:
    """Pick a symbol not in `exclude`.

    Prefer meme watchlist if available & liquid; fallback to high-volatility liquid symbols.
    """

    # Build a quick lookup from tickers
    resp = session.get_tickers(category=cfg.category)
    tickers = (resp.get("result", {}) or {}).get("list", [])
    by_sym = {t.get("symbol"): t for t in tickers if t.get("symbol")}

    def ok(sym: str) -> bool:
        if sym in exclude:
            return False
        if sym in cfg.exclude_symbols:
            return False
        t = by_sym.get(sym)
        if not t:
            return False
        try:
            turnover = float(t.get("turnover24h", 0) or 0)
            last = float(t.get("lastPrice", 0) or 0)
        except Exception:
            return False

        if last <= 0:
            return False

        # For meme watchlist, allow much lower turnover.
        thresh = cfg.min_turnover_watchlist if sym in cfg.meme_watchlist else cfg.min_turnover_24h
        return turnover >= thresh

    # 1) Prefer watchlist
    watch = [s for s in cfg.meme_watchlist if ok(s)]
    if watch:
        return random.choice(watch)

    # If watchlist has no eligible symbols, stop (user explicitly wants meme coins, not random small-caps).
    return None


def get_klines(session: HTTP, category: str, symbol: str, interval: str, limit: int = 300) -> list[dict[str, Any]]:
    resp = session.get_kline(category=category, symbol=symbol, interval=interval, limit=limit)
    rows = (resp.get("result", {}) or {}).get("list", [])
    # bybit returns newest first; reverse
    rows = list(reversed(rows))
    return rows


def parse_ohlc(rows: list[dict[str, Any]]):
    ts = []
    o = []
    h = []
    l = []
    c = []
    for r in rows:
        # r: [startTime, open, high, low, close, volume, turnover]
        start = int(r[0])
        ts.append(start)
        o.append(float(r[1]))
        h.append(float(r[2]))
        l.append(float(r[3]))
        c.append(float(r[4]))
    return ts, o, h, l, c


def get_position(session: HTTP, cfg: BotConfig, symbol: str) -> Optional[dict[str, Any]]:
    resp = session.get_positions(category=cfg.category, symbol=symbol)
    rows = (resp.get("result", {}) or {}).get("list", [])
    if not rows:
        return None
    pos = rows[0]
    try:
        size = float(pos.get("size", 0) or 0)
    except Exception:
        size = 0
    if size == 0:
        return None
    return pos


def get_max_leverage(session: HTTP, cfg: BotConfig, symbol: str) -> float | None:
    try:
        resp = session.get_instruments_info(category=cfg.category, symbol=symbol)
        lst = (resp.get("result", {}) or {}).get("list", [])
        if not lst:
            return None
        levf = (lst[0] or {}).get("leverageFilter", {}) or {}
        ml = levf.get("maxLeverage")
        return float(ml) if ml is not None else None
    except Exception:
        return None


def set_leverage(session: HTTP, cfg: BotConfig, symbol: str) -> int | None:
    max_lev = get_max_leverage(session, cfg, symbol)
    target = cfg.leverage
    if max_lev:
        target = min(target, int(float(max_lev)))
    # hard cap to avoid small-cap risk limit errors
    target = min(target, int(cfg.leverage_hard_cap))
    if target < 1:
        target = 1

    lev = str(target)
    session.set_leverage(category=cfg.category, symbol=symbol, buyLeverage=lev, sellLeverage=lev)
    return target


def place_market(
    session: HTTP,
    cfg: BotConfig,
    symbol: str,
    side: str,
    qty: float,
    *,
    reduce_only: bool = False,
) -> dict[str, Any]:
    q = f"{qty:.6f}".rstrip("0").rstrip(".")
    return session.place_order(
        category=cfg.category,
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=q,
        timeInForce="IOC",
        reduceOnly=reduce_only,
    )


def get_tick_size(session: HTTP, cfg: BotConfig, symbol: str) -> float | None:
    try:
        resp = session.get_instruments_info(category=cfg.category, symbol=symbol)
        lst = (resp.get("result", {}) or {}).get("list", [])
        if not lst:
            return None
        pf = (lst[0] or {}).get("priceFilter", {}) or {}
        ts = pf.get("tickSize")
        return float(ts) if ts is not None else None
    except Exception:
        return None


def _round_up(x: float, step: float) -> float:
    if step <= 0:
        return x
    return math.ceil(x / step) * step


def fmt_price(x: float, tick: float, *, mode: str) -> str:
    """Format price to tick size.

    mode:
      - 'down' => floor to tick
      - 'up'   => ceil to tick
    """
    if tick and tick > 0:
        x = _round_down(x, tick) if mode == "down" else _round_up(x, tick)

    # avoid scientific notation
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s


def set_tp_sl(session: HTTP, cfg: BotConfig, symbol: str, side: str, take_profit: float, stop_loss: float):
    tick = get_tick_size(session, cfg, symbol) or 0.0

    # Safer rounding:
    # - For TP on both sides: round down (avoid accidentally crossing entry due to rounding)
    # - For SL: round up
    tp_s = fmt_price(take_profit, tick, mode="down")
    sl_s = fmt_price(stop_loss, tick, mode="up")

    session.set_trading_stop(
        category=cfg.category,
        symbol=symbol,
        takeProfit=tp_s,
        stopLoss=sl_s,
        tpTriggerBy="LastPrice",
        slTriggerBy="LastPrice",
    )


# ----------------------------
# Strategy
# ----------------------------


def decide_bias(session: HTTP, cfg: BotConfig, symbol: str) -> str:
    rows_15m = get_klines(session, cfg.category, symbol, interval="15", limit=max(cfg.ema_slow + 50, 260))
    _, _, _, _, closes = parse_ohlc(rows_15m)
    e_fast = ema(closes, cfg.ema_fast)
    e_slow = ema(closes, cfg.ema_slow)

    if e_fast[-1] > e_slow[-1]:
        return "LONG"
    else:
        return "SHORT"


def entry_signal(session: HTTP, cfg: BotConfig, symbol: str, bias: str, *, first_trade: bool) -> bool:
    """Entry trigger (demo aggressive mode).

    With cooldown=0 and no 15m guard, we enter whenever flat and allowed by max_entries_per_hour.
    """

    return True


def compute_tp_sl(session: HTTP, cfg: BotConfig, symbol: str, side: str, entry: float) -> tuple[float, float]:
    """Compute fee-aware TP/SL.

    Fee-aware rule (based on observed taker fee):
    - Ensure TP distance >= roundtrip_fee * buffer.

    roundtrip_fee_pct ≈ 2 * taker_fee_rate
    min_tp_pct = roundtrip_fee_pct * fee_buffer_mult

    This prevents tiny TP that can't cover fees.
    """

    rows_1m = get_klines(session, cfg.category, symbol, interval="1", limit=200)
    _, _, highs, lows, closes = parse_ohlc(rows_1m)
    a = atr(highs, lows, closes, cfg.atr_len)
    atr_now = a[-1]

    sl_dist = cfg.sl_atr_mult * atr_now
    tp_dist = cfg.tp_atr_mult * atr_now

    # fee-aware minimum TP distance
    min_tp_pct = (2.0 * cfg.taker_fee_rate) * cfg.fee_buffer_mult
    min_tp_dist = entry * min_tp_pct
    tp_dist = max(tp_dist, min_tp_dist)

    if side == "Buy":
        sl = entry - sl_dist
        tp = entry + tp_dist
    else:
        sl = entry + sl_dist
        tp = entry - tp_dist

    return tp, max(sl, 0.0000001)


def _round_down(x: float, step: float) -> float:
    if step <= 0:
        return x
    return math.floor(x / step) * step


def get_lot_limits(session: HTTP, cfg: BotConfig, symbol: str) -> dict[str, float] | None:
    """Fetch lot size limits for symbol (min/max/step + min notional)."""
    try:
        resp = session.get_instruments_info(category=cfg.category, symbol=symbol)
        lst = (resp.get("result", {}) or {}).get("list", [])
        if not lst:
            return None
        lot = (lst[0] or {}).get("lotSizeFilter", {}) or {}
        return {
            "minOrderQty": float(lot.get("minOrderQty", 0) or 0),
            "maxOrderQty": float(lot.get("maxOrderQty", 0) or 0),
            "maxMktOrderQty": float(lot.get("maxMktOrderQty", 0) or 0),
            "qtyStep": float(lot.get("qtyStep", 0) or 0),
            "minNotionalValue": float(lot.get("minNotionalValue", 0) or 0),
        }
    except Exception:
        return None


def compute_qty(
    equity: float,
    risk_usdt: float,
    entry: float,
    stop_loss: float,
    cfg: BotConfig,
    lot: dict[str, float] | None,
    order_type: str = "Market",
) -> float:
    stop_dist = abs(entry - stop_loss)
    if stop_dist <= 0:
        return 0.0

    qty_by_risk = risk_usdt / stop_dist
    max_notional = min(equity * cfg.leverage * 0.9, cfg.max_notional_per_trade)
    qty_cap = max_notional / entry

    qty = min(qty_by_risk, qty_cap)

    # Apply exchange limits
    if lot:
        step = lot.get("qtyStep", 0.0) or 0.0
        min_qty = lot.get("minOrderQty", 0.0) or 0.0
        max_qty = lot.get("maxOrderQty", 0.0) or 0.0
        max_mkt = lot.get("maxMktOrderQty", 0.0) or 0.0
        min_notional = lot.get("minNotionalValue", 0.0) or 0.0

        # cap market order
        if order_type.lower() == "market" and max_mkt > 0:
            qty = min(qty, max_mkt)
        elif max_qty > 0:
            qty = min(qty, max_qty)

        if step > 0:
            qty = _round_down(qty, step)

        # ensure meets min notional
        if min_notional > 0 and entry > 0:
            min_qty_by_notional = min_notional / entry
            if step > 0:
                # round up to step
                min_qty_by_notional = math.ceil(min_qty_by_notional / step) * step
            qty = max(qty, min_qty_by_notional)

        if min_qty > 0:
            qty = max(qty, min_qty)

    return max(qty, 0.0)


# ----------------------------
# Main loop
# ----------------------------


def main():
    cfg = BotConfig(
        demo=(get_env("BYBIT_DEMO") or "true").lower() in ("1", "true", "yes", "y"),
        testnet=(get_env("BYBIT_TESTNET") or "false").lower() in ("1", "true", "yes", "y"),
    )
    session = make_session()

    print(f"[{now_iso()}] Bybit endpoint: {session.endpoint}")
    print(
        f"[{now_iso()}] DEMO={cfg.demo} TESTNET={cfg.testnet} leverage={cfg.leverage} "
        f"risk_per_trade={cfg.risk_per_trade} max_open_positions={cfg.max_open_positions} "
        f"fee_min_tp_pct={(2*cfg.taker_fee_rate*cfg.fee_buffer_mult):.4%}"
    )

    base_dir = os.path.dirname(__file__)
    state_path = os.path.join(base_dir, "state.json")
    log_path = os.path.join(base_dir, "trades.log.jsonl")

    state = {
        "active_symbols": [],
        "entries_last_hour": [],
        "last_status_ms": 0,
    }
    if os.path.exists(state_path):
        try:
            state = json.loads(open(state_path, "r", encoding="utf-8").read())
        except Exception:
            pass

    def save_state():
        with open(state_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(state, ensure_ascii=False, indent=2))

    # bootstrap active symbols: keep only meme watchlist symbols (user wants 5 different meme coins)
    active: list[str] = list(state.get("active_symbols") or [])
    active = [s for s in active if isinstance(s, str) and s]
    active = [s for s in active if s in cfg.meme_watchlist]
    state["active_symbols"] = active
    save_state()

    while True:
        try:
            now_ms = utc_ms()
            # cleanup entry timestamps
            state["entries_last_hour"] = [t for t in state.get("entries_last_hour", []) if now_ms - t < 3600_000]

            equity = get_equity_usdt(session)

            # Ensure we have up to N symbols to work with
            while len(state["active_symbols"]) < cfg.max_open_positions:
                sym = choose_symbol(session, cfg, exclude=set(state["active_symbols"]))
                if not sym:
                    break
                state["active_symbols"].append(sym)
                save_state()

            active = list(state["active_symbols"])

            # Gather positions
            open_positions: dict[str, dict[str, Any]] = {}
            for sym in active:
                pos = get_position(session, cfg, sym)
                if pos:
                    open_positions[sym] = pos

            # Status
            if now_ms - int(state.get("last_status_ms", 0) or 0) > 30_000:
                state["last_status_ms"] = now_ms
                print(
                    f"[{now_iso()}] STATUS equity={equity:.2f} open={len(open_positions)}/{cfg.max_open_positions} "
                    f"syms={','.join(active)}"
                )
                save_state()

            # If too many active symbols and some have no positions, trim extras
            # (keep symbols with open positions)
            if len(state["active_symbols"]) > cfg.max_open_positions:
                keep = list(open_positions.keys())
                state["active_symbols"] = keep[: cfg.max_open_positions]
                save_state()

            # anti-bug throttle
            if len(state["entries_last_hour"]) >= cfg.max_entries_per_hour:
                print(f"[{now_iso()}] THROTTLE: max entries/hour reached")
                time.sleep(15)
                continue

            # Open new positions until we reach max_open_positions
            slots = cfg.max_open_positions - len(open_positions)
            if slots <= 0:
                # print holds
                for sym, pos in open_positions.items():
                    try:
                        side = pos.get("side")
                        size = pos.get("size")
                        avg = pos.get("avgPrice")
                        upl = pos.get("unrealisedPnl")
                        print(f"[{now_iso()}] HOLD {sym} {side} size={size} avg={avg} uPnL={upl}")
                    except Exception:
                        pass
                time.sleep(cfg.poll_seconds)
                continue

            # Risk allocation: spread total risk across N slots
            risk_usdt_per_pos = equity * cfg.risk_per_trade / cfg.max_open_positions

            # Try to enter on any symbol without an open position
            for sym in active:
                if sym in open_positions:
                    continue
                if slots <= 0:
                    break

                # anti-bug throttle
                if len(state["entries_last_hour"]) >= cfg.max_entries_per_hour:
                    break

                bias = decide_bias(session, cfg, sym)
                side = "Buy" if bias == "LONG" else "Sell"

                # Best-effort leverage set per symbol
                try:
                    used = set_leverage(session, cfg, sym)
                    if used:
                        print(f"[{now_iso()}] {sym} leverage={used}x (req {cfg.leverage}x)")
                except Exception as e:
                    print(f"[{now_iso()}] WARN: set_leverage failed for {sym}: {e}")

                # Price
                t = session.get_tickers(category=cfg.category, symbol=sym)
                last = float(((t.get("result", {}) or {}).get("list", [{}])[0] or {}).get("lastPrice"))

                tp, sl = compute_tp_sl(session, cfg, sym, side, last)
                lot = get_lot_limits(session, cfg, sym)
                qty = compute_qty(
                    equity=equity,
                    risk_usdt=risk_usdt_per_pos,
                    entry=last,
                    stop_loss=sl,
                    cfg=cfg,
                    lot=lot,
                    order_type="Market",
                )
                if qty <= 0:
                    print(f"[{now_iso()}] SKIP {sym}: qty <= 0")
                    continue

                print(
                    f"[{now_iso()}] ENTRY {sym} bias={bias} side={side} last={last:.6f} "
                    f"qty={qty:.6f} SL={sl:.6f} TP={tp:.6f}"
                )

                try:
                    r_order = place_market(session, cfg, sym, side, qty)
                except Exception as e:
                    print(f"[{now_iso()}] ORDER_FAILED {sym}: {e}")
                    continue

                try:
                    set_tp_sl(session, cfg, sym, side, take_profit=tp, stop_loss=sl)
                except Exception as e:
                    print(f"[{now_iso()}] WARN: set_tp_sl failed for {sym}: {e}")

                state["entries_last_hour"].append(now_ms)
                save_state()

                log_rec = {
                    "ts": now_iso(),
                    "symbol": sym,
                    "bias": bias,
                    "side": side,
                    "entry_ref": last,
                    "qty": qty,
                    "sl": sl,
                    "tp": tp,
                    "equity": equity,
                    "order_resp": r_order,
                }
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_rec, ensure_ascii=False) + "\n")

                # refresh open positions count
                slots -= 1

            time.sleep(cfg.poll_seconds)

        except KeyboardInterrupt:
            print("\nStopped.")
            return
        except Exception as e:
            print(f"[{now_iso()}] ERROR: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
