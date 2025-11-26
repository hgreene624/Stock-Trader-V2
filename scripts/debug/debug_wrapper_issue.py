"""
Debug script to identify why AdaptiveRegimeSwitcher underperforms standalone SectorRotationAdaptive_v3
"""

import pandas as pd
import numpy as np
from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from models.sector_rotation_adaptive_v3 import SectorRotationAdaptive_v3
from models.base import Context, RegimeState
from decimal import Decimal

# Load data
print("Loading data...")
xlk_df = pd.read_parquet('data/equities/XLK_4H.parquet')
xlf_df = pd.read_parquet('data/equities/XLF_4H.parquet')
xlv_df = pd.read_parquet('data/equities/XLV_4H.parquet')
xlc_df = pd.read_parquet('data/equities/XLC_4H.parquet')
tlt_df = pd.read_parquet('data/equities/TLT_4H.parquet')
vix_df = pd.read_parquet('data/equities/^VIX_1D.parquet')

# Initialize models
print("\nInitializing models...")
wrapper = AdaptiveRegimeSwitcher_v1()
standalone = SectorRotationAdaptive_v3(
    atr_period=21,
    stop_loss_atr_mult=1.6,
    take_profit_atr_mult=2.48,
    min_hold_days=2,
    bull_leverage=2.0,
    bear_leverage=1.38,
    bull_momentum_period=126,
    bear_momentum_period=126,
    bull_top_n=3,
    bear_top_n=3,
    bull_min_momentum=0.0,
    bear_min_momentum=0.0
)

# Test date range - use 4H frequency since we're using 4H data
test_dates = pd.date_range('2020-06-01', '2020-08-31', freq='4h', tz='UTC')

# Track outputs
wrapper_outputs = []
standalone_outputs = []
wrapper_trades = 0
standalone_trades = 0

# Track exposures for both models
wrapper_exposures = {}
standalone_exposures = {}

print(f"\nTesting period: {test_dates[0]} to {test_dates[-1]}")
print("=" * 80)

for date in test_dates:
    # Filter data up to current date
    asset_features = {
        'XLK': xlk_df[xlk_df.index <= date].tail(200),
        'XLF': xlf_df[xlf_df.index <= date].tail(200),
        'XLV': xlv_df[xlv_df.index <= date].tail(200),
        'XLC': xlc_df[xlc_df.index <= date].tail(200),
        'TLT': tlt_df[tlt_df.index <= date].tail(200),
        '^VIX': vix_df[vix_df.index <= date].tail(200)
    }

    # Skip if insufficient data
    if any(len(df) < 150 for df in asset_features.values()):
        continue

    # Create context for wrapper
    wrapper_context = Context(
        timestamp=date,
        asset_features=asset_features,
        regime=RegimeState(
            timestamp=date,
            equity_regime='bull',
            vol_regime='normal',
            crypto_regime='neutral',
            macro_regime='neutral'
        ),
        model_budget_fraction=1.0,
        model_budget_value=Decimal('100000'),
        current_exposures=wrapper_exposures.copy()
    )

    # Create context for standalone (without VIX in features)
    standalone_features = {k: v for k, v in asset_features.items() if k != '^VIX'}
    standalone_context = Context(
        timestamp=date,
        asset_features=standalone_features,
        regime=RegimeState(
            timestamp=date,
            equity_regime='bull',
            vol_regime='normal',
            crypto_regime='neutral',
            macro_regime='neutral'
        ),
        model_budget_fraction=1.0,
        model_budget_value=Decimal('100000'),
        current_exposures=standalone_exposures.copy()
    )

    # Get outputs
    wrapper_output = wrapper.generate_target_weights(wrapper_context)
    standalone_output = standalone.generate_target_weights(standalone_context)

    # Count trades (position changes)
    if wrapper_output.weights != wrapper_exposures:
        wrapper_trades += sum(1 for k in set(wrapper_output.weights) | set(wrapper_exposures)
                             if wrapper_output.weights.get(k, 0) != wrapper_exposures.get(k, 0))
        wrapper_exposures = wrapper_output.weights.copy()

    if standalone_output.weights != standalone_exposures:
        standalone_trades += sum(1 for k in set(standalone_output.weights) | set(standalone_exposures)
                               if standalone_output.weights.get(k, 0) != standalone_exposures.get(k, 0))
        standalone_exposures = standalone_output.weights.copy()

    # Store outputs
    wrapper_outputs.append({
        'date': date,
        'weights': wrapper_output.weights,
        'hold_current': wrapper_output.hold_current,
        'total_weight': sum(wrapper_output.weights.values())
    })

    standalone_outputs.append({
        'date': date,
        'weights': standalone_output.weights,
        'hold_current': standalone_output.hold_current,
        'total_weight': sum(standalone_output.weights.values())
    })

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Compare outputs
print(f"\nWrapper trades: {wrapper_trades}")
print(f"Standalone trades: {standalone_trades}")
print(f"Trade ratio: {wrapper_trades/standalone_trades if standalone_trades > 0 else 0:.2f}")

# Analyze leverage usage
wrapper_avg_leverage = np.mean([o['total_weight'] for o in wrapper_outputs])
standalone_avg_leverage = np.mean([o['total_weight'] for o in standalone_outputs])

print(f"\nWrapper avg leverage: {wrapper_avg_leverage:.3f}")
print(f"Standalone avg leverage: {standalone_avg_leverage:.3f}")

# Check position consistency
print("\nFirst 10 days comparison:")
for i in range(min(10, len(wrapper_outputs))):
    w_out = wrapper_outputs[i]
    s_out = standalone_outputs[i]

    w_symbols = sorted(w_out['weights'].keys())
    s_symbols = sorted(s_out['weights'].keys())

    w_total = w_out['total_weight']
    s_total = s_out['total_weight']

    if w_symbols != s_symbols or abs(w_total - s_total) > 0.01:
        print(f"{w_out['date'].date()}:")
        print(f"  Wrapper: {w_symbols} (total: {w_total:.3f}, hold: {w_out['hold_current']})")
        print(f"  Standalone: {s_symbols} (total: {s_total:.3f}, hold: {s_out['hold_current']})")

# Check last rebalance tracking
print(f"\nWrapper last_rebalance: {wrapper.bull_model.last_rebalance}")
print(f"Standalone last_rebalance: {standalone.last_rebalance}")

print(f"\nWrapper entry_prices: {len(wrapper.bull_model.entry_prices)} entries")
print(f"Standalone entry_prices: {len(standalone.entry_prices)} entries")