"""
Quick test to verify regime-aware bull/bear models work correctly.

Tests:
1. Bull model only activates in bull regime
2. Bear model only activates in bear regime
3. Both use their specialized parameters
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models.sector_rotation_bull_v1 import SectorRotationBull_v1
from models.sector_rotation_bear_v1 import SectorRotationBear_v1
from models.base import Context, RegimeState
import pandas as pd
import numpy as np

def create_mock_context(regime: str) -> Context:
    """Create mock context with specified regime."""

    # Create mock features for a few sectors
    mock_features = {}
    sectors = ['XLK', 'XLF', 'XLE', 'TLT']

    for sector in sectors:
        # Create 200 days of mock price data (timezone-aware)
        dates = pd.date_range(end='2024-01-01', periods=200, freq='D', tz='UTC')
        prices = pd.Series(
            100 + np.cumsum(np.random.randn(200) * 0.5),
            index=dates
        )
        mock_features[sector] = pd.DataFrame({
            'close': prices,
            'volume': 1000000
        })

    # Create regime state
    regime_state = RegimeState(
        timestamp=pd.Timestamp('2024-01-01'),
        equity_regime=regime,
        vol_regime='normal',
        crypto_regime='neutral',
        macro_regime='neutral'
    )

    # Create context
    from decimal import Decimal
    context = Context(
        timestamp=pd.Timestamp('2024-01-01', tz='UTC'),
        asset_features=mock_features,
        regime=regime_state,
        model_budget_fraction=1.0,
        model_budget_value=Decimal('100000.0'),
        current_exposures={}
    )

    return context


def test_bull_model():
    """Test that bull model only activates in bull regime."""
    print("\n" + "="*60)
    print("Testing SectorRotationBull_v1")
    print("="*60)

    model = SectorRotationBull_v1()
    print(f"Model parameters: momentum={model.momentum_period}, top_n={model.top_n}, "
          f"min_momentum={model.min_momentum}, leverage={model.target_leverage}")

    # Test in bull regime (should activate)
    print("\n1. Testing in BULL regime (should activate):")
    context_bull = create_mock_context('bull')
    output_bull = model.generate_target_weights(context_bull)
    total_weight_bull = sum(output_bull.weights.values())
    print(f"   Total weight: {total_weight_bull:.2f}")
    print(f"   Non-zero weights: {sum(1 for w in output_bull.weights.values() if w > 0)}")
    print(f"   ✓ Model ACTIVE" if total_weight_bull > 0 else f"   ✗ Model INACTIVE (ERROR!)")

    # Test in bear regime (should NOT activate)
    print("\n2. Testing in BEAR regime (should NOT activate):")
    context_bear = create_mock_context('bear')
    output_bear = model.generate_target_weights(context_bear)
    total_weight_bear = sum(output_bear.weights.values())
    print(f"   Total weight: {total_weight_bear:.2f}")
    print(f"   ✓ Model INACTIVE (correct)" if total_weight_bear == 0 else f"   ✗ Model ACTIVE (ERROR!)")

    # Test in neutral regime (should NOT activate)
    print("\n3. Testing in NEUTRAL regime (should NOT activate):")
    context_neutral = create_mock_context('neutral')
    output_neutral = model.generate_target_weights(context_neutral)
    total_weight_neutral = sum(output_neutral.weights.values())
    print(f"   Total weight: {total_weight_neutral:.2f}")
    print(f"   ✓ Model INACTIVE (correct)" if total_weight_neutral == 0 else f"   ✗ Model ACTIVE (ERROR!)")


def test_bear_model():
    """Test that bear model only activates in bear regime."""
    print("\n" + "="*60)
    print("Testing SectorRotationBear_v1")
    print("="*60)

    model = SectorRotationBear_v1()
    print(f"Model parameters: momentum={model.momentum_period}, top_n={model.top_n}, "
          f"min_momentum={model.min_momentum}, leverage={model.target_leverage}")

    # Test in bear regime (should activate)
    print("\n1. Testing in BEAR regime (should activate):")
    context_bear = create_mock_context('bear')
    output_bear = model.generate_target_weights(context_bear)
    total_weight_bear = sum(output_bear.weights.values())
    print(f"   Total weight: {total_weight_bear:.2f}")
    print(f"   Non-zero weights: {sum(1 for w in output_bear.weights.values() if w > 0)}")
    print(f"   ✓ Model ACTIVE" if total_weight_bear > 0 else f"   ✗ Model INACTIVE (ERROR!)")

    # Test in bull regime (should NOT activate)
    print("\n2. Testing in BULL regime (should NOT activate):")
    context_bull = create_mock_context('bull')
    output_bull = model.generate_target_weights(context_bull)
    total_weight_bull = sum(output_bull.weights.values())
    print(f"   Total weight: {total_weight_bull:.2f}")
    print(f"   ✓ Model INACTIVE (correct)" if total_weight_bull == 0 else f"   ✗ Model ACTIVE (ERROR!)")

    # Test in neutral regime (should NOT activate)
    print("\n3. Testing in NEUTRAL regime (should NOT activate):")
    context_neutral = create_mock_context('neutral')
    output_neutral = model.generate_target_weights(context_neutral)
    total_weight_neutral = sum(output_neutral.weights.values())
    print(f"   Total weight: {total_weight_neutral:.2f}")
    print(f"   ✓ Model INACTIVE (correct)" if total_weight_neutral == 0 else f"   ✗ Model ACTIVE (ERROR!)")


def main():
    print("\n" + "#"*60)
    print("# Regime-Aware Model Tests")
    print("#"*60)

    test_bull_model()
    test_bear_model()

    print("\n" + "="*60)
    print("✓ All tests complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Test with real backtest: python -m backtest.analyze_cli --profile sector_rotation_bull")
    print("2. Test with real backtest: python -m backtest.analyze_cli --profile sector_rotation_bear")
    print("3. Run walk-forward on regime-specific models")
    print()


if __name__ == "__main__":
    main()
