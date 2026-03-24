from __future__ import annotations

import os
import time
import MetaTrader5 as mt5


def load_env_file(path: str):
    if not os.path.exists(path):
        return
    for line in open(path, "r", encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k and k not in os.environ:
            os.environ[k] = v


def env_int(name: str, default: int) -> int:
    try:
        return int(float(os.environ.get(name, str(default))))
    except Exception:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except Exception:
        return default


def pick_side(symbol: str, momentum_seconds: int) -> int:
    """Return mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL based on short momentum."""
    tick1 = mt5.symbol_info_tick(symbol)
    if tick1 is None:
        return mt5.ORDER_TYPE_BUY
    p1 = float(tick1.ask or tick1.bid)
    time.sleep(max(0, momentum_seconds))
    tick2 = mt5.symbol_info_tick(symbol)
    if tick2 is None:
        return mt5.ORDER_TYPE_BUY
    p2 = float(tick2.ask or tick2.bid)
    return mt5.ORDER_TYPE_BUY if p2 >= p1 else mt5.ORDER_TYPE_SELL


def positions_for_magic(symbol: str, magic: int):
    pos = mt5.positions_get(symbol=symbol) or ()
    return [p for p in pos if int(p.magic) == int(magic)]


def total_profit(symbol: str, magic: int) -> float:
    return sum(float(p.profit) for p in positions_for_magic(symbol, magic))


def close_position(symbol: str, pos, deviation: int, magic: int):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    if pos.type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(pos.volume),
        "type": order_type,
        "position": int(pos.ticket),
        "price": float(price),
        "deviation": int(deviation),
        "magic": int(magic),
        "comment": "openclaw-mt5-spam-close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    return mt5.order_send(req)


def open_batch(symbol: str, batch_orders: int, spacing_ms: int, deviation: int, magic: int, momentum_s: int, volume: float | None):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError("symbol_info is None")

    # Use configured volume if provided; otherwise use min.
    vol = float(volume) if volume is not None else float(info.volume_min or 0.1)
    # Clamp to broker constraints
    if info.volume_min:
        vol = max(vol, float(info.volume_min))
    if info.volume_max:
        vol = min(vol, float(info.volume_max))

    side = pick_side(symbol, momentum_s)
    side_txt = "BUY" if side == mt5.ORDER_TYPE_BUY else "SELL"

    ok = 0
    err = 0
    for _ in range(batch_orders):
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            err += 1
            time.sleep(spacing_ms / 1000)
            continue
        price = tick.ask if side == mt5.ORDER_TYPE_BUY else tick.bid

        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": vol,
            "type": side,
            "price": float(price),
            "deviation": int(deviation),
            "magic": int(magic),
            "comment": "openclaw-mt5-spam",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        res = mt5.order_send(req)
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            ok += 1
        else:
            err += 1
        time.sleep(spacing_ms / 1000)

    return side_txt, vol, ok, err


def close_all(symbol: str, magic: int, deviation: int):
    pos = positions_for_magic(symbol, magic)
    for p in list(pos):
        close_position(symbol, p, deviation, magic)


def main():
    base_dir = os.path.dirname(__file__)
    load_env_file(os.path.join(base_dir, "spam_config.env"))

    symbol = os.environ.get("SYMBOL", "ETHUSD")
    batch_orders = env_int("BATCH_ORDERS", 20)
    spacing_ms = env_int("ORDER_SPACING_MS", 200)
    volume = env_float("VOLUME", -1.0)
    volume = None if volume <= 0 else volume

    profit_target = env_float("PROFIT_TARGET_USD", 0.50)
    loss_cut = env_float("LOSS_CUT_USD", 1.00)
    max_hold = env_int("MAX_HOLD_SECONDS", 60)
    deviation = env_int("DEVIATION", 50)
    momentum_s = env_int("MOMENTUM_SECONDS", 3)
    magic = env_int("MAGIC", 240322)

    if not mt5.initialize():
        code, msg = mt5.last_error()
        raise SystemExit(f"MT5 initialize failed: {code} {msg}\nMake sure MT5 is running + logged in + Algo Trading ON.")

    try:
        acc = mt5.account_info()
        term = mt5.terminal_info()
        print("terminal:", term.name, term.company)
        print("account:", acc.login, acc.server, "balance=", acc.balance, "equity=", acc.equity)
        print("symbol:", symbol)
        print(
            "loop config:",
            f"batch={batch_orders}",
            f"spacing_ms={spacing_ms}",
            f"volume={volume if volume is not None else 'min'}",
            f"profit_target={profit_target}",
            f"loss_cut={loss_cut}",
            f"max_hold_s={max_hold}",
        )

        if not mt5.symbol_select(symbol, True):
            code, msg = mt5.last_error()
            raise SystemExit(f"symbol_select failed: {code} {msg}")

        consecutive_fail_batches = 0
        batch_id = 0

        while True:
            batch_id += 1

            # Ensure no leftover positions for this magic
            if positions_for_magic(symbol, magic):
                close_all(symbol, magic, deviation)
                time.sleep(1)

            side_txt, vol, ok, err = open_batch(symbol, batch_orders, spacing_ms, deviation, magic, momentum_s, volume)
            print(time.strftime("%H:%M:%S"), f"BATCH#{batch_id} OPEN {side_txt} vol={vol} ok={ok} err={err}")

            if ok == 0:
                consecutive_fail_batches += 1
                if consecutive_fail_batches >= 3:
                    print("Too many failed batches -> stop.")
                    break
                time.sleep(2)
                continue
            consecutive_fail_batches = 0

            # Monitor PnL and close conditions
            t0 = time.time()
            while True:
                prof = total_profit(symbol, magic)
                pos = positions_for_magic(symbol, magic)
                print(time.strftime("%H:%M:%S"), f"BATCH#{batch_id} positions={len(pos)} profit={prof:.2f}")

                if not pos:
                    break

                # Take profit
                if prof >= profit_target:
                    print(time.strftime("%H:%M:%S"), f"BATCH#{batch_id} TP hit -> close all")
                    close_all(symbol, magic, deviation)
                    time.sleep(1)
                    break

                # Cut loss
                if prof <= -abs(loss_cut):
                    print(time.strftime("%H:%M:%S"), f"BATCH#{batch_id} LOSS cut -> close all")
                    close_all(symbol, magic, deviation)
                    time.sleep(1)
                    break

                # Timeout
                if time.time() - t0 >= max_hold:
                    print(time.strftime("%H:%M:%S"), f"BATCH#{batch_id} TIMEOUT -> close all")
                    close_all(symbol, magic, deviation)
                    time.sleep(1)
                    break

                time.sleep(1)

            # immediately continue next batch
            time.sleep(0.5)

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
