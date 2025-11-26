#!/usr/bin/env python3
"""
Test AdaptiveRegimeSwitcher during March 2020 COVID crash
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

from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from backtest.runner import BacktestRunner


def test_march_2020():
    """Test regime switching during March 2020"""

    print("="*80)
    print("TESTING MARCH 2020 REGIME SWITCHING")
    print("="*80)
    print("VIX peaked at 82.69 on March 16, 2020")
    print("AdaptiveRegimeSwitcher should switch to panic mode (BearDipBuyer)")
    print("="*80)

    # Create config
    base_config = {
        'mode': 'backtest',
        'data': {
            'base_path': 'data',
            'assets': {
                'equity': {
                    'symbols': ['SPY', 'QQQ', 'TLT', 'GLD', 'UUP', 'SHY',
                              'XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLP',
                              'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'],
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
        },
        'system': {
            'reference_assets': [
                {'symbol': '^VIX', 'required': False},
                {'symbol': 'SPY', 'required': True}
            ]
        }
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(base_config, f)
        temp_config_path = f.name

    # Initialize model with lower thresholds to ensure switching
    model = AdaptiveRegimeSwitcher_v1(
        vix_extreme_panic=35.0,   # VIX > 35: 100% panic
        vix_elevated_panic=30.0,   # VIX > 30: blend
        vix_normal=25.0           # VIX < 25: bull
    )

    # Create runner
    runner = BacktestRunner(temp_config_path)

    # Run for March 2020 only
    print("\nRunning backtest for March 2020...")
    results = runner.run(
        model=model,
        start_date="2020-03-01",
        end_date="2020-03-31"
    )

    print("\n" + "="*80)
    print("RESULTS:")
    if results and 'metrics' in results:
        metrics = results['metrics']
        print(f"CAGR: {metrics.get('cagr', 0) * 100:.2f}%")
        print(f"Total Return: {metrics.get('total_return', 0) * 100:.2f}%")
        print(f"Trades: {metrics.get('total_trades', 0)}")
        print(f"Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%")

    # Clean up
    import os
    try:
        os.unlink(temp_config_path)
    except:
        pass

    print("\n" + "="*80)
    print("EXPECTED BEHAVIOR:")
    print("- Early March: VIX 30-40 → ELEVATED mode (blend)")
    print("- Mid March: VIX 50-82 → EXTREME mode (100% BearDipBuyer)")
    print("- Late March: VIX 60-65 → Still EXTREME mode")
    print("="*80)


if __name__ == "__main__":
    test_march_2020()