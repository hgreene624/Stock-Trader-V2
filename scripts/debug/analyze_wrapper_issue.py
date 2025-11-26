"""
Analyze why AdaptiveRegimeSwitcher underperforms standalone SectorRotationAdaptive
"""

import json
import pandas as pd
import numpy as np

# Read the metadata from recent runs
wrapper_dir = "results/analysis/20251125_121510"  # exp014_combined_2020_2024
standalone_dir = "results/analysis/20251125_121453"  # ea_optimized_atr

print("=" * 80)
print("WRAPPER vs STANDALONE ANALYSIS")
print("=" * 80)

# Load trade logs
wrapper_trades = pd.read_csv(f"{wrapper_dir}/trades.csv")
standalone_trades = pd.read_csv(f"{standalone_dir}/trades.csv")

print(f"\nTrade counts:")
print(f"  Wrapper: {len(wrapper_trades)} trades")
print(f"  Standalone: {len(standalone_trades)} trades")
print(f"  Ratio: {len(wrapper_trades)/len(standalone_trades):.2f}x")

# Load performance logs (NAV series)
wrapper_perf = pd.read_csv(f"{wrapper_dir}/nav_series.csv")
standalone_perf = pd.read_csv(f"{standalone_dir}/nav_series.csv")

# Convert timestamps
wrapper_perf['timestamp'] = pd.to_datetime(wrapper_perf['timestamp'])
standalone_perf['timestamp'] = pd.to_datetime(standalone_perf['timestamp'])

# Calculate returns
wrapper_returns = wrapper_perf['nav'].pct_change().dropna()
standalone_returns = standalone_perf['nav'].pct_change().dropna()

print(f"\nReturn statistics:")
print(f"  Wrapper mean return: {wrapper_returns.mean():.5f}")
print(f"  Standalone mean return: {standalone_returns.mean():.5f}")
print(f"  Wrapper volatility: {wrapper_returns.std():.5f}")
print(f"  Standalone volatility: {standalone_returns.std():.5f}")

# Load metadata
with open(f"{wrapper_dir}/metadata.json") as f:
    wrapper_meta = json.load(f)

with open(f"{standalone_dir}/metadata.json") as f:
    standalone_meta = json.load(f)

print(f"\nMetrics comparison:")
print(f"  CAGR: Wrapper={wrapper_meta['metrics']['cagr']:.2%} vs Standalone={standalone_meta['metrics']['cagr']:.2%}")
print(f"  Sharpe: Wrapper={wrapper_meta['metrics']['sharpe_ratio']:.3f} vs Standalone={standalone_meta['metrics']['sharpe_ratio']:.3f}")
print(f"  Max DD: Wrapper={wrapper_meta['metrics']['max_drawdown']:.2%} vs Standalone={standalone_meta['metrics']['max_drawdown']:.2%}")
print(f"  Win Rate: Wrapper={wrapper_meta['metrics']['win_rate']:.2%} vs Standalone={standalone_meta['metrics']['win_rate']:.2%}")

# Analyze trading frequency
wrapper_trades['timestamp'] = pd.to_datetime(wrapper_trades['timestamp'])
standalone_trades['timestamp'] = pd.to_datetime(standalone_trades['timestamp'])

# Group by month
wrapper_monthly = wrapper_trades.set_index('timestamp').resample('M').size()
standalone_monthly = standalone_trades.set_index('timestamp').resample('M').size()

print(f"\nAverage trades per month:")
print(f"  Wrapper: {wrapper_monthly.mean():.1f}")
print(f"  Standalone: {standalone_monthly.mean():.1f}")

# Analyze position sizes
print(f"\nPosition sizes (quantity):")
print(f"  Wrapper mean: {wrapper_trades['quantity'].mean():.0f} shares")
print(f"  Standalone mean: {standalone_trades['quantity'].mean():.0f} shares")
print(f"  Wrapper median: {wrapper_trades['quantity'].median():.0f} shares")
print(f"  Standalone median: {standalone_trades['quantity'].median():.0f} shares")

# Analyze symbols traded
wrapper_symbols = wrapper_trades['symbol'].value_counts()
standalone_symbols = standalone_trades['symbol'].value_counts()

print(f"\nTop symbols traded:")
print("  Wrapper:")
for sym, count in wrapper_symbols.head(5).items():
    print(f"    {sym}: {count} trades ({100*count/len(wrapper_trades):.1f}%)")

print("  Standalone:")
for sym, count in standalone_symbols.head(5).items():
    print(f"    {sym}: {count} trades ({100*count/len(standalone_trades):.1f}%)")

# Check for defensive asset usage
tlt_wrapper = (wrapper_trades['symbol'] == 'TLT').sum()
tlt_standalone = (standalone_trades['symbol'] == 'TLT').sum()

print(f"\nDefensive asset (TLT) usage:")
print(f"  Wrapper: {tlt_wrapper} trades ({100*tlt_wrapper/len(wrapper_trades):.1f}%)")
print(f"  Standalone: {tlt_standalone} trades ({100*tlt_standalone/len(standalone_trades):.1f}%)")

# Analyze trade timing
print(f"\nFirst trade dates:")
print(f"  Wrapper: {wrapper_trades['timestamp'].min()}")
print(f"  Standalone: {standalone_trades['timestamp'].min()}")

print(f"\nLast trade dates:")
print(f"  Wrapper: {wrapper_trades['timestamp'].max()}")
print(f"  Standalone: {standalone_trades['timestamp'].max()}")

# Analyze trade clustering
wrapper_trades['date'] = wrapper_trades['timestamp'].dt.date
standalone_trades['date'] = standalone_trades['timestamp'].dt.date

wrapper_daily_counts = wrapper_trades.groupby('date').size()
standalone_daily_counts = standalone_trades.groupby('date').size()

print(f"\nTrade clustering:")
print(f"  Wrapper max trades in a day: {wrapper_daily_counts.max()}")
print(f"  Standalone max trades in a day: {standalone_daily_counts.max()}")
print(f"  Wrapper avg trades per trading day: {wrapper_daily_counts.mean():.2f}")
print(f"  Standalone avg trades per trading day: {standalone_daily_counts.mean():.2f}")