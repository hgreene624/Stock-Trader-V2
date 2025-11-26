import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Load VIX data to understand regimes
vix = pd.read_parquet('data/equities/^VIX_1D.parquet')
vix['date'] = vix.index.date

# Load trades
standalone = pd.read_csv('results/analysis/20251125_120208/trades.csv')
combined = pd.read_csv('results/analysis/20251125_145000/trades.csv')

# Convert timestamps
standalone['timestamp'] = pd.to_datetime(standalone['timestamp'])
combined['timestamp'] = pd.to_datetime(combined['timestamp'])
standalone['date'] = standalone['timestamp'].dt.date
combined['date'] = combined['timestamp'].dt.date

# Focus on the divergence period (Feb-Apr 2020)
start_date = pd.to_datetime('2020-02-20').date()
end_date = pd.to_datetime('2020-04-30').date()

print("="*80)
print("ANALYSIS OF TRADE DIVERGENCE - COVID CRASH PERIOD")
print("="*80)

# Check VIX levels during divergence dates
divergence_dates = [
    '2020-02-27', '2020-03-02', '2020-03-03', '2020-03-06',
    '2020-03-09', '2020-03-13', '2020-03-16', '2020-03-20',
    '2020-03-23', '2020-03-27', '2020-03-30', '2020-04-03',
    '2020-04-06', '2020-04-13'
]

print("\nVIX LEVELS DURING DIVERGENCE:")
print("-"*50)
for date_str in divergence_dates:
    date = pd.to_datetime(date_str).date()
    vix_val = vix[vix['date'] == date]['close'].values
    if len(vix_val) > 0:
        vix_level = vix_val[0]
        regime = "PANIC" if vix_level > 30 else "NORMAL"
        print(f"{date_str}: VIX = {vix_level:.2f} - {regime} MODE")

# Analyze what each model traded
print("\n"+"="*80)
print("STANDALONE MODEL TRADES (SectorRotation only):")
print("-"*50)

for date_str in divergence_dates[:8]:  # Show first 8 dates
    date = pd.to_datetime(date_str).date()
    s_trades = standalone[standalone['date'] == date]

    if len(s_trades) > 0:
        print(f"\n{date_str}:")
        for _, trade in s_trades.iterrows():
            print(f"  {trade['symbol']:4} {trade['side']:4} {abs(trade['quantity']):6.0f} @ ${trade['price']:7.2f}")
    else:
        print(f"\n{date_str}: NO TRADES")

print("\n"+"="*80)
print("COMBINED MODEL TRADES (AdaptiveRegimeSwitcher):")
print("-"*50)

for date_str in divergence_dates[:8]:  # Show first 8 dates
    date = pd.to_datetime(date_str).date()
    c_trades = combined[combined['date'] == date]

    if len(c_trades) > 0:
        print(f"\n{date_str}:")
        for _, trade in c_trades.iterrows():
            print(f"  {trade['symbol']:4} {trade['side']:4} {abs(trade['quantity']):6.0f} @ ${trade['price']:7.2f}")
    else:
        print(f"\n{date_str}: NO TRADES")

# Check what symbols are being traded
print("\n"+"="*80)
print("SYMBOL ANALYSIS:")
print("-"*50)
standalone_symbols = set(standalone['symbol'].unique())
combined_symbols = set(combined['symbol'].unique())

print(f"Standalone trades these symbols: {sorted(standalone_symbols)}")
print(f"Combined trades these symbols: {sorted(combined_symbols)}")
print(f"Combined-only symbols: {sorted(combined_symbols - standalone_symbols)}")

# These are defensive/panic assets
panic_assets = combined_symbols - standalone_symbols
print(f"\nDEFENSIVE/PANIC ASSETS: {sorted(panic_assets)}")
print("These are being traded during panic mode, causing the divergence!")