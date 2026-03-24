import os, json
from datetime import datetime
from zoneinfo import ZoneInfo

STATE_PATH = r"C:/Users/ADMIN/.openclaw/workspace/projects/bybit-demo-bot/notify_state_btcusdt.json"

# 1) read previous snapshot
try:
    with open(STATE_PATH, 'r', encoding='utf-8') as f:
        prev = json.load(f)
except FileNotFoundError:
    prev = {"flat": True, "side": None, "size": 0.0, "avgPrice": None}

# normalize prev
prev_flat = bool(prev.get('flat', True))
prev_side = prev.get('side') if not prev_flat else None
prev_size = float(prev.get('size') or 0.0) if not prev_flat else 0.0
prev_avg = prev.get('avgPrice') if not prev_flat else None

# 2) query current position
key = os.getenv('BYBIT_API_KEY')
sec = os.getenv('BYBIT_API_SECRET')
demo = os.getenv('BYBIT_DEMO', '').lower() in ('1','true','yes','on')

if not key or not sec:
    raise SystemExit('ERROR: Missing BYBIT_API_KEY/BYBIT_API_SECRET in environment')

from pybit.unified_trading import HTTP

session = HTTP(
    demo=demo,
    testnet=False,
    api_key=key,
    api_secret=sec,
)

resp = session.get_positions(category='linear', symbol='BTCUSDT')
# resp shape: { 'retCode':0, 'result': { 'list': [ { 'size':'0', 'side':'Buy', 'avgPrice':'0', ... } ] } }
if not isinstance(resp, dict) or resp.get('retCode') not in (0, '0', None):
    raise SystemExit(f"ERROR: Bybit API error: {resp}")

lst = (((resp.get('result') or {}).get('list')) or [])
pos = lst[0] if lst else {}

# Size is string; side is 'Buy'/'Sell'; avgPrice string
try:
    size = float(pos.get('size') or 0.0)
except Exception:
    size = 0.0
side = pos.get('side')
try:
    avg = float(pos.get('avgPrice') or 0.0)
except Exception:
    avg = 0.0

flat = (size == 0.0) or (side in (None, '', 'None'))
if flat:
    side = None
    avg = None

# 3) determine transition
msgs = []
now_bkk = datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y-%m-%d %H:%M:%S')

def fmt_open(s, sz, ap):
    return f"[{now_bkk} ICT] (DEMO) BTCUSDT OPEN\nSide: {s}\nSize: {sz}\nAvgPrice: {ap}"

def fmt_close(prev_s, prev_sz, prev_ap):
    return f"[{now_bkk} ICT] (DEMO) BTCUSDT CLOSE\nPrev side: {prev_s}\nPrev size: {prev_sz}\nPrev avgPrice: {prev_ap}"

if prev_flat and not flat:
    msgs.append(fmt_open(side, size, avg))
elif (not prev_flat) and flat:
    msgs.append(fmt_close(prev_side, prev_size, prev_avg))
elif (not prev_flat) and (not flat) and (prev_side != side):
    # side change = close + open
    msgs.append(fmt_close(prev_side, prev_size, prev_avg))
    msgs.append(fmt_open(side, size, avg))

# 5) write new snapshot
new_state = {
    'flat': bool(flat),
    'side': side,
    'size': float(size) if not flat else 0.0,
    'avgPrice': float(avg) if (not flat and avg is not None) else None,
}
with open(STATE_PATH, 'w', encoding='utf-8') as f:
    json.dump(new_state, f, ensure_ascii=False, indent=2)

# 4/6) output
if not msgs:
    print('NO_REPLY', end='')
else:
    # NOTE: Cron delivery will post this to Telegram; we do not call message tool here.
    print('\n\n'.join(msgs), end='')
