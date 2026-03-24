import os, json, sys
from datetime import datetime

try:
    from pybit.unified_trading import HTTP
except Exception as e:
    print('IMPORT_ERROR', e)
    sys.exit(2)

demo = os.getenv('BYBIT_DEMO','').lower() in ('1','true','yes')
api_key = os.getenv('BYBIT_API_KEY')
api_secret = os.getenv('BYBIT_API_SECRET')
if not api_key or not api_secret:
    print('MISSING_CREDS')
    sys.exit(3)

session = HTTP(testnet=demo, api_key=api_key, api_secret=api_secret)
resp = session.get_positions(category='linear', symbol='BTCUSDT')
print(json.dumps(resp))
