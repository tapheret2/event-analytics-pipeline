import inspect
from pybit.unified_trading import HTTP
print('module:', HTTP.__module__)
print('signature:', inspect.signature(HTTP))
try:
    src = inspect.getsource(HTTP)
    print(src[:2000])
except Exception as e:
    print('getsource_failed:', e)
