"""Debug data preparation pipeline."""
import pandas as pd
from pathlib import Path

# Load cached data
cache_file = Path('production/local_data/equities/SPY_1D.parquet')
df = pd.read_parquet(cache_file)

print("=== Original cached data ===")
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"Index: {df.index[:3]}")
print(f"Data:\n{df.head()}")

# Rename columns
df.rename(columns={
    'open': 'Open',
    'high': 'High',
    'low': 'Low',
    'close': 'Close',
    'volume': 'Volume'
}, inplace=True)

print("\n=== After column rename ===")
print(f"Columns: {list(df.columns)}")

# Filter date range (last 250 days)
from datetime import datetime, timedelta
end_date = datetime.now().replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
start_date = end_date - timedelta(days=250)

print(f"\n=== Date filtering ===")
print(f"Start: {start_date}")
print(f"End: {end_date}")
print(f"Index is tz-aware: {df.index.tz is not None}")
print(f"Index type: {type(df.index)}")

# Make datetimes timezone-aware for comparison
if df.index.tz is None:
    df.index = df.index.tz_localize('UTC')

start_date = pd.Timestamp(start_date, tz='UTC')
end_date = pd.Timestamp(end_date, tz='UTC')

df_filtered = df[(df.index >= start_date) & (df.index <= end_date)]
print(f"After date filter: {len(df_filtered)} bars")

# Compute MA_200
df_filtered['MA_200'] = df_filtered['Close'].rolling(window=200).mean()

print(f"\n=== After MA_200 calculation ===")
print(f"MA_200 non-null count: {df_filtered['MA_200'].notna().sum()}")
print(f"Last 5 MA_200 values:\n{df_filtered['MA_200'].tail()}")

# Apply dropna
df_final = df_filtered.dropna(subset=['Close', 'MA_200'], how='any')
print(f"\n=== After dropna(subset=['Close', 'MA_200']) ===")
print(f"Final shape: {df_final.shape}")
print(f"Remaining bars: {len(df_final)}")
if len(df_final) > 0:
    print(f"Date range: {df_final.index[0]} to {df_final.index[-1]}")
