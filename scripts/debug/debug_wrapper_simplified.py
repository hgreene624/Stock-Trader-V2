"""
Simplified debug to understand wrapper vs standalone differences
"""

import pandas as pd
import numpy as np
from decimal import Decimal
from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from models.sector_rotation_adaptive_v3 import SectorRotationAdaptive_v3
from models.base import Context, RegimeState
from backtest.runner import BacktestRunner
from engines.data.pipeline import DataPipeline
import sys

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

# Initialize data pipeline
pipeline = DataPipeline()

# Load data for the model universe
print("Loading data...")
symbols = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE', 'TLT', '^VIX']
asset_data = {}
for symbol in symbols:
    try:
        df = pipeline.load_parquet_data(f'data/equities/{symbol}_1D.parquet')
        asset_data[symbol] = df
    except:
        print(f"Warning: Could not load {symbol}")

# Get common timestamps for testing
timestamps = pipeline.get_common_timestamps(asset_data, start_date='2020-06-01', end_date='2020-08-31')
print(f"\nFound {len(timestamps)} common timestamps")

if len(timestamps) < 10:
    print("Insufficient data. Adjusting to 2024...")
    timestamps = pipeline.get_common_timestamps(asset_data, start_date='2024-06-01', end_date='2024-08-31')
    print(f"Now found {len(timestamps)} common timestamps")

# Track outputs
wrapper_outputs = []
standalone_outputs = []
wrapper_exposures = {}
standalone_exposures = {}

# Process first 20 timestamps
for i, timestamp in enumerate(timestamps[:20]):
    # Create asset features for context
    asset_features = {}
    for symbol, df in asset_data.items():
        # Get data up to current timestamp
        historical = df[df.index <= timestamp].tail(200)
        asset_features[symbol] = historical

    # Create regime state
    regime = RegimeState(
        timestamp=timestamp,
        equity_regime='bull',
        vol_regime='normal',
        crypto_regime='neutral',
        macro_regime='neutral'
    )

    # Create contexts
    wrapper_context = Context(
        timestamp=timestamp,
        asset_features=asset_features,
        regime=regime,
        model_budget_fraction=1.0,
        model_budget_value=Decimal('100000'),
        current_exposures=wrapper_exposures.copy()
    )

    # For standalone, remove VIX from features
    standalone_features = {k: v for k, v in asset_features.items() if k != '^VIX'}
    standalone_context = Context(
        timestamp=timestamp,
        asset_features=standalone_features,
        regime=regime,
        model_budget_fraction=1.0,
        model_budget_value=Decimal('100000'),
        current_exposures=standalone_exposures.copy()
    )

    # Generate outputs
    try:
        wrapper_output = wrapper.generate_target_weights(wrapper_context)
        standalone_output = standalone.generate_target_weights(standalone_context)
    except Exception as e:
        print(f"Error at {timestamp}: {e}")
        continue

    # Update exposures
    wrapper_exposures = wrapper_output.weights.copy()
    standalone_exposures = standalone_output.weights.copy()

    # Store results
    wrapper_outputs.append({
        'timestamp': timestamp,
        'weights': wrapper_output.weights,
        'hold_current': wrapper_output.hold_current,
        'total_weight': sum(wrapper_output.weights.values())
    })

    standalone_outputs.append({
        'timestamp': timestamp,
        'weights': standalone_output.weights,
        'hold_current': standalone_output.hold_current,
        'total_weight': sum(standalone_output.weights.values())
    })

    # Print comparison for interesting differences
    if i < 5 or abs(sum(wrapper_output.weights.values()) - sum(standalone_output.weights.values())) > 0.1:
        print(f"\n{timestamp}:")
        print(f"  Wrapper: {sorted(wrapper_output.weights.keys())} (total: {sum(wrapper_output.weights.values()):.3f}, hold: {wrapper_output.hold_current})")
        print(f"  Standalone: {sorted(standalone_output.weights.keys())} (total: {sum(standalone_output.weights.values()):.3f}, hold: {standalone_output.hold_current})")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Count differences
differences = 0
for w_out, s_out in zip(wrapper_outputs, standalone_outputs):
    if sorted(w_out['weights'].keys()) != sorted(s_out['weights'].keys()):
        differences += 1
    elif abs(w_out['total_weight'] - s_out['total_weight']) > 0.01:
        differences += 1

print(f"Position differences: {differences}/{len(wrapper_outputs)}")

# Check average leverage
wrapper_avg_leverage = np.mean([o['total_weight'] for o in wrapper_outputs if o['total_weight'] > 0])
standalone_avg_leverage = np.mean([o['total_weight'] for o in standalone_outputs if o['total_weight'] > 0])

print(f"\nWrapper avg leverage: {wrapper_avg_leverage:.3f}")
print(f"Standalone avg leverage: {standalone_avg_leverage:.3f}")

# Check which bull model instance is being used
print(f"\nWrapper bull model object id: {id(wrapper.bull_model)}")
print(f"Standalone model object id: {id(standalone)}")
print(f"Are they the same object? {wrapper.bull_model is standalone}")

# Check if state is persisting
print(f"\nWrapper bull model last_rebalance: {wrapper.bull_model.last_rebalance}")
print(f"Standalone last_rebalance: {standalone.last_rebalance}")
print(f"\nWrapper bull model entry_prices: {wrapper.bull_model.entry_prices}")
print(f"Standalone entry_prices: {standalone.entry_prices}")