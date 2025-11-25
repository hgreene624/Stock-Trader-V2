#!/usr/bin/env python3
"""
Test script for AdaptiveRegimeSwitcher_v1
"""

import sys
import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/Users/holdengreene/PycharmProjects/Stock-Trader-V2')

from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from models.base import Context, RegimeState

def load_data(symbol, start_date, end_date):
    """Load data for a symbol."""
    try:
        data = pd.read_parquet(f'/Users/holdengreene/PycharmProjects/Stock-Trader-V2/data/equities/{symbol}_1D.parquet')
        # Filter date range
        data = data[start_date:end_date]
        # Rename columns to lowercase
        data.columns = [c.lower() for c in data.columns]
        return data
    except Exception as e:
        print(f"Error loading {symbol}: {e}")
        return None

def main():
    print("Testing AdaptiveRegimeSwitcher_v1")
    print("="*60)

    # Create model
    model = AdaptiveRegimeSwitcher_v1()
    print(f"Model created: {model}")
    print(f"Universe: {model.universe}")
    print()

    # Test period: COVID crash
    start_date = '2020-02-01'
    end_date = '2020-04-30'

    # Load data for key symbols
    print("Loading data...")
    vix_data = load_data('^VIX', start_date, end_date)
    spy_data = load_data('SPY', start_date, end_date)
    tlt_data = load_data('TLT', start_date, end_date)

    if vix_data is None or spy_data is None:
        print("Failed to load required data")
        return

    print(f"VIX data: {len(vix_data)} days")
    print(f"SPY data: {len(spy_data)} days")
    print(f"TLT data: {len(tlt_data)} days")
    print()

    # Test a few key dates
    test_dates = [
        ('2020-02-20', 'Pre-crash'),
        ('2020-03-12', 'Crash begins'),
        ('2020-03-18', 'Peak panic'),
        ('2020-04-01', 'Recovery begins')
    ]

    for date_str, description in test_dates:
        date = pd.Timestamp(date_str, tz='UTC')

        # Get VIX level for this date
        vix_val = None
        if date in vix_data.index:
            vix_val = vix_data.loc[date, 'close']
        else:
            # Find closest date
            closest_idx = vix_data.index.get_indexer([date], method='nearest')[0]
            if closest_idx >= 0:
                vix_val = vix_data.iloc[closest_idx]['close']

        if vix_val is None:
            print(f"{date_str} ({description}): No VIX data")
            continue

        print(f"{date_str} ({description}): VIX={vix_val:.2f}")

        # Create minimal context
        asset_features = {
            '^VIX': pd.DataFrame({'close': [vix_val]}, index=[date]),
            'SPY': pd.DataFrame({'close': [100.0]}, index=[date])
        }

        regime = RegimeState(
            timestamp=date,
            equity_regime='bear' if vix_val > 30 else 'bull',
            vol_regime='high' if vix_val > 30 else 'normal',
            crypto_regime='neutral',
            macro_regime='neutral'
        )

        context = Context(
            timestamp=date,
            asset_features=asset_features,
            regime=regime,
            model_budget_fraction=1.0,
            model_budget_value=Decimal('100000')
        )

        try:
            # Get model output
            output = model.generate_target_weights(context)
            weights_str = ', '.join([f"{k}={v:.2f}" for k, v in sorted(output.weights.items(), key=lambda x: -x[1])[:3]])
            print(f"  → Weights: {weights_str}")
        except Exception as e:
            print(f"  → Error: {e}")

        print()

if __name__ == '__main__':
    main()