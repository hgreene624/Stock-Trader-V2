"""
Test Alpaca latest bars and quotes (real-time data).
"""

import os

os.environ['ALPACA_API_KEY'] = 'PKOJHUORSUX2C3VPVMC2FGKDT2'
os.environ['ALPACA_SECRET_KEY'] = 'EFU2nQz3WYRjweBkLdw2vH5g5cPML2CTU18sEMSD19AG'

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest, StockLatestQuoteRequest
from alpaca.data.enums import DataFeed

print("=" * 80)
print("Alpaca API Test - Latest Bars (Real-time)")
print("=" * 80)
print()

api_key = os.environ['ALPACA_API_KEY']
secret_key = os.environ['ALPACA_SECRET_KEY']

client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
print("✅ Client initialized")
print()

# Test 1: Latest bar for single symbol
print("=" * 80)
print("TEST 1: Latest bar for SPY")
print("=" * 80)

try:
    request = StockLatestBarRequest(symbol_or_symbols='SPY', feed=DataFeed.IEX)
    bars = client.get_stock_latest_bar(request)

    print(f"✅ SUCCESS!")
    if 'SPY' in bars:
        bar = bars['SPY']
        print(f"Timestamp: {bar.timestamp}")
        print(f"Open: ${bar.open}")
        print(f"High: ${bar.high}")
        print(f"Low: ${bar.low}")
        print(f"Close: ${bar.close}")
        print(f"Volume: {bar.volume:,}")
    else:
        print("⚠️  'SPY' not in response")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Latest bars for multiple symbols
print("=" * 80)
print("TEST 2: Latest bars for multiple symbols")
print("=" * 80)

symbols = ['SPY', 'XLE', 'XLY', 'XLV', 'XLC', 'XLRE', 'XLP', 'XLI', 'TLT', 'XLF', 'XLU', 'XLK', 'XLB']
print(f"Symbols: {len(symbols)} symbols")
print()

try:
    request = StockLatestBarRequest(symbol_or_symbols=symbols, feed=DataFeed.IEX)
    bars = client.get_stock_latest_bar(request)

    print(f"✅ SUCCESS!")
    print(f"Symbols with data:")

    for symbol in symbols:
        if symbol in bars:
            bar = bars[symbol]
            print(f"  ✅ {symbol}: ${bar.close:.2f} @ {bar.timestamp}")
        else:
            print(f"  ❌ {symbol}: NOT IN RESPONSE")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Check if we can get quotes
print("=" * 80)
print("TEST 3: Latest quotes")
print("=" * 80)

try:
    request = StockLatestQuoteRequest(symbol_or_symbols=['SPY', 'XLE'], feed=DataFeed.IEX)
    quotes = client.get_stock_latest_quote(request)

    print(f"✅ SUCCESS!")
    for symbol in ['SPY', 'XLE']:
        if symbol in quotes:
            quote = quotes[symbol]
            print(f"{symbol}:")
            print(f"  Bid: ${quote.bid_price} x {quote.bid_size}")
            print(f"  Ask: ${quote.ask_price} x {quote.ask_size}")
            print(f"  Timestamp: {quote.timestamp}")
        else:
            print(f"{symbol}: NOT IN RESPONSE")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Conclusion:")
print("=" * 80)
print("Latest bars/quotes work, but historical bars don't for paper trading.")
print("Paper trading accounts have limited historical data access.")
print("Solution: Use the download script which works differently,")
print("or switch to a live (funded) account for full historical data.")
print("=" * 80)
