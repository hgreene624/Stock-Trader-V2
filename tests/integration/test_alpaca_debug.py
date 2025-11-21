"""
Debug Alpaca API response structure.
"""

import os
from datetime import datetime, timedelta
import pytz

os.environ['ALPACA_API_KEY'] = 'PKOJHUORSUX2C3VPVMC2FGKDT2'
os.environ['ALPACA_SECRET_KEY'] = 'EFU2nQz3WYRjweBkLdw2vH5g5cPML2CTU18sEMSD19AG'

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

print("=" * 80)
print("Debug Alpaca API Response")
print("=" * 80)
print()

client = StockHistoricalDataClient(
    api_key=os.environ['ALPACA_API_KEY'],
    secret_key=os.environ['ALPACA_SECRET_KEY']
)

end_date = datetime.now(pytz.UTC) - timedelta(days=1)
start_date = end_date - timedelta(days=30)

print(f"Date range: {start_date.date()} to {end_date.date()}")
print()

request = StockBarsRequest(
    symbol_or_symbols='SPY',
    timeframe=TimeFrame.Day,
    start=start_date,
    end=end_date
)

print("Making request...")
bars = client.get_stock_bars(request)

print(f"\nResponse type: {type(bars)}")
print(f"Response class: {bars.__class__.__name__}")
print(f"\nDir (non-private attrs):")
for attr in dir(bars):
    if not attr.startswith('_'):
        print(f"  - {attr}")

print(f"\nIs it dict-like? hasattr __getitem__: {hasattr(bars, '__getitem__')}")
print(f"Is it iterable? hasattr __iter__: {hasattr(bars, '__iter__')}")
print(f"Has 'data' attr?: {hasattr(bars, 'data')}")
print(f"Has 'df' attr?: {hasattr(bars, 'df')}")

if hasattr(bars, 'data'):
    print(f"\ndata attribute type: {type(bars.data)}")
    print(f"data content: {bars.data}")

if hasattr(bars, 'df'):
    print(f"\ndf attribute type: {type(bars.df)}")
    try:
        df = bars.df
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame columns: {list(df.columns)}")
        print(f"DataFrame head:\n{df.head()}")
    except Exception as e:
        print(f"Error accessing df: {e}")

print(f"\nTrying to iterate:")
try:
    for key in bars:
        print(f"  Key: {key}, Type: {type(bars[key])}")
        if hasattr(bars[key], '__len__'):
            print(f"    Length: {len(bars[key])}")
        break  # Just show first one
except Exception as e:
    print(f"  Error iterating: {e}")

print(f"\nTrying dict access bars['SPY']:")
try:
    spy_data = bars['SPY']
    print(f"  Type: {type(spy_data)}")
    print(f"  Content: {spy_data}")
except Exception as e:
    print(f"  Error: {e}")

print(f"\nTrying to convert to dict:")
try:
    as_dict = dict(bars)
    print(f"  Keys: {list(as_dict.keys())}")
except Exception as e:
    print(f"  Error: {e}")
