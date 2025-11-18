"""
Test Alpaca API with IEX feed (free data for paper trading).
"""

import os
from datetime import datetime, timedelta
import pytz

os.environ['ALPACA_API_KEY'] = 'PKOJHUORSUX2C3VPVMC2FGKDT2'
os.environ['ALPACA_SECRET_KEY'] = 'EFU2nQz3WYRjweBkLdw2vH5g5cPML2CTU18sEMSD19AG'

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed

print("=" * 80)
print("Alpaca API Test with IEX Feed (Paper Trading)")
print("=" * 80)
print()

api_key = os.environ['ALPACA_API_KEY']
secret_key = os.environ['ALPACA_SECRET_KEY']

# Initialize client
client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
print("✅ Client initialized")
print()

# Test with IEX feed
end_date = datetime.now(pytz.UTC)
start_date = end_date - timedelta(days=300)

print("=" * 80)
print("TEST: SPY with IEX feed")
print("=" * 80)
print(f"Start: {start_date.date()}")
print(f"End: {end_date.date()}")
print(f"Feed: IEX (free)")
print()

try:
    request = StockBarsRequest(
        symbol_or_symbols='SPY',
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
        feed=DataFeed.IEX  # Use IEX feed instead of SIP
    )

    print("Fetching...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")

    if 'SPY' in bars:
        spy_bars = bars['SPY']
        print(f"Number of bars: {len(spy_bars)}")
        if len(spy_bars) > 0:
            print(f"\nFirst bar ({spy_bars[0].timestamp}):")
            print(f"  Open: ${spy_bars[0].open}")
            print(f"  Close: ${spy_bars[0].close}")
            print(f"\nLast bar ({spy_bars[-1].timestamp}):")
            print(f"  Open: ${spy_bars[-1].open}")
            print(f"  Close: ${spy_bars[-1].close}")
    else:
        print("⚠️  'SPY' not in response")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test multiple symbols
print("=" * 80)
print("TEST: Multiple symbols with IEX feed")
print("=" * 80)

symbols = ['SPY', 'XLE', 'XLY', 'XLV']
print(f"Symbols: {symbols}")
print()

try:
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
        feed=DataFeed.IEX
    )

    print("Fetching...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")
    print(f"Results:")
    for symbol in symbols:
        if symbol in bars:
            count = len(bars[symbol])
            print(f"  ✅ {symbol}: {count} bars")
        else:
            print(f"  ❌ {symbol}: NOT IN RESPONSE")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test all 13 symbols
print("=" * 80)
print("TEST: All 13 symbols (production symbols)")
print("=" * 80)

all_symbols = ['SPY', 'XLY', 'XLV', 'XLC', 'XLRE', 'XLP', 'XLI', 'TLT', 'XLE', 'XLF', 'XLU', 'XLK', 'XLB']
print(f"Symbols: {len(all_symbols)} symbols")
print()

try:
    request = StockBarsRequest(
        symbol_or_symbols=all_symbols,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
        feed=DataFeed.IEX
    )

    print("Fetching...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")
    print(f"Results:")

    success_count = 0
    for symbol in all_symbols:
        if symbol in bars and len(bars[symbol]) > 0:
            count = len(bars[symbol])
            print(f"  ✅ {symbol}: {count} bars")
            success_count += 1
        elif symbol in bars:
            print(f"  ⚠️  {symbol}: 0 bars")
        else:
            print(f"  ❌ {symbol}: NOT IN RESPONSE")

    print()
    print(f"Summary: {success_count}/{len(all_symbols)} symbols have data")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Conclusion:")
print("=" * 80)
print("Use feed=DataFeed.IEX for paper trading accounts!")
print("This provides free IEX market data instead of requiring SIP subscription.")
print("=" * 80)
