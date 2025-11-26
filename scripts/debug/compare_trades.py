import pandas as pd
import numpy as np

# Load both trade files
standalone = pd.read_csv('results/analysis/20251125_120208/trades.csv')
combined = pd.read_csv('results/analysis/20251125_145000/trades.csv')

# Convert timestamps
standalone['timestamp'] = pd.to_datetime(standalone['timestamp'])
combined['timestamp'] = pd.to_datetime(combined['timestamp'])

# Group by date and compare
standalone['date'] = standalone['timestamp'].dt.date
combined['date'] = combined['timestamp'].dt.date

print('Comparing trades grouped by date:')
print('='*80)

# Get unique dates
all_dates = sorted(set(standalone['date'].unique()) | set(combined['date'].unique()))

differences = []
for date in all_dates[:30]:  # Check first 30 trading days
    s_trades = standalone[standalone['date'] == date].sort_values(['symbol', 'quantity'])
    c_trades = combined[combined['date'] == date].sort_values(['symbol', 'quantity'])

    # Create signature for comparison
    s_sig = set(zip(s_trades['symbol'], s_trades['quantity'].round(0).astype(int)))
    c_sig = set(zip(c_trades['symbol'], c_trades['quantity'].round(0).astype(int)))

    if s_sig != c_sig:
        print(f'\nDATE: {date} - TRADES DIFFER!')
        print(f'  Standalone has: {sorted(s_sig)}')
        print(f'  Combined has:   {sorted(c_sig)}')

        # Find what's different
        only_in_standalone = s_sig - c_sig
        only_in_combined = c_sig - s_sig
        if only_in_standalone:
            print(f'  Only in standalone: {only_in_standalone}')
        if only_in_combined:
            print(f'  Only in combined:   {only_in_combined}')
        differences.append(date)
    else:
        print(f'DATE: {date} - Trades match (just different order)')

print(f'\n\nTotal dates with different trades in first 30 days: {len(differences)}')
print(f'Total standalone trades: {len(standalone)}')
print(f'Total combined trades: {len(combined)}')
print(f'Difference in trade count: {len(combined) - len(standalone)}')