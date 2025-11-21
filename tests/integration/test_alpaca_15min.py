"""
Test Alpaca API with end date 15+ minutes in the past (required for free SIP data).
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
print("Alpaca API Test - Historical Data with 15+ Min Delay")
print("=" * 80)
print()

api_key = os.environ['ALPACA_API_KEY']
secret_key = os.environ['ALPACA_SECRET_KEY']

client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
print("✅ Client initialized")
print()

# KEY FIX: End date must be at least 15 minutes in the past for free SIP data
end_date = datetime.now(pytz.UTC) - timedelta(days=1)  # Yesterday to be safe
start_date = end_date - timedelta(days=300)

print(f"Start: {start_date.date()}")
print(f"End: {end_date.date()} (yesterday - safely >15min old)")
print()

# Test 1: Single symbol
print("=" * 80)
print("TEST 1: Single symbol (SPY)")
print("=" * 80)

try:
    request = StockBarsRequest(
        symbol_or_symbols='SPY',
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )

    print("Fetching...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")

    if 'SPY' in bars:
        spy_bars = bars['SPY']
        print(f"Number of bars: {len(spy_bars)}")
        if len(spy_bars) > 0:
            print(f"\nFirst bar: {spy_bars[0].timestamp} - Close: ${spy_bars[0].close}")
            print(f"Last bar: {spy_bars[-1].timestamp} - Close: ${spy_bars[-1].close}")
    else:
        print("⚠️  'SPY' not in response")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: All production symbols
print("=" * 80)
print("TEST 2: All 13 production symbols")
print("=" * 80)

symbols = ['SPY', 'XLY', 'XLV', 'XLC', 'XLRE', 'XLP', 'XLI', 'TLT', 'XLE', 'XLF', 'XLU', 'XLK', 'XLB']
print(f"Symbols: {len(symbols)} symbols")
print()

try:
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )

    print("Fetching...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")
    print(f"Results:")

    success_count = 0
    for symbol in symbols:
        if symbol in bars and len(bars[symbol]) > 0:
            count = len(bars[symbol])
            last_bar = bars[symbol][-1]
            print(f"  ✅ {symbol}: {count} bars (last: {last_bar.timestamp.date()} @ ${last_bar.close:.2f})")
            success_count += 1
        elif symbol in bars:
            print(f"  ⚠️  {symbol}: 0 bars")
        else:
            print(f"  ❌ {symbol}: NOT IN RESPONSE")

    print()
    print(f"Summary: {success_count}/{len(symbols)} symbols have data")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("KEY FIX: Set end date to at least 15 minutes (or 1 day) in the past!")
print("This allows free accounts to access SIP historical data.")
print("=" * 80)
