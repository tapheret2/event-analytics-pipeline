from __future__ import annotations

import time
import MetaTrader5 as mt5


def main():
    # 1) Initialize connection to the running MT5 terminal
    if not mt5.initialize():
        code, msg = mt5.last_error()
        raise SystemExit(f"MT5 initialize failed: {code} {msg}\n\nMake sure MetaTrader 5 is running + logged in, and Algo Trading/AutoTrading is enabled.")

    try:
        term = mt5.terminal_info()
        acc = mt5.account_info()
        print("terminal:", term)
        print("account:", acc)

        # 2) Find ETH-related symbols (Exness naming differs)
        syms = mt5.symbols_get("*ETH*") or []
        names = sorted({s.name for s in syms})
        print("ETH candidates:")
        for n in names[:50]:
            print("-", n)

        if not names:
            raise SystemExit("No ETH symbols found. Try enabling crypto symbols in Market Watch.")

        # Prefer ETHUSD if present
        pick = None
        for pref in ["ETHUSD", "ETHUSDm", "ETHUSD." , "ETHUSDT", "ETHUSD#"]:
            for n in names:
                if n.upper() == pref.upper():
                    pick = n
                    break
            if pick:
                break
        if not pick:
            pick = names[0]

        print("picked_symbol:", pick)

        # 3) Ensure symbol is selected in Market Watch
        if not mt5.symbol_select(pick, True):
            code, msg = mt5.last_error()
            raise SystemExit(f"symbol_select failed for {pick}: {code} {msg}")

        info = mt5.symbol_info(pick)
        tick = mt5.symbol_info_tick(pick)
        print("symbol_info:", info)
        print("tick:", tick)

        if tick is None:
            raise SystemExit("No tick data. Market may be closed or symbol not available.")

        # 4) Place minimal market order (DEMO test)
        vol = info.volume_min if info and info.volume_min else 0.01
        vol = float(vol)

        # Buy at market
        price = tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pick,
            "volume": vol,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "deviation": 50,
            "magic": 240322,
            "comment": "openclaw-mt5-demo-test",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        print("sending order:", request)
        result = mt5.order_send(request)
        print("order_send result:", result)
        if result is None:
            code, msg = mt5.last_error()
            raise SystemExit(f"order_send returned None: {code} {msg}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise SystemExit(f"order failed retcode={result.retcode} comment={result.comment}")

        # 5) Wait a moment then close the position (sell)
        time.sleep(2)

        positions = mt5.positions_get(symbol=pick) or []
        print("positions:", positions)
        if not positions:
            raise SystemExit("No position found after opening (unexpected).")

        pos = positions[0]
        close_price = mt5.symbol_info_tick(pick).bid
        close_req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pick,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL,
            "position": pos.ticket,
            "price": close_price,
            "deviation": 50,
            "magic": 240322,
            "comment": "openclaw-mt5-demo-test-close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        print("closing:", close_req)
        close_res = mt5.order_send(close_req)
        print("close result:", close_res)

        print("OK: open+close demo test completed")

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
