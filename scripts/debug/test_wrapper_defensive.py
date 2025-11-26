"""
Test why AdaptiveRegimeSwitcher goes defensive at the start
"""

import pandas as pd
from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from models.sector_rotation_adaptive_v3 import SectorRotationAdaptive_v3
from models.base import Context, RegimeState
from decimal import Decimal

print("Testing why wrapper goes defensive...")
print("=" * 80)

# Initialize wrapper
wrapper = AdaptiveRegimeSwitcher_v1()

# Load minimal data for testing (early 2020)
test_date = pd.Timestamp('2020-01-15', tz='UTC')

# Load sector data
sectors = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE']
asset_features = {}

for sector in sectors:
    df = pd.read_parquet(f'data/equities/{sector}_1D.parquet')
    # Set timestamp as index
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    # Get data up to test date
    df = df[df.index <= test_date]
    if len(df) > 0:
        asset_features[sector] = df.tail(200)  # Get last 200 bars
        print(f"{sector}: {len(asset_features[sector])} bars available")

# Add TLT
df = pd.read_parquet('data/equities/TLT_1D.parquet')
if 'timestamp' in df.columns:
    df = df.set_index('timestamp')
df = df[df.index <= test_date]
if len(df) > 0:
    asset_features['TLT'] = df.tail(200)
    print(f"TLT: {len(asset_features['TLT'])} bars available")

# Add VIX
df = pd.read_parquet('data/equities/^VIX_1D.parquet')
df = df[df.index <= test_date] if hasattr(df.index, '__len__') else df[:0]
if len(df) > 0:
    asset_features['^VIX'] = df.tail(200)
    print(f"^VIX: {len(asset_features['^VIX'])} bars available")

print(f"\nTotal symbols with data: {len(asset_features)}")

# Create context
context = Context(
    timestamp=test_date,
    asset_features=asset_features,
    regime=RegimeState(
        timestamp=test_date,
        equity_regime='bull',
        vol_regime='normal',
        crypto_regime='neutral',
        macro_regime='neutral'
    ),
    model_budget_fraction=1.0,
    model_budget_value=Decimal('100000'),
    current_exposures={}
)

# Get wrapper output
print("\n" + "=" * 80)
print("WRAPPER OUTPUT:")
try:
    wrapper_output = wrapper.generate_target_weights(context)
    print(f"Weights: {wrapper_output.weights}")
    print(f"Hold current: {wrapper_output.hold_current}")
    print(f"Total weight: {sum(wrapper_output.weights.values()):.3f}")
except Exception as e:
    print(f"Error: {e}")

# Now test the bull model directly with same context
print("\n" + "=" * 80)
print("DIRECT BULL MODEL OUTPUT:")
bull_model = wrapper.bull_model

# Remove VIX for direct bull model test
bull_features = {k: v for k, v in asset_features.items() if k != '^VIX'}
bull_context = Context(
    timestamp=test_date,
    asset_features=bull_features,
    regime=context.regime,
    model_budget_fraction=1.0,
    model_budget_value=Decimal('100000'),
    current_exposures={}
)

try:
    bull_output = bull_model.generate_target_weights(bull_context)
    print(f"Weights: {bull_output.weights}")
    print(f"Hold current: {bull_output.hold_current}")
    print(f"Total weight: {sum(bull_output.weights.values()):.3f}")
except Exception as e:
    print(f"Error: {e}")

# Check momentum calculations
print("\n" + "=" * 80)
print("MOMENTUM CHECK:")
for sector in sectors[:5]:  # Check first 5 sectors
    if sector in asset_features:
        df = asset_features[sector]
        if len(df) >= 127:  # Need 126 + 1 for momentum calculation
            close_col = 'Close' if 'Close' in df.columns else 'close'
            current_price = df[close_col].iloc[-1]
            past_price = df[close_col].iloc[-127]
            momentum = (current_price - past_price) / past_price
            print(f"{sector}: current={current_price:.2f}, past={past_price:.2f}, momentum={momentum:.3f}")
        else:
            print(f"{sector}: insufficient data for momentum (need 127, have {len(df)})")