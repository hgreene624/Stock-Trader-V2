#!/usr/bin/env python3
"""
Comprehensive Validation Suite for AdaptiveRegimeSwitcher_v1

PURPOSE: Systematically identify why AdaptiveRegimeSwitcher underperforms when it
SHOULD beat both constituent models by combining their strengths.

LOGIC VIOLATION:
- Model A (SectorRotation): 15.11% CAGR in bull markets
- Model B (BearDipBuyer): Profitable during crashes
- Combined: Use A when VIX < 30, B when VIX > 30
- Expected: Combined ≥ max(A, B) across all conditions
- Actual: Combined = 8.58% CAGR (worse than both!)

EXPERIMENTS:
1. Trivial Passthrough - Verify backtest engine works
2. Forced Bull Mode - Test wrapper with VIX=999 threshold
3. Forced Panic Mode - Test wrapper with VIX=0 threshold
4. Manual Regime Split - Calculate theoretical best performance
5. Data Comparison - Verify same data seen by both
6. Trade-by-Trade Comparison - Find exact divergence point
7. Commission Audit - Why different commission per trade?
8. Hold Current Flag Audit - Is hold_current working?
9. State Persistence Check - Does model state persist?
10. VIX Detection Audit - Is regime detection correct?

Author: AI Agent
Date: 2025-11-25
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from models.base import BaseModel, Context, ModelOutput
from models.sector_rotation_adaptive_v3 import SectorRotationAdaptive_v3
from models.beardipbuyer_v1 import BearDipBuyer_v1
from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from backtest.runner import BacktestRunner


class ValidationResult:
    """Container for validation test results."""

    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.passed = False
        self.cagr = 0.0
        self.sharpe = 0.0
        self.max_dd = 0.0
        self.total_return = 0.0
        self.num_trades = 0
        self.commissions = 0.0
        self.notes = []
        self.data = {}

    def __str__(self):
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        return f"""
{self.experiment_name}
{'='*60}
Status: {status}
CAGR: {self.cagr:.2f}%
Sharpe: {self.sharpe:.2f}
Max DD: {self.max_dd:.2f}%
Total Return: {self.total_return:.2f}%
Trades: {self.num_trades}
Commissions: ${self.commissions:,.0f}
Notes: {'; '.join(self.notes)}
"""


# =============================================================================
# EXPERIMENT 1: Trivial Passthrough
# =============================================================================

class TrivialPassthrough_v1(BaseModel):
    """
    Trivial wrapper that just passes through SectorRotation 100% of the time.

    PURPOSE: Verify backtest engine works correctly with wrappers.
    EXPECTED: Should match standalone SectorRotation EXACTLY (15.11% CAGR).
    """

    def __init__(self):
        # Set model_id first
        self.model_id = "TrivialPassthrough_v1"

        # Initialize the bull model with exact same parameters
        self.bull_model = SectorRotationAdaptive_v3(
            model_id="SectorRotation_Passthrough",
            atr_period=21,
            stop_loss_atr_mult=1.6,
            take_profit_atr_mult=2.48,
            min_hold_days=2,
            bull_leverage=2.0,
            bear_leverage=1.38,
            bull_momentum_period=126,
            bear_momentum_period=126,
            bull_top_n=4,
            bear_top_n=4,
            bull_min_momentum=0.10,
            bear_min_momentum=0.10
        )

        # Copy assets for compatibility
        self.assets = self.bull_model.assets
        self.all_assets = self.bull_model.all_assets

        super().__init__(
            name="TrivialPassthrough_v1",
            version="1.0.0",
            universe=self.all_assets
        )

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Simply pass through the bull model's output."""
        return self.bull_model.generate_target_weights(context)


# =============================================================================
# EXPERIMENT 2 & 3: Forced Modes
# =============================================================================

class ForcedBullMode_v1(BaseModel):
    """
    AdaptiveRegimeSwitcher with VIX thresholds set impossibly high.

    PURPOSE: Test wrapper with regime detection but FORCE bull mode only.
    EXPECTED: Should match standalone SectorRotation EXACTLY.
    """

    def __init__(self):
        # Set model_id first
        self.model_id = "ForcedBullMode_v1"

        # Use AdaptiveRegimeSwitcher but force bull mode
        self.switcher = AdaptiveRegimeSwitcher_v1(
            model_id="ForcedBull",
            vix_extreme_panic=999.0,  # Impossible threshold
            vix_elevated_panic=999.0,
            vix_normal=999.0
        )

        self.assets = self.switcher.assets
        self.all_assets = self.switcher.all_assets

        super().__init__(
            name="ForcedBullMode_v1",
            version="1.0.0",
            universe=self.all_assets
        )

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Use the switcher which should always be in bull mode."""
        return self.switcher.generate_target_weights(context)


class ForcedPanicMode_v1(BaseModel):
    """
    AdaptiveRegimeSwitcher with VIX thresholds set impossibly low.

    PURPOSE: Test BearDipBuyer in isolation through wrapper.
    EXPECTED: Should match standalone BearDipBuyer performance.
    """

    def __init__(self):
        # Set model_id first
        self.model_id = "ForcedPanicMode_v1"

        # Use AdaptiveRegimeSwitcher but force panic mode
        self.switcher = AdaptiveRegimeSwitcher_v1(
            model_id="ForcedPanic",
            vix_extreme_panic=0.0,  # Always trigger
            vix_elevated_panic=0.0,
            vix_normal=0.0
        )

        self.assets = self.switcher.assets
        self.all_assets = self.switcher.all_assets

        super().__init__(
            name="ForcedPanicMode_v1",
            version="1.0.0",
            universe=self.all_assets
        )

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Use the switcher which should always be in panic mode."""
        return self.switcher.generate_target_weights(context)


# =============================================================================
# EXPERIMENT 5: Data Comparison Logger
# =============================================================================

class DataLogger_v1(BaseModel):
    """
    Wrapper that logs all data seen by the model for comparison.

    PURPOSE: Verify wrapper and standalone see the same data.
    """

    def __init__(self, base_model: BaseModel, log_file: str):
        self.model_id = f"DataLogger_{base_model.__class__.__name__}"
        self.base_model = base_model
        self.log_file = log_file
        self.assets = base_model.assets
        self.all_assets = getattr(base_model, 'all_assets', base_model.assets)

        super().__init__(
            name=f"DataLogger_{base_model.__class__.__name__}",
            version="1.0.0",
            universe=self.all_assets
        )

        # Initialize log
        self.log_data = []

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Log context data and pass through to base model."""
        # Log key data points
        log_entry = {
            'timestamp': str(context.timestamp),
            'nav': float(context.nav),
            'current_exposures': {k: float(v) for k, v in context.current_exposures.items()},
            'prices': {}
        }

        # Log prices for key assets
        for symbol in ['XLK', 'SPY', '^VIX']:
            if symbol in context.asset_features:
                features = context.asset_features[symbol]
                close_col = 'Close' if 'Close' in features.columns else 'close'
                if len(features) > 0:
                    log_entry['prices'][symbol] = float(features[close_col].iloc[-1])

        self.log_data.append(log_entry)

        # Save log periodically
        if len(self.log_data) % 100 == 0:
            with open(self.log_file, 'w') as f:
                json.dump(self.log_data, f, indent=2)

        # Pass through to base model
        return self.base_model.generate_target_weights(context)

    def __del__(self):
        """Save log on destruction."""
        if self.log_data:
            with open(self.log_file, 'w') as f:
                json.dump(self.log_data, f, indent=2)


# =============================================================================
# Main Validation Runner
# =============================================================================

def run_backtest(model: BaseModel, start_date: str, end_date: str,
                 experiment_name: str) -> ValidationResult:
    """
    Run a backtest and return validation results.
    """
    import yaml
    import tempfile
    from backtest.runner import BacktestRunner

    result = ValidationResult(experiment_name)

    try:
        # Create base configuration
        base_config = {
            'mode': 'backtest',
            'data': {
                'base_path': 'data',
                'assets': {
                    'equity': {
                        'symbols': ['SPY', 'QQQ', 'TLT', 'GLD', 'UUP', 'SHY',
                                  'XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLP',
                                  'XLU', 'XLY', 'XLC', 'XLB', 'XLRE', '^VIX'],
                        'timeframe': '1D'
                    }
                }
            },
            'models': {
                'model_1': {
                    'enabled': True,
                    'model_class': model.__class__.__name__,
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
                'per_asset_class_max': {'equity': 2.0, 'crypto': 0.2},
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

        # Create runner
        runner = BacktestRunner(temp_config_path)

        # Run backtest
        print(f"\n🔬 Running: {experiment_name}")
        print(f"   Period: {start_date} to {end_date}")

        results = runner.run(
            model=model,
            start_date=start_date,
            end_date=end_date
        )

        # Extract results
        if results and 'metrics' in results:
            metrics = results['metrics']
            result.cagr = metrics.get('cagr', 0.0) * 100
            result.sharpe = metrics.get('sharpe_ratio', 0.0)
            result.max_dd = metrics.get('max_drawdown', 0.0) * 100
            result.total_return = metrics.get('total_return', 0.0) * 100
            result.num_trades = metrics.get('total_trades', 0)
            result.commissions = metrics.get('total_commissions', 0.0)
            result.data = metrics

            # Log summary
            print(f"   CAGR: {result.cagr:.2f}%")
            print(f"   Sharpe: {result.sharpe:.2f}")
            print(f"   Trades: {result.num_trades}")

    except Exception as e:
        result.notes.append(f"Error: {str(e)}")
        print(f"   ❌ Error: {str(e)}")

    finally:
        # Cleanup temp file
        import os
        if 'temp_config_path' in locals():
            try:
                os.unlink(temp_config_path)
            except:
                pass

    return result


def validate_experiment_1():
    """
    EXPERIMENT 1: Trivial Passthrough

    Expected: Should match standalone SectorRotation EXACTLY
    """
    print("\n" + "="*80)
    print("EXPERIMENT 1: TRIVIAL PASSTHROUGH")
    print("="*80)
    print("Purpose: Verify backtest engine works with wrappers")
    print("Expected: Match standalone SectorRotation EXACTLY (15.11% CAGR)")

    # Run standalone SectorRotation
    standalone = SectorRotationAdaptive_v3()
    standalone_result = run_backtest(
        standalone,
        "2020-01-01",
        "2024-12-31",
        "Standalone SectorRotation"
    )

    # Run trivial passthrough
    passthrough = TrivialPassthrough_v1()
    passthrough_result = run_backtest(
        passthrough,
        "2020-01-01",
        "2024-12-31",
        "Trivial Passthrough"
    )

    # Compare results
    print("\n📊 COMPARISON:")
    print(f"Standalone CAGR: {standalone_result.cagr:.2f}%")
    print(f"Passthrough CAGR: {passthrough_result.cagr:.2f}%")
    print(f"Difference: {abs(standalone_result.cagr - passthrough_result.cagr):.2f}%")

    # Check if they match (within 0.1% tolerance for rounding)
    if abs(standalone_result.cagr - passthrough_result.cagr) < 0.1:
        print("✅ PASSED: Passthrough matches standalone!")
        passthrough_result.passed = True
    else:
        print("❌ FAILED: Results don't match - backtest engine bug!")
        passthrough_result.notes.append("Mismatch indicates backtest engine bug")

    return standalone_result, passthrough_result


def validate_experiment_2():
    """
    EXPERIMENT 2: Forced Bull Mode

    Expected: Should match standalone SectorRotation EXACTLY
    """
    print("\n" + "="*80)
    print("EXPERIMENT 2: FORCED BULL MODE")
    print("="*80)
    print("Purpose: Test wrapper with regime detection but FORCE bull mode")
    print("Expected: Match standalone SectorRotation EXACTLY")

    # Run forced bull mode
    forced_bull = ForcedBullMode_v1()
    forced_result = run_backtest(
        forced_bull,
        "2020-01-01",
        "2024-12-31",
        "Forced Bull Mode"
    )

    # Compare to standalone (from exp 1)
    standalone = SectorRotationAdaptive_v3()
    standalone_result = run_backtest(
        standalone,
        "2020-01-01",
        "2024-12-31",
        "Standalone Reference"
    )

    print("\n📊 COMPARISON:")
    print(f"Standalone CAGR: {standalone_result.cagr:.2f}%")
    print(f"Forced Bull CAGR: {forced_result.cagr:.2f}%")
    print(f"Difference: {abs(standalone_result.cagr - forced_result.cagr):.2f}%")

    if abs(standalone_result.cagr - forced_result.cagr) < 0.1:
        print("✅ PASSED: Forced bull matches standalone!")
        forced_result.passed = True
    else:
        print("❌ FAILED: Wrapper has issues even in forced bull mode!")
        forced_result.notes.append("Wrapper logic bug detected")

    return forced_result


def validate_experiment_3():
    """
    EXPERIMENT 3: Forced Panic Mode (March 2020)

    Expected: Should use BearDipBuyer during crash period
    """
    print("\n" + "="*80)
    print("EXPERIMENT 3: FORCED PANIC MODE (COVID CRASH)")
    print("="*80)
    print("Purpose: Test BearDipBuyer in isolation through wrapper")
    print("Test Period: March 2020 (VIX peaked at 82.69)")

    # Run forced panic mode
    forced_panic = ForcedPanicMode_v1()
    panic_result = run_backtest(
        forced_panic,
        "2020-03-01",
        "2020-04-30",
        "Forced Panic Mode"
    )

    # Run standalone BearDipBuyer
    bear = BearDipBuyer_v1()
    bear_result = run_backtest(
        bear,
        "2020-03-01",
        "2020-04-30",
        "Standalone BearDipBuyer"
    )

    print("\n📊 COMPARISON:")
    print(f"Standalone Bear Return: {bear_result.total_return:.2f}%")
    print(f"Forced Panic Return: {panic_result.total_return:.2f}%")
    print(f"Difference: {abs(bear_result.total_return - panic_result.total_return):.2f}%")

    if abs(bear_result.total_return - panic_result.total_return) < 1.0:
        print("✅ PASSED: Forced panic matches BearDipBuyer!")
        panic_result.passed = True
    else:
        print("❌ FAILED: Wrapper not correctly using panic model!")
        panic_result.notes.append("Panic mode switching bug")

    return panic_result


def validate_experiment_4():
    """
    EXPERIMENT 4: Manual Regime Split

    Calculate what perfect regime switching could achieve.
    """
    print("\n" + "="*80)
    print("EXPERIMENT 4: MANUAL REGIME SPLIT")
    print("="*80)
    print("Purpose: Calculate theoretical best performance")
    print("Method: Run each model on optimal periods, combine results")

    # Period 1: Bull market (2021)
    bull_model = SectorRotationAdaptive_v3()
    bull_2021 = run_backtest(bull_model, "2021-01-01", "2021-12-31", "Bull 2021")

    # Period 2: Crash (March 2020)
    bear_model = BearDipBuyer_v1()
    bear_crash = run_backtest(bear_model, "2020-03-01", "2020-04-30", "Bear Crash")

    # Period 3: Recovery (May-Dec 2020)
    bull_recovery = run_backtest(bull_model, "2020-05-01", "2020-12-31", "Bull Recovery")

    print("\n📊 OPTIMAL REGIME RESULTS:")
    print(f"Bull 2021: {bull_2021.total_return:.2f}%")
    print(f"Bear Crash: {bear_crash.total_return:.2f}%")
    print(f"Bull Recovery: {bull_recovery.total_return:.2f}%")

    # Now test actual AdaptiveRegimeSwitcher
    switcher = AdaptiveRegimeSwitcher_v1()
    actual_result = run_backtest(
        switcher,
        "2020-01-01",
        "2021-12-31",
        "Actual AdaptiveRegimeSwitcher"
    )

    print(f"\nActual Switcher CAGR: {actual_result.cagr:.2f}%")
    print("Theoretical best would combine the above periods optimally")

    return actual_result


def validate_experiment_7():
    """
    EXPERIMENT 7: Commission Audit

    Check why commission per trade differs.
    """
    print("\n" + "="*80)
    print("EXPERIMENT 7: COMMISSION AUDIT")
    print("="*80)
    print("Purpose: Verify commission calculations")

    # Run both models
    standalone = SectorRotationAdaptive_v3()
    standalone_result = run_backtest(
        standalone,
        "2020-01-01",
        "2024-12-31",
        "Standalone"
    )

    switcher = AdaptiveRegimeSwitcher_v1()
    switcher_result = run_backtest(
        switcher,
        "2020-01-01",
        "2024-12-31",
        "Switcher"
    )

    # Calculate commission per trade
    standalone_per_trade = (
        standalone_result.commissions / standalone_result.num_trades
        if standalone_result.num_trades > 0 else 0
    )
    switcher_per_trade = (
        switcher_result.commissions / switcher_result.num_trades
        if switcher_result.num_trades > 0 else 0
    )

    print("\n📊 COMMISSION ANALYSIS:")
    print(f"Standalone: ${standalone_result.commissions:,.0f} / {standalone_result.num_trades} trades = ${standalone_per_trade:.2f}/trade")
    print(f"Switcher: ${switcher_result.commissions:,.0f} / {switcher_result.num_trades} trades = ${switcher_per_trade:.2f}/trade")

    if switcher_per_trade < standalone_per_trade:
        print("⚠️ WARNING: Switcher has LOWER commission per trade!")
        print("This suggests smaller position sizes - potential bug!")

    return switcher_result


def main():
    """
    Run all validation experiments.
    """
    print("\n" + "="*80)
    print("ADAPTIVE REGIME SWITCHER VALIDATION SUITE")
    print("="*80)
    print("Mission: Find why AdaptiveRegimeSwitcher underperforms")
    print("Expected: Combined should beat constituent models")
    print("Actual: 8.58% CAGR (worse than both!)")

    results = []

    # Run experiments
    print("\n🔬 STARTING VALIDATION EXPERIMENTS...")

    # Experiment 1: Trivial Passthrough
    standalone, passthrough = validate_experiment_1()
    results.append(passthrough)

    # Experiment 2: Forced Bull
    forced_bull = validate_experiment_2()
    results.append(forced_bull)

    # Experiment 3: Forced Panic
    forced_panic = validate_experiment_3()
    results.append(forced_panic)

    # Experiment 4: Manual Split
    manual_split = validate_experiment_4()
    results.append(manual_split)

    # Experiment 7: Commission Audit
    commission = validate_experiment_7()
    results.append(commission)

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    for result in results:
        status = "✅" if result.passed else "❌"
        print(f"{status} {result.experiment_name}: CAGR={result.cagr:.2f}%")

    print("\n📋 KEY FINDINGS:")
    if not results[0].passed:  # Trivial passthrough
        print("• CRITICAL: Backtest engine has wrapper overhead issues!")
    if not results[1].passed:  # Forced bull
        print("• CRITICAL: Wrapper logic corrupts bull model behavior!")
    if not results[2].passed:  # Forced panic
        print("• CRITICAL: Panic mode switching not working!")

    print("\nNext Steps:")
    print("1. Fix any failed experiments starting from #1")
    print("2. Run more detailed logging experiments")
    print("3. Implement trade-by-trade comparison")

    return results


if __name__ == "__main__":
    results = main()