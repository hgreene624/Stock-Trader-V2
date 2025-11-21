#!/usr/bin/env python3
"""Quick test to show actual momentum values."""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta, timezone

# Read .env file
env_path = project_root / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                # Strip quotes from value
                val = val.strip('"').strip("'")
                os.environ[key] = val

api_key = os.environ.get('ALPACA_API_KEY')
secret_key = os.environ.get('ALPACA_API_SECRET')  # Note: _SECRET not _SECRET_KEY

if not api_key or not secret_key:
    print("ERROR: ALPACA_API_KEY or ALPACA_SECRET_KEY not found in .env")
    sys.exit(1)

# Initialize data client
data_client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)

# Request 126-day momentum data
now = datetime.now(timezone.utc)
start = now - timedelta(days=200)

symbols = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE', 'TLT']

print(f"Fetching data from {start.date()} to {now.date()}")
print(f"Calculating 126-day momentum for {len(symbols)} symbols...\n")

request_params = StockBarsRequest(
    symbol_or_symbols=symbols,
    timeframe=TimeFrame.Day,
    start=start
)

print("Requesting bars...")
try:
    bars = data_client.get_stock_bars(request_params)
    print("API call successful!")
    for sym in symbols:
        if sym in bars:
            print(f"  {sym}: {len(bars[sym])} bars")
        else:
            print(f"  {sym}: NO DATA")
except Exception as e:
    print(f"ERROR: API call failed: {e}")
    print(f"Exception type: {type(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

momentum_data = []

for symbol in symbols:
    if symbol in bars and len(bars[symbol]) > 126:
        symbol_bars = bars[symbol]
        current_price = float(symbol_bars[-1].close)
        old_price = float(symbol_bars[-127].close)

        momentum = (current_price / old_price) - 1.0
        momentum_data.append({
            'symbol': symbol,
            'momentum': momentum,
            'current': current_price,
            'old': old_price,
            'bars': len(symbol_bars)
        })
    else:
        bars_count = len(bars[symbol]) if symbol in bars else 0
        momentum_data.append({
            'symbol': symbol,
            'momentum': 0.0,
            'current': 0,
            'old': 0,
            'bars': bars_count
        })

# Sort by momentum (descending)
momentum_data.sort(key=lambda x: x['momentum'], reverse=True)

print("=" * 80)
print(f"{'Rank':<6} {'Symbol':<8} {'Mom%':>10} {'Current':>10} {'126d Ago':>10} {'Bars':>6}")
print("=" * 80)

for i, data in enumerate(momentum_data, 1):
    rank_marker = "●" if data['symbol'] in ['XLK', 'XLU', 'XLY'] else "○"
    print(f"{rank_marker} #{i:<3} {data['symbol']:<8} {data['momentum']*100:>9.2f}% ${data['current']:>9.2f} ${data['old']:>9.2f} {data['bars']:>6}")

print("=" * 80)
print("\n● = Currently held position")
print("○ = Not held")
print("\nIf ranking is correct, ● should appear on ranks #1, #2, #3")
print("(Sector rotation model buys top 3 momentum)")
