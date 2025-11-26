#!/usr/bin/env python3
"""
Quick test to identify VIX data loading issue
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
import yaml
import tempfile

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from models.sector_rotation_adaptive_v3 import SectorRotationAdaptive_v3
from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from backtest.runner import BacktestRunner


def test_vix_loading():
    """Test if VIX is being loaded properly in backtest"""

    print("="*60)
    print("TESTING VIX DATA LOADING")
    print("="*60)

    # Create config with VIX included
    base_config = {
        'mode': 'backtest',
        'data': {
            'base_path': 'data',
            'assets': {
                'equity': {
                    'symbols': ['^VIX', 'SPY', 'QQQ', 'TLT', 'XLK', 'XLF'],
                    'timeframe': '1D'
                }
            }
        },
        'models': {
            'model_1': {
                'enabled': True,
                'model_class': 'AdaptiveRegimeSwitcher_v1',
                'budget_allocation': 1.0,
                'parameters': {}
            }
        },
        'portfolio': {
            'initial_capital': 100000.0,
            'max_leverage': 2.0
        },
        'execution': {
            'commission_rate': 0.001,
            'slippage_rate': 0.0005
        },
        'risk': {
            'per_asset_max': 0.4,
            'per_asset_class_max': {'equity': 2.0},
            'max_leverage': 2.0,
            'circuit_breaker': {
                'drawdown_threshold': 0.15,
                'halt_duration_bars': 10
            }
        },
        'regime': {
            'detection_enabled': False
        }
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(base_config, f)
        temp_config_path = f.name

    # Initialize model
    model = AdaptiveRegimeSwitcher_v1()

    # Create runner
    runner = BacktestRunner(temp_config_path)

    # Run for just March 2020 (COVID crash)
    print("\nRunning backtest for March 2020 (COVID crash period)...")
    print("Expected: VIX should spike to 80+ during this period")

    results = runner.run(
        model=model,
        start_date="2020-03-01",
        end_date="2020-03-31"
    )

    print("\nRESULTS:")
    if results and 'metrics' in results:
        metrics = results['metrics']
        print(f"CAGR: {metrics.get('cagr', 0) * 100:.2f}%")
        print(f"Trades: {metrics.get('total_trades', 0)}")

    # Clean up
    import os
    try:
        os.unlink(temp_config_path)
    except:
        pass

    print("\n" + "="*60)
    print("CHECK THE OUTPUT ABOVE:")
    print("- If VIX is always 0.00, we have a data loading issue")
    print("- If VIX shows real values (should be 40-80 in March 2020)")
    print("  then the regime detection should work properly")
    print("="*60)


if __name__ == "__main__":
    test_vix_loading()