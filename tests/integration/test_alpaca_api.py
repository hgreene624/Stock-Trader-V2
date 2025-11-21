"""
Test Alpaca API historical data fetch.
This script tests different ways to fetch historical data from Alpaca.
"""

import os
from datetime import datetime, timedelta
import pytz

# Set test credentials
os.environ['ALPACA_API_KEY'] = 'PKOJHUORSUX2C3VPVMC2FGKDT2'
os.environ['ALPACA_SECRET_KEY'] = 'EFU2nQz3WYRjweBkLdw2vH5g5cPML2CTU18sEMSD19AG'

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

print("=" * 80)
print("Alpaca API Historical Data Test")
print("=" * 80)
print()

# Initialize client
api_key = os.environ['ALPACA_API_KEY']
secret_key = os.environ['ALPACA_SECRET_KEY']

print(f"API Key: {api_key[:8]}...")
print(f"Secret Key: {secret_key[:8]}...")
print()

client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
print("✅ Client initialized")
print()

# Test 1: Single symbol with start/end dates
print("=" * 80)
print("TEST 1: Single symbol (SPY) with start/end dates")
print("=" * 80)

end_date = datetime.now(pytz.UTC)
start_date = end_date - timedelta(days=300)

print(f"Start: {start_date}")
print(f"End: {end_date}")
print(f"Symbol: SPY")
print(f"Timeframe: Daily")
print()

try:
    request = StockBarsRequest(
        symbol_or_symbols='SPY',
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )

    print("Request created, fetching data...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")
    print(f"Response type: {type(bars)}")
    print(f"Response keys: {list(bars.keys()) if hasattr(bars, 'keys') else 'N/A'}")

    if 'SPY' in bars:
        spy_bars = bars['SPY']
        print(f"Number of bars: {len(spy_bars)}")
        if len(spy_bars) > 0:
            print(f"First bar: {spy_bars[0]}")
            print(f"Last bar: {spy_bars[-1]}")
    else:
        print("⚠️  WARNING: 'SPY' not in response")
        print(f"Available symbols: {list(bars.keys())}")

except Exception as e:
    print(f"❌ ERROR: {e}")
    print(f"Error type: {type(e)}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Multiple symbols with start/end dates
print("=" * 80)
print("TEST 2: Multiple symbols with start/end dates")
print("=" * 80)

symbols = ['SPY', 'XLE', 'XLY']
print(f"Symbols: {symbols}")
print()

try:
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date
    )

    print("Request created, fetching data...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")
    print(f"Symbols in response: {list(bars.keys())}")

    for symbol in symbols:
        if symbol in bars:
            count = len(bars[symbol])
            print(f"  {symbol}: {count} bars")
        else:
            print(f"  {symbol}: ❌ NOT IN RESPONSE")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Using limit parameter instead of dates
print("=" * 80)
print("TEST 3: Single symbol with limit (no start/end)")
print("=" * 80)

print(f"Symbol: SPY")
print(f"Timeframe: Daily")
print(f"Limit: 250 bars")
print()

try:
    request = StockBarsRequest(
        symbol_or_symbols='SPY',
        timeframe=TimeFrame.Day,
        limit=250
    )

    print("Request created, fetching data...")
    bars = client.get_stock_bars(request)

    print(f"✅ SUCCESS!")

    if 'SPY' in bars:
        spy_bars = bars['SPY']
        print(f"Number of bars: {len(spy_bars)}")
        if len(spy_bars) > 0:
            print(f"First bar: {spy_bars[0]}")
            print(f"Last bar: {spy_bars[-1]}")
    else:
        print("⚠️  WARNING: 'SPY' not in response")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 4: Check account info to verify API keys work
print("=" * 80)
print("TEST 4: Verify API credentials with Trading API")
print("=" * 80)

try:
    from alpaca.trading.client import TradingClient

    trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
    account = trading_client.get_account()

    print(f"✅ Trading API working")
    print(f"Account status: {account.status}")
    print(f"Buying power: ${float(account.buying_power):,.2f}")
    print(f"Portfolio value: ${float(account.portfolio_value):,.2f}")
    print(f"Paper trading: {account.account_number.startswith('P')}")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 5: Check what's actually returned by the problematic call
print("=" * 80)
print("TEST 5: Reproduce production request")
print("=" * 80)

# This mimics what the production code is doing
symbols = ['XLE', 'XLY', 'XLV', 'XLF', 'SPY', 'XLB', 'XLP', 'TLT', 'XLC', 'XLU', 'XLI', 'XLK', 'XLRE']
print(f"Symbols: {len(symbols)} symbols")
print(f"Start: {start_date.date()}")
print(f"End: {end_date.date()}")
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

    print(f"✅ Response received")
    print(f"Type: {type(bars)}")
    print(f"Has data for symbols:")

    for symbol in symbols:
        if symbol in bars:
            count = len(bars[symbol])
            status = "✅" if count > 0 else "⚠️ "
            print(f"  {status} {symbol}: {count} bars")
        else:
            print(f"  ❌ {symbol}: NOT IN RESPONSE")

    # Check the raw response structure
    print()
    print("Response structure:")
    print(f"  dir(bars): {[x for x in dir(bars) if not x.startswith('_')][:10]}...")

except Exception as e:
    print(f"❌ ERROR: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Test Complete")
print("=" * 80)
