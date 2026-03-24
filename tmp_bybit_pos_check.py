import os, json
from pybit.unified_trading import HTTP
import subprocess

def reg_get(name: str):
    try:
        cmd = ["powershell","-NoProfile","-Command", f"(Get-ItemProperty -Path 'HKCU:\\Environment' -Name {name} -ErrorAction SilentlyContinue).{name}"]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
        return out if out else None
    except Exception:
        return None

api_key = os.environ.get('BYBIT_API_KEY') or reg_get('BYBIT_API_KEY')
api_secret = os.environ.get('BYBIT_API_SECRET') or reg_get('BYBIT_API_SECRET')
demo_flag = os.environ.get('BYBIT_DEMO')
if demo_flag is None:
    demo_flag = reg_get('BYBIT_DEMO')

is_demo = str(demo_flag).lower() in ('1','true','yes','y','on')

if not api_key or not api_secret:
    raise SystemExit('Missing BYBIT_API_KEY/BYBIT_API_SECRET in env or HKCU\\Environment')

session = HTTP(testnet=is_demo, api_key=api_key, api_secret=api_secret)
resp = session.get_positions(category='linear', symbol='BTCUSDT')
lst = (((resp or {}).get('result') or {}).get('list') or [])
pos = None
for p in lst:
    if p.get('symbol') == 'BTCUSDT':
        pos = p
        break

size = 0.0
side = None
avg = 0.0
if pos:
    try:
        size = float(pos.get('size') or 0)
    except Exception:
        size = 0.0
    side = pos.get('side')
    try:
        avg = float(pos.get('avgPrice') or 0)
    except Exception:
        avg = 0.0

is_flat = (size == 0.0)
state = {
    'flat': bool(is_flat),
    'side': None if is_flat else side,
    'size': 0.0 if is_flat else size,
    'avgPrice': None if is_flat else avg,
}
print(json.dumps({'state': state, 'is_demo': is_demo}, ensure_ascii=False))
