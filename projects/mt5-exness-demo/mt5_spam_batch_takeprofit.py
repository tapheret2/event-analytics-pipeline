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


def main():
    base_dir = os.path.dirname(__file__)
    load_env_file(os.path.join(base_dir, "spam_config.env"))

    symbol = os.environ.get("SYMBOL", "ETHUSD")
    batch_orders = env_int("BATCH_ORDERS", 20)
    spacing_ms = env_int("ORDER_SPACING_MS", 200)
    profit_target = env_float("PROFIT_TARGET_USD", 0.50)
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
        print("terminal:", term.name, term.company, term.path)
        print("account:", acc.login, acc.server, "balance=", acc.balance, "equity=", acc.equity)
        print("symbol:", symbol)

        if not mt5.symbol_select(symbol, True):
            code, msg = mt5.last_error()
            raise SystemExit(f"symbol_select failed: {code} {msg}")

        info = mt5.symbol_info(symbol)
        if info is None:
            raise SystemExit("symbol_info is None")

        vol = float(info.volume_min or 0.1)
        print("volume_min:", vol)

        # Decide direction
        side = pick_side(symbol, momentum_s)
        side_txt = "BUY" if side == mt5.ORDER_TYPE_BUY else "SELL"
        print(f"direction_by_momentum({momentum_s}s): {side_txt}")

        # Open batch
        ok = 0
        errors = 0
        for i in range(batch_orders):
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                errors += 1
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
                errors += 1
            time.sleep(spacing_ms / 1000)

        print(f"opened: ok={ok} errors={errors}")

        # Monitor and close when profit reached
        t0 = time.time()
        while True:
            prof = total_profit(symbol, magic)
            pos = positions_for_magic(symbol, magic)
            print(time.strftime("%H:%M:%S"), f"positions={len(pos)} profit={prof:.2f} target={profit_target:.2f}")

            if len(pos) == 0:
                print("no positions left; done")
                break

            if prof >= profit_target:
                print("profit target hit -> closing all")
                for p in list(pos):
                    close_position(symbol, p, deviation, magic)
                time.sleep(1)
                continue

            if time.time() - t0 >= max_hold:
                print("max hold reached -> closing all")
                for p in list(pos):
                    close_position(symbol, p, deviation, magic)
                time.sleep(1)
                continue

            time.sleep(1)

        print("DONE")

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
