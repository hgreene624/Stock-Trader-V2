"""
Test the broker adapter get_latest_bars method with the fix.
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

os.environ['ALPACA_API_KEY'] = 'PKOJHUORSUX2C3VPVMC2FGKDT2'
os.environ['ALPACA_SECRET_KEY'] = 'EFU2nQz3WYRjweBkLdw2vH5g5cPML2CTU18sEMSD19AG'

from production.runner.broker_adapter import AlpacaBrokerAdapter

print("=" * 80)
print("Test Broker Adapter with Fix")
print("=" * 80)
print()

# Initialize adapter
adapter = AlpacaBrokerAdapter(
    api_key=os.environ['ALPACA_API_KEY'],
    secret_key=os.environ['ALPACA_SECRET_KEY'],
    paper=True
)

print("✅ Broker adapter initialized")
print()

# Test 1: Get latest bars for single symbol
print("=" * 80)
print("TEST 1: Latest bars for SPY (limit=5)")
print("=" * 80)

result = adapter.get_latest_bars(['SPY'], timeframe='1Day', limit=5)

if 'SPY' in result and len(result['SPY']) > 0:
    print(f"✅ SUCCESS! Got {len(result['SPY'])} bars")
    for i, bar in enumerate(result['SPY'][-3:], 1):  # Show last 3
        print(f"  Bar {i}: {bar['timestamp']} - Close: ${bar['close']:.2f}, Volume: {bar['volume']:,.0f}")
else:
    print(f"❌ FAILED: No data for SPY")
    print(f"Result: {result}")

print()

# Test 2: Get latest bars for multiple symbols (all production symbols)
print("=" * 80)
print("TEST 2: Latest bars for all 13 production symbols")
print("=" * 80)

symbols = ['SPY', 'XLY', 'XLV', 'XLC', 'XLRE', 'XLP', 'XLI', 'TLT', 'XLE', 'XLF', 'XLU', 'XLK', 'XLB']

result = adapter.get_latest_bars(symbols, timeframe='1Day', limit=10)

success_count = 0
for symbol in symbols:
    if symbol in result and len(result[symbol]) > 0:
        bars = result[symbol]
        last_bar = bars[-1]
        print(f"  ✅ {symbol}: {len(bars)} bars (last: {last_bar['timestamp'].date()} @ ${last_bar['close']:.2f})")
        success_count += 1
    else:
        print(f"  ❌ {symbol}: No data")

print()
print(f"Summary: {success_count}/{len(symbols)} symbols have data")

if success_count == len(symbols):
    print()
    print("=" * 80)
    print("🎉 ALL TESTS PASSED! Broker adapter is working correctly.")
    print("=" * 80)
    print()
    print("The fix correctly accesses bars.data instead of using 'in' operator.")
    print("v9 is ready to deploy!")
else:
    print()
    print("=" * 80)
    print("⚠️  SOME TESTS FAILED")
    print("=" * 80)
