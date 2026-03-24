import os

old_k = "pTwlMemPdrEyWh5vbx"
old_s = "Pad5AQWaTEbXi49uiuTYjexkSizmP3LWbtaa"


def get_env(name: str):
    v = os.environ.get(name)
    if v:
        return v
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as k:
                val, _ = winreg.QueryValueEx(k, name)
                if isinstance(val, str) and val:
                    return val
        except Exception:
            return None
    return None


k = get_env("BYBIT_API_KEY") or ""
s = get_env("BYBIT_API_SECRET") or ""
demo = (get_env("BYBIT_DEMO") or "").lower()

ready = bool(k and s and demo in ("1", "true", "yes", "y") and k != old_k and s != old_s)

print(
    "READY" if ready else "NOT_READY",
    "k_len=", len(k),
    "s_len=", len(s),
    "demo=", demo,
)
