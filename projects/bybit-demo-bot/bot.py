from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pybit.unified_trading import HTTP

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ----------------------------
# Env helpers
# ----------------------------


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def env_bool(name: str, default: bool) -> bool:
    value = (get_env(name) or "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(str(get_env(name, str(default))).strip())
    except Exception:
        return default


def env_float(name: str, default: float) -> float:
    try:
        raw = str(get_env(name, str(default))).split("#", 1)[0].strip()
        return float(raw)
    except Exception:
        return default


# ----------------------------
# Config
# ----------------------------


@dataclass
class BotConfig:
    demo: bool = True
    testnet: bool = False
    category: str = "linear"
    symbol: str = "BTCUSDT"
    timeframe: str = "15"
    analysis_interval_seconds: int = 60
    leverage: int = 20

    max_risk_pct: float = 1.0
    max_position_pct: float = 15.0
    stop_loss_pct: float = 1.5
    take_profit_pct: float = 2.5
    atr_sl_mult: float = 1.6
    atr_tp_mult: float = 4.0
    trailing_stop_atr: float = 2.0
    trailing_step_atr: float = 1.0
    min_trail_update_ticks: int = 5
    max_daily_loss_pct: float = 4.0
    max_consecutive_losses: int = 2
    daily_target_pct: float = 1.2
    max_drawdown_pct: float = 15.0
    max_trades_per_day: int = 6
    min_entry_interval_seconds: int = 900
    loss_cooldown_seconds: int = 3600

    ema_fast: int = 20
    ema_slow: int = 50
    rsi_len: int = 14
    atr_len: int = 14
    adx_len: int = 14
    min_adx: float = 22.0
    min_ema_gap_pct: float = 0.08
    rsi_long_floor: float = 52.0
    rsi_long_ceiling: float = 72.0
    rsi_short_floor: float = 28.0
    rsi_short_ceiling: float = 48.0

    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000


def load_config() -> BotConfig:
    timeframe_raw = (get_env("TIMEFRAME", "15m") or "15m").strip().lower()
    if timeframe_raw.endswith("m"):
        timeframe = timeframe_raw[:-1]
    else:
        timeframe = timeframe_raw

    return BotConfig(
        demo=env_bool("BYBIT_DEMO", True),
        testnet=env_bool("BYBIT_TESTNET", False),
        symbol=(get_env("SYMBOL", "BTCUSDT") or "BTCUSDT").strip().upper(),
        timeframe=timeframe,
        analysis_interval_seconds=env_int("ANALYSIS_INTERVAL_SECONDS", 60),
        leverage=env_int("LEVERAGE", 20),
        max_risk_pct=env_float("MAX_RISK_PCT", 1.0),
        max_position_pct=env_float("MAX_POSITION_PCT", 15.0),
        stop_loss_pct=env_float("STOP_LOSS_PCT", 1.5),
        take_profit_pct=env_float("TAKE_PROFIT_PCT", 2.5),
        atr_sl_mult=env_float("ATR_SL_MULT", 1.6),
        atr_tp_mult=env_float("ATR_TP_MULT", 4.0),
        trailing_stop_atr=env_float("TRAILING_STOP_ATR", 2.0),
        trailing_step_atr=env_float("TRAILING_STEP_ATR", 1.0),
        min_trail_update_ticks=env_int("MIN_TRAIL_UPDATE_TICKS", 5),
        max_daily_loss_pct=env_float("MAX_DAILY_LOSS_PCT", 4.0),
        max_consecutive_losses=env_int("MAX_CONSECUTIVE_LOSSES", 2),
        daily_target_pct=env_float("DAILY_TARGET_PCT", 1.2),
        max_drawdown_pct=env_float("MAX_DRAWDOWN_PCT", 15.0),
        max_trades_per_day=env_int("MAX_TRADES_PER_DAY", 6),
        min_entry_interval_seconds=env_int("MIN_ENTRY_INTERVAL_SECONDS", 900),
        loss_cooldown_seconds=env_int("LOSS_COOLDOWN_SECONDS", 3600),
        min_adx=env_float("MIN_ADX", 22.0),
        min_ema_gap_pct=env_float("MIN_EMA_GAP_PCT", 0.08),
        rsi_long_floor=env_float("RSI_LONG_FLOOR", 52.0),
        rsi_long_ceiling=env_float("RSI_LONG_CEILING", 72.0),
        rsi_short_floor=env_float("RSI_SHORT_FLOOR", 28.0),
        rsi_short_ceiling=env_float("RSI_SHORT_CEILING", 48.0),
        dashboard_host=get_env("DASHBOARD_HOST", "0.0.0.0") or "0.0.0.0",
        dashboard_port=env_int("DASHBOARD_PORT", 8000),
    )


# ----------------------------
# Indicators
# ----------------------------


def ema(values: list[float], period: int) -> list[float]:
    if len(values) < period:
        raise ValueError("not enough values for EMA")
    k = 2 / (period + 1)
    seed = sum(values[:period]) / period
    out = [seed]
    for v in values[period:]:
        out.append(out[-1] + k * (v - out[-1]))
    return [out[0]] * (period - 1) + out


def rsi(values: list[float], period: int) -> list[float]:
    if len(values) < period + 1:
        raise ValueError("not enough values for RSI")
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out = [50.0] * period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else float("inf")
        out.append(100 - (100 / (1 + rs)))
    return [50.0] + out


def atr(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float]:
    if len(closes) < period + 1:
        raise ValueError("not enough values for ATR")
    trs: list[float] = []
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
    return [out[0]] * period + out


def adx(highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float]:
    if len(closes) < period * 2:
        raise ValueError("not enough values for ADX")

    tr_list: list[float] = []
    plus_dm_list: list[float] = []
    minus_dm_list: list[float] = []

    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm = up if up > down and up > 0 else 0.0
        minus_dm = down if down > up and down > 0 else 0.0
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

    tr_smooth = sum(tr_list[:period])
    plus_dm_smooth = sum(plus_dm_list[:period])
    minus_dm_smooth = sum(minus_dm_list[:period])

    dx_vals: list[float] = []
    for i in range(period, len(tr_list)):
        if i > period:
            tr_smooth = tr_smooth - (tr_smooth / period) + tr_list[i]
            plus_dm_smooth = plus_dm_smooth - (plus_dm_smooth / period) + plus_dm_list[i]
            minus_dm_smooth = minus_dm_smooth - (minus_dm_smooth / period) + minus_dm_list[i]

        plus_di = 100 * (plus_dm_smooth / tr_smooth) if tr_smooth else 0.0
        minus_di = 100 * (minus_dm_smooth / tr_smooth) if tr_smooth else 0.0
        denom = plus_di + minus_di
        dx = 100 * abs(plus_di - minus_di) / denom if denom else 0.0
        dx_vals.append(dx)

    if len(dx_vals) < period:
        raise ValueError("not enough DX values for ADX")

    adx_seed = sum(dx_vals[:period]) / period
    out = [adx_seed]
    for dxv in dx_vals[period:]:
        out.append(((out[-1] * (period - 1)) + dxv) / period)

    pad = len(closes) - len(out)
    return [out[0]] * pad + out


# ----------------------------
# Utils
# ----------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def utc_ts() -> int:
    return int(time.time())


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def round_down(x: float, step: float) -> float:
    if step <= 0:
        return x
    return math.floor(x / step) * step


def round_up(x: float, step: float) -> float:
    if step <= 0:
        return x
    return math.ceil(x / step) * step


def fmt_price(x: float, tick: float, mode: str) -> str:
    value = round_down(x, tick) if mode == "down" else round_up(x, tick)
    return f"{value:.10f}".rstrip("0").rstrip(".")


# ----------------------------
# Bybit wrappers
# ----------------------------


def make_session() -> HTTP:
    api_key = get_env("BYBIT_API_KEY")
    api_secret = get_env("BYBIT_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit("Missing BYBIT_API_KEY / BYBIT_API_SECRET")

    cfg = load_config()
    session = HTTP(
        api_key=api_key,
        api_secret=api_secret,
        demo=cfg.demo,
        testnet=cfg.testnet,
        recv_window=10000,
        timeout=20,
    )
    return session


def get_wallet_snapshot(session: HTTP) -> dict[str, float]:
    resp = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
    rows = (resp.get("result", {}) or {}).get("list", [])
    if not rows:
        raise RuntimeError("No wallet balance returned")
    coins = (rows[0] or {}).get("coin", [])
    usdt = next((c for c in coins if c.get("coin") == "USDT"), None)
    if not usdt:
        raise RuntimeError("USDT balance not found")
    return {
        "equity": safe_float(usdt.get("equity") or usdt.get("walletBalance") or 0),
        "wallet_balance": safe_float(usdt.get("walletBalance") or 0),
        "available": safe_float(usdt.get("availableToWithdraw") or usdt.get("availableBalance") or 0),
    }


def get_ticker(session: HTTP, category: str, symbol: str) -> dict[str, Any]:
    resp = session.get_tickers(category=category, symbol=symbol)
    lst = (resp.get("result", {}) or {}).get("list", [])
    if not lst:
        raise RuntimeError(f"Ticker not found for {symbol}")
    return lst[0]


def get_position(session: HTTP, category: str, symbol: str) -> dict[str, Any] | None:
    resp = session.get_positions(category=category, symbol=symbol)
    rows = (resp.get("result", {}) or {}).get("list", [])
    if not rows:
        return None
    for pos in rows:
        if safe_float(pos.get("size")) > 0:
            return pos
    return None


def get_klines(session: HTTP, category: str, symbol: str, interval: str, limit: int = 300) -> list[list[str]]:
    resp = session.get_kline(category=category, symbol=symbol, interval=interval, limit=limit)
    rows = (resp.get("result", {}) or {}).get("list", [])
    return list(reversed(rows))


def parse_ohlc(rows: list[list[str]]) -> tuple[list[float], list[float], list[float], list[float]]:
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    volumes: list[float] = []
    for r in rows:
        highs.append(float(r[2]))
        lows.append(float(r[3]))
        closes.append(float(r[4]))
        volumes.append(float(r[5]))
    return highs, lows, closes, volumes


def get_instrument_filters(session: HTTP, category: str, symbol: str) -> dict[str, float]:
    resp = session.get_instruments_info(category=category, symbol=symbol)
    rows = (resp.get("result", {}) or {}).get("list", [])
    if not rows:
        raise RuntimeError(f"Instrument not found for {symbol}")
    row = rows[0]
    lot = (row.get("lotSizeFilter") or {})
    price = (row.get("priceFilter") or {})
    lev = (row.get("leverageFilter") or {})
    return {
        "min_qty": safe_float(lot.get("minOrderQty")),
        "qty_step": safe_float(lot.get("qtyStep")),
        "max_mkt_qty": safe_float(lot.get("maxMktOrderQty")),
        "max_qty": safe_float(lot.get("maxOrderQty")),
        "min_notional": safe_float(lot.get("minNotionalValue")),
        "tick_size": safe_float(price.get("tickSize")),
        "max_leverage": safe_float(lev.get("maxLeverage"), 1.0),
    }


def set_leverage(session: HTTP, cfg: BotConfig, symbol: str, max_leverage: float) -> int:
    lev = max(1, min(cfg.leverage, int(max_leverage) if max_leverage else cfg.leverage))
    session.set_leverage(category=cfg.category, symbol=symbol, buyLeverage=str(lev), sellLeverage=str(lev))
    return lev


def place_market_order(session: HTTP, cfg: BotConfig, symbol: str, side: str, qty: float, reduce_only: bool = False) -> dict[str, Any]:
    q = f"{qty:.8f}".rstrip("0").rstrip(".")
    return session.place_order(
        category=cfg.category,
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=q,
        reduceOnly=reduce_only,
        timeInForce="IOC",
    )


def set_trading_stop(session: HTTP, cfg: BotConfig, symbol: str, take_profit: float, stop_loss: float, *, tick_size: float):
    session.set_trading_stop(
        category=cfg.category,
        symbol=symbol,
        takeProfit=fmt_price(take_profit, tick_size, "down"),
        stopLoss=fmt_price(stop_loss, tick_size, "up"),
        tpTriggerBy="LastPrice",
        slTriggerBy="LastPrice",
    )


# ----------------------------
# Strategy + risk
# ----------------------------


def build_signal(
    cfg: BotConfig,
    highs: list[float],
    lows: list[float],
    closes: list[float],
    *,
    signal_idx: int = -2,
) -> dict[str, Any]:
    ema_fast = ema(closes, cfg.ema_fast)
    ema_slow = ema(closes, cfg.ema_slow)
    rsi_vals = rsi(closes, cfg.rsi_len)
    atr_vals = atr(highs, lows, closes, cfg.atr_len)
    adx_vals = adx(highs, lows, closes, cfg.adx_len)

    idx = signal_idx if abs(signal_idx) <= len(closes) else -1
    last = closes[idx]
    fast = ema_fast[idx]
    slow = ema_slow[idx]
    r = rsi_vals[idx]
    a = atr_vals[idx]
    adx_now = adx_vals[idx]
    ema_gap_pct = (abs(fast - slow) / last * 100.0) if last > 0 else 0.0

    long_ok = (
        fast > slow
        and r >= cfg.rsi_long_floor
        and r <= cfg.rsi_long_ceiling
        and adx_now >= cfg.min_adx
        and ema_gap_pct >= cfg.min_ema_gap_pct
    )
    short_ok = (
        fast < slow
        and r <= cfg.rsi_short_ceiling
        and r >= cfg.rsi_short_floor
        and adx_now >= cfg.min_adx
        and ema_gap_pct >= cfg.min_ema_gap_pct
    )

    if long_ok and not short_ok:
        side = "Buy"
    elif short_ok and not long_ok:
        side = "Sell"
    else:
        side = "NONE"

    return {
        "side": side,
        "price": last,
        "ema_fast": fast,
        "ema_slow": slow,
        "rsi": r,
        "atr": a,
        "adx": adx_now,
        "ema_gap_pct": ema_gap_pct,
    }


def compute_exit_prices(cfg: BotConfig, side: str, entry_price: float, atr_now: float) -> tuple[float, float]:
    sl_dist = atr_now * cfg.atr_sl_mult if atr_now > 0 else entry_price * (cfg.stop_loss_pct / 100.0)
    tp_dist = atr_now * cfg.atr_tp_mult if atr_now > 0 else entry_price * (cfg.take_profit_pct / 100.0)

    if side == "Buy":
        stop_loss = entry_price - sl_dist
        take_profit = entry_price + tp_dist
    else:
        stop_loss = entry_price + sl_dist
        take_profit = entry_price - tp_dist

    return take_profit, max(stop_loss, 0.0000001)


def compute_qty(cfg: BotConfig, equity: float, entry: float, stop_loss: float, leverage: int, filters: dict[str, float]) -> float:
    risk_usdt = equity * (cfg.max_risk_pct / 100.0)
    stop_dist = abs(entry - stop_loss)
    if stop_dist <= 0:
        return 0.0

    qty_by_risk = risk_usdt / stop_dist

    max_margin = equity * (cfg.max_position_pct / 100.0)
    max_notional = max_margin * leverage
    qty_by_cap = max_notional / entry if entry > 0 else 0.0

    qty = min(qty_by_risk, qty_by_cap)

    step = filters.get("qty_step", 0.0)
    if step > 0:
        qty = round_down(qty, step)

    min_qty = filters.get("min_qty", 0.0)
    min_notional = filters.get("min_notional", 0.0)
    if min_notional > 0 and entry > 0:
        qty = max(qty, round_up(min_notional / entry, step or 0.0))
    if min_qty > 0:
        qty = max(qty, min_qty)

    max_qty = filters.get("max_mkt_qty") or filters.get("max_qty") or 0.0
    if max_qty > 0:
        qty = min(qty, max_qty)

    return max(qty, 0.0)


def pnl_pct_from_equity(start_equity: float, equity: float) -> float:
    if start_equity <= 0:
        return 0.0
    return ((equity - start_equity) / start_equity) * 100.0


# ----------------------------
# State
# ----------------------------


BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "state_v2.json"
TRADE_LOG_PATH = BASE_DIR / "trades_v2.log.jsonl"
RUNTIME_LOG_PATH = BASE_DIR / "bot_v2_runtime.log"


DEFAULT_STATE: dict[str, Any] = {
    "day": "",
    "start_equity": 0.0,
    "peak_equity": 0.0,
    "daily_realized_pnl": 0.0,
    "daily_trade_count": 0,
    "consecutive_losses": 0,
    "paused": False,
    "pause_reason": "",
    "last_signal": None,
    "last_loop_ts": 0,
    "last_entry_ts": 0,
    "last_entry_candle_ts": 0,
    "cooldown_until_ts": 0,
    "open_trade": None,
    "trade_seq": 0,
}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return dict(DEFAULT_STATE)
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_STATE)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_STATE)


def save_state(state: dict[str, Any]):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def log_runtime(message: str):
    line = f"[{now_iso()}] {message}"
    print(line)
    with RUNTIME_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_trade(event: dict[str, Any]):
    with TRADE_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def reset_day_if_needed(state: dict[str, Any], equity: float):
    today = utc_day()
    if state.get("day") != today:
        state["day"] = today
        state["start_equity"] = equity
        state["peak_equity"] = equity
        state["daily_realized_pnl"] = 0.0
        state["daily_trade_count"] = 0
        state["consecutive_losses"] = 0
        state["paused"] = False
        state["pause_reason"] = ""


# ----------------------------
# Trade lifecycle helpers
# ----------------------------


def sync_open_trade_from_exchange(state: dict[str, Any], position: dict[str, Any] | None):
    open_trade = state.get("open_trade")
    if position and not open_trade:
        state["open_trade"] = {
            "trade_id": f"restored-{utc_ts()}",
            "side": position.get("side"),
            "entry_price": safe_float(position.get("avgPrice")),
            "qty": safe_float(position.get("size")),
            "stop_loss": safe_float(position.get("stopLoss")),
            "take_profit": safe_float(position.get("takeProfit")),
            "atr_at_entry": 0.0,
            "entry_ts": utc_ts(),
            "best_price": safe_float(position.get("avgPrice")),
            "trail_stage": 0,
        }
    elif not position and open_trade and str(open_trade.get("trade_id", "")).startswith("restored-"):
        state["open_trade"] = None


def evaluate_closed_trade(state: dict[str, Any], equity: float, cfg: BotConfig):
    open_trade = state.get("open_trade")
    if not open_trade:
        return

    prev_equity = float(state.get("peak_equity") or equity)
    # only treat as closed if exchange says flat and we still had local open_trade
    pnl_equity = equity - float(state.get("start_equity") or equity)
    pnl_trade = pnl_equity - float(state.get("daily_realized_pnl") or 0.0)
    if abs(pnl_trade) < 1e-9:
        pnl_trade = 0.0

    state["daily_realized_pnl"] = pnl_equity
    if pnl_trade < 0:
        state["consecutive_losses"] = int(state.get("consecutive_losses", 0) or 0) + 1
        state["cooldown_until_ts"] = utc_ts() + max(0, cfg.loss_cooldown_seconds)
    else:
        state["consecutive_losses"] = 0
        state["cooldown_until_ts"] = int(state.get("cooldown_until_ts") or 0)

    log_trade({
        "ts": now_iso(),
        "event": "trade_closed",
        "trade": open_trade,
        "realized_pnl_est": pnl_trade,
        "equity": equity,
        "peak_equity_before": prev_equity,
    })
    state["open_trade"] = None


# ----------------------------
# Main loop
# ----------------------------


def main():
    cfg = load_config()
    session = make_session()
    state = load_state()

    log_runtime(
        f"bot_start symbol={cfg.symbol} tf={cfg.timeframe} demo={cfg.demo} testnet={cfg.testnet} leverage={cfg.leverage} "
        f"risk={cfg.max_risk_pct}% max_position={cfg.max_position_pct}%"
    )
    actual_leverage = cfg.leverage
    try:
        startup_filters = get_instrument_filters(session, cfg.category, cfg.symbol)
        actual_leverage = set_leverage(session, cfg, cfg.symbol, startup_filters.get("max_leverage", cfg.leverage))
        log_runtime(f"leverage_set value={actual_leverage}")
    except Exception as e:
        if "110043" in str(e):
            log_runtime(f"leverage_unchanged keep={actual_leverage}")
        else:
            log_runtime(f"WARN set_leverage_failed err={e}")
    log_runtime(f"dashboard_config host={cfg.dashboard_host} port={cfg.dashboard_port} (dashboard wiring pending)")

    while True:
        try:
            wallet = get_wallet_snapshot(session)
            equity = wallet["equity"]
            reset_day_if_needed(state, equity)
            state["peak_equity"] = max(float(state.get("peak_equity") or 0.0), equity)

            filters = get_instrument_filters(session, cfg.category, cfg.symbol)

            rows = get_klines(session, cfg.category, cfg.symbol, cfg.timeframe, limit=max(cfg.ema_slow + cfg.adx_len + 50, 220))
            highs, lows, closes, _volumes = parse_ohlc(rows)
            signal = build_signal(cfg, highs, lows, closes, signal_idx=-2)
            signal_candle_ts = int(float(rows[-2][0])) if len(rows) >= 2 else 0
            ticker = get_ticker(session, cfg.category, cfg.symbol)
            last_price = safe_float(ticker.get("lastPrice"), signal["price"])
            position = get_position(session, cfg.category, cfg.symbol)

            state["last_signal"] = {
                "ts": now_iso(),
                "side": signal["side"],
                "price": last_price,
                "ema_fast": signal["ema_fast"],
                "ema_slow": signal["ema_slow"],
                "rsi": signal["rsi"],
                "atr": signal["atr"],
                "adx": signal["adx"],
                "ema_gap_pct": signal["ema_gap_pct"],
                "signal_candle_ts": signal_candle_ts,
            }
            sync_open_trade_from_exchange(state, position)

            if position is None and state.get("open_trade"):
                evaluate_closed_trade(state, equity, cfg)

            daily_pnl_pct = pnl_pct_from_equity(float(state.get("start_equity") or equity), equity)
            drawdown_pct = pnl_pct_from_equity(float(state.get("peak_equity") or equity), equity)
            cooldown_until_ts = int(state.get("cooldown_until_ts") or 0)
            in_cooldown = utc_ts() < cooldown_until_ts

            pause_reason = ""
            if daily_pnl_pct <= -cfg.max_daily_loss_pct:
                pause_reason = f"daily loss {daily_pnl_pct:.2f}% <= -{cfg.max_daily_loss_pct}%"
            elif int(state.get("consecutive_losses") or 0) >= cfg.max_consecutive_losses:
                pause_reason = f"consecutive losses >= {cfg.max_consecutive_losses}"
            elif drawdown_pct <= -cfg.max_drawdown_pct:
                pause_reason = f"drawdown {drawdown_pct:.2f}% <= -{cfg.max_drawdown_pct}%"
            elif daily_pnl_pct >= cfg.daily_target_pct:
                pause_reason = f"daily target hit {daily_pnl_pct:.2f}% >= {cfg.daily_target_pct}%"
            elif int(state.get("daily_trade_count") or 0) >= cfg.max_trades_per_day:
                pause_reason = f"daily trade cap reached {state['daily_trade_count']} >= {cfg.max_trades_per_day}"

            state["paused"] = bool(pause_reason)
            state["pause_reason"] = pause_reason

            if position:
                open_trade = state.get("open_trade") or {}
                side = position.get("side")
                avg_price = safe_float(position.get("avgPrice"))
                atr_now = float(signal["atr"])
                best_price = max(float(open_trade.get("best_price") or avg_price), last_price) if side == "Buy" else min(float(open_trade.get("best_price") or avg_price), last_price)
                open_trade["best_price"] = best_price
                open_trade["qty"] = safe_float(position.get("size"))
                open_trade["entry_price"] = avg_price

                move = (best_price - avg_price) if side == "Buy" else (avg_price - best_price)
                trigger = atr_now * cfg.trailing_step_atr
                if atr_now > 0 and move >= trigger:
                    if side == "Buy":
                        new_sl = best_price - (atr_now * cfg.trailing_stop_atr)
                    else:
                        new_sl = best_price + (atr_now * cfg.trailing_stop_atr)

                    current_sl = safe_float(position.get("stopLoss") or open_trade.get("stop_loss"))
                    tick_size = filters.get("tick_size", 0.0)
                    min_update = tick_size * max(1, cfg.min_trail_update_ticks)
                    sl_delta = abs(new_sl - current_sl)
                    should_update = (
                        ((side == "Buy" and new_sl > current_sl) or (side == "Sell" and (current_sl == 0 or new_sl < current_sl)))
                        and (min_update <= 0 or sl_delta >= min_update)
                    )
                    if should_update:
                        tp = safe_float(position.get("takeProfit") or open_trade.get("take_profit"))
                        try:
                            set_trading_stop(session, cfg, cfg.symbol, tp, new_sl, tick_size=tick_size)
                            open_trade["stop_loss"] = new_sl
                            open_trade["trail_stage"] = int(open_trade.get("trail_stage") or 0) + 1
                            log_runtime(f"trail_update side={side} new_sl={new_sl:.2f} price={last_price:.2f}")
                        except Exception as e:
                            log_runtime(f"WARN trail_update_failed err={e}")
                state["open_trade"] = open_trade
            else:
                now_ts = utc_ts()
                can_trade_interval = now_ts - int(state.get("last_entry_ts") or 0) >= cfg.min_entry_interval_seconds
                same_candle = signal_candle_ts == int(state.get("last_entry_candle_ts") or 0)
                if not state["paused"] and not in_cooldown and signal["side"] in {"Buy", "Sell"} and can_trade_interval and not same_candle:
                    take_profit, stop_loss = compute_exit_prices(cfg, signal["side"], last_price, float(signal["atr"]))
                    qty = compute_qty(cfg, equity, last_price, stop_loss, actual_leverage, filters)
                    if qty > 0:
                        log_runtime(
                            f"entry_signal side={signal['side']} price={last_price:.2f} qty={qty:.6f} sl={stop_loss:.2f} tp={take_profit:.2f} "
                            f"rsi={signal['rsi']:.2f} adx={signal['adx']:.2f} ema_gap={signal['ema_gap_pct']:.3f}%"
                        )
                        order = place_market_order(session, cfg, cfg.symbol, signal["side"], qty)
                        time.sleep(2)
                        pos_after = get_position(session, cfg.category, cfg.symbol)
                        entry_price = safe_float((pos_after or {}).get("avgPrice"), last_price)
                        try:
                            set_trading_stop(session, cfg, cfg.symbol, take_profit, stop_loss, tick_size=filters.get("tick_size", 0.0))
                        except Exception as e:
                            log_runtime(f"WARN initial_set_trading_stop_failed err={e}")

                        state["trade_seq"] = int(state.get("trade_seq") or 0) + 1
                        trade_id = f"{utc_day()}-{state['trade_seq']}"
                        state["last_entry_ts"] = now_ts
                        state["last_entry_candle_ts"] = signal_candle_ts
                        state["daily_trade_count"] = int(state.get("daily_trade_count") or 0) + 1
                        state["open_trade"] = {
                            "trade_id": trade_id,
                            "side": signal["side"],
                            "entry_price": entry_price,
                            "qty": qty,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "atr_at_entry": signal["atr"],
                            "entry_ts": utc_ts(),
                            "best_price": entry_price,
                            "trail_stage": 0,
                            "order_resp": order,
                        }
                        log_trade({
                            "ts": now_iso(),
                            "event": "trade_opened",
                            "trade_id": trade_id,
                            "side": signal["side"],
                            "symbol": cfg.symbol,
                            "entry_price": entry_price,
                            "qty": qty,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "atr": signal["atr"],
                            "signal": state["last_signal"],
                        })
                    else:
                        log_runtime("skip_entry qty<=0 after sizing")
                elif state["paused"]:
                    log_runtime(f"paused reason={state['pause_reason']}")
                elif in_cooldown:
                    cooldown_left = max(0, cooldown_until_ts - utc_ts())
                    log_runtime(f"cooldown active remaining={cooldown_left}s")
                elif same_candle:
                    log_runtime(f"skip_entry same_signal_candle ts={signal_candle_ts}")
                elif not can_trade_interval:
                    wait_left = max(0, cfg.min_entry_interval_seconds - (now_ts - int(state.get('last_entry_ts') or 0)))
                    log_runtime(f"skip_entry interval_guard remaining={wait_left}s")
                else:
                    log_runtime(
                        f"no_entry signal={signal['side']} price={last_price:.2f} ema_fast={signal['ema_fast']:.2f} "
                        f"ema_slow={signal['ema_slow']:.2f} rsi={signal['rsi']:.2f} adx={signal['adx']:.2f} "
                        f"ema_gap={signal['ema_gap_pct']:.3f}%"
                    )

            state["last_loop_ts"] = utc_ts()
            save_state(state)
            time.sleep(max(15, cfg.analysis_interval_seconds))

        except KeyboardInterrupt:
            log_runtime("stopped_by_user")
            save_state(state)
            return
        except Exception as e:
            log_runtime(f"ERROR {e}")
            save_state(state)
            time.sleep(10)


if __name__ == "__main__":
    main()
