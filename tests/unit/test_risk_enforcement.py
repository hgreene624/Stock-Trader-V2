"""
Unit tests for Risk Engine constraint enforcement.

Tests:
1. Per-asset position caps (40% NAV limit)
2. Asset-class caps (crypto 20% limit)
3. Leverage limits (1.2x NAV total exposure)
4. Drawdown de-risking (50% reduction at 15% threshold)
5. Drawdown halt (zero positions at 20% threshold)
6. Multiple constraints simultaneously
7. Regime-aware budget scaling
"""

import pytest
import pandas as pd
from decimal import Decimal
from typing import Dict, List

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.risk.engine import RiskEngine, RiskLimits, RiskViolation
from engines.risk.scaling import RegimeRiskScaler
from models.base import RegimeState


class TestRiskEnginePerAssetCaps:
    """Test per-asset position size constraints."""

    def test_single_asset_exceeds_cap(self):
        """Test that single asset exceeding 40% cap gets scaled down."""
        # Setup
        limits = RiskLimits(max_position_size=0.40)
        engine = RiskEngine(limits=limits)

        # Target: SPY = 50% (exceeds 40% cap)
        target_weights = {'SPY': 0.50, 'QQQ': 0.30}
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify
        assert constrained['SPY'] == 0.40, "SPY should be capped to 40%"
        assert constrained['QQQ'] == 0.30, "QQQ should remain unchanged"
        assert len(violations) == 1, "Should have 1 violation"
        assert violations[0].constraint_type == 'position_size'
        assert violations[0].affected_assets == ['SPY']

    def test_multiple_assets_exceed_cap(self):
        """Test that multiple assets exceeding cap all get scaled down."""
        # Setup
        limits = RiskLimits(max_position_size=0.40)
        engine = RiskEngine(limits=limits)

        # Target: SPY = 50%, QQQ = 45% (both exceed 40%)
        target_weights = {'SPY': 0.50, 'QQQ': 0.45, 'BTC': 0.10}
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify
        assert constrained['SPY'] == 0.40, "SPY should be capped to 40%"
        assert constrained['QQQ'] == 0.40, "QQQ should be capped to 40%"
        assert constrained['BTC'] == 0.10, "BTC should remain unchanged"
        assert len(violations) == 2, "Should have 2 violations"

    def test_negative_position_respects_cap(self):
        """Test that short positions also respect per-asset cap."""
        # Setup
        limits = RiskLimits(max_position_size=0.40)
        engine = RiskEngine(limits=limits)

        # Target: SPY = -50% (short position)
        target_weights = {'SPY': -0.50, 'QQQ': 0.30}
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify
        assert constrained['SPY'] == -0.40, "Short SPY should be capped to -40%"
        assert len(violations) == 1


class TestRiskEngineAssetClassCaps:
    """Test asset-class exposure constraints (crypto)."""

    def test_crypto_exceeds_class_cap(self):
        """Test that crypto exposure > 20% gets scaled down proportionally."""
        # Setup
        limits = RiskLimits(max_crypto_exposure=0.20)
        engine = RiskEngine(limits=limits)

        # Target: BTC = 20%, ETH = 10% → total crypto = 30% (exceeds 20%)
        target_weights = {'SPY': 0.40, 'BTC': 0.20, 'ETH': 0.10}
        asset_metadata = {
            'SPY': {'asset_class': 'equity'},
            'BTC': {'asset_class': 'crypto'},
            'ETH': {'asset_class': 'crypto'}
        }
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav, asset_metadata
        )

        # Verify
        # Crypto should be scaled by 20/30 = 0.6667
        crypto_exposure = abs(constrained['BTC']) + abs(constrained['ETH'])
        assert abs(crypto_exposure - 0.20) < 0.0001, "Total crypto should be 20%"

        # BTC and ETH should be scaled proportionally
        expected_btc = 0.20 * (0.20 / 0.30)  # ~0.1333
        expected_eth = 0.10 * (0.20 / 0.30)  # ~0.0667
        assert abs(constrained['BTC'] - expected_btc) < 0.0001
        assert abs(constrained['ETH'] - expected_eth) < 0.0001

        # Equity should remain unchanged
        assert constrained['SPY'] == 0.40

        assert len(violations) == 1
        assert violations[0].constraint_type == 'asset_class'

    def test_crypto_under_class_cap(self):
        """Test that crypto under 20% cap is not modified."""
        # Setup
        limits = RiskLimits(
            max_position_size=0.70,  # Set high to avoid per-asset cap interfering
            max_crypto_exposure=0.20
        )
        engine = RiskEngine(limits=limits)

        # Target: BTC = 10%, ETH = 5% → total crypto = 15% (under 20%)
        target_weights = {'SPY': 0.60, 'BTC': 0.10, 'ETH': 0.05}
        asset_metadata = {
            'SPY': {'asset_class': 'equity'},
            'BTC': {'asset_class': 'crypto'},
            'ETH': {'asset_class': 'crypto'}
        }
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav, asset_metadata
        )

        # Verify - no changes (crypto under cap, all positions under per-asset cap)
        assert constrained['BTC'] == 0.10
        assert constrained['ETH'] == 0.05
        assert constrained['SPY'] == 0.60

        # No asset_class violations (might have other violations)
        asset_class_violations = [v for v in violations if v.constraint_type == 'asset_class']
        assert len(asset_class_violations) == 0


class TestRiskEngineLeverageLimits:
    """Test total portfolio leverage constraints."""

    def test_leverage_exceeds_limit(self):
        """Test that total exposure > 1.2x gets scaled down proportionally."""
        # Setup
        limits = RiskLimits(
            max_position_size=0.70,  # Set high to avoid per-asset cap interfering
            max_total_leverage=1.20
        )
        engine = RiskEngine(limits=limits)

        # Target: Total = 1.40 (SPY 60% + QQQ 50% + BTC 30%)
        target_weights = {'SPY': 0.60, 'QQQ': 0.50, 'BTC': 0.30}
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify
        # Total should be scaled by 1.20/1.40 = 0.8571
        total_exposure = sum(abs(w) for w in constrained.values())
        assert abs(total_exposure - 1.20) < 0.0001, f"Total exposure should be 1.20, got {total_exposure}"

        # All positions scaled proportionally
        scale_factor = 1.20 / 1.40
        assert abs(constrained['SPY'] - 0.60 * scale_factor) < 0.0001
        assert abs(constrained['QQQ'] - 0.50 * scale_factor) < 0.0001
        assert abs(constrained['BTC'] - 0.30 * scale_factor) < 0.0001

        assert len(violations) >= 1
        leverage_violations = [v for v in violations if v.constraint_type == 'leverage']
        assert len(leverage_violations) == 1

    def test_leverage_under_limit(self):
        """Test that total exposure under 1.2x is not modified."""
        # Setup
        limits = RiskLimits(
            max_position_size=0.70,  # Set high to avoid per-asset cap interfering
            max_total_leverage=1.20
        )
        engine = RiskEngine(limits=limits)

        # Target: Total = 1.00 (under limit), all positions under per-asset cap
        target_weights = {'SPY': 0.60, 'QQQ': 0.30, 'BTC': 0.10}
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify - no leverage scaling, no per-asset capping
        assert constrained['SPY'] == 0.60
        assert constrained['QQQ'] == 0.30
        assert constrained['BTC'] == 0.10

        leverage_violations = [v for v in violations if v.constraint_type == 'leverage']
        assert len(leverage_violations) == 0


class TestRiskEngineDrawdownDerisking:
    """Test drawdown-based risk reduction."""

    def test_drawdown_derisk_triggered(self):
        """Test that 16% drawdown triggers 50% position reduction."""
        # Setup
        limits = RiskLimits(
            max_drawdown_threshold=0.15,
            drawdown_derisk_factor=0.50
        )
        engine = RiskEngine(limits=limits)

        # Simulate drawdown: peak = $120k, current = $100.8k → 16% drawdown
        engine.peak_nav = Decimal('120000.00')
        current_nav = Decimal('100800.00')

        # Target portfolio
        target_weights = {'SPY': 0.60, 'QQQ': 0.40}

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify drawdown calculation
        expected_drawdown = 1.0 - (100800.0 / 120000.0)  # ~0.16
        assert abs(engine.current_drawdown - expected_drawdown) < 0.0001

        # Verify 50% scale down
        assert abs(constrained['SPY'] - 0.30) < 0.0001, "SPY should be 60% * 0.5 = 30%"
        assert abs(constrained['QQQ'] - 0.20) < 0.0001, "QQQ should be 40% * 0.5 = 20%"

        # Verify violation recorded
        drawdown_violations = [v for v in violations if v.constraint_type == 'drawdown']
        assert len(drawdown_violations) >= 1
        assert engine.derisk_active is True

    def test_drawdown_under_threshold(self):
        """Test that drawdown < 15% does not trigger de-risk."""
        # Setup
        limits = RiskLimits(max_drawdown_threshold=0.15)
        engine = RiskEngine(limits=limits)

        # Simulate small drawdown: peak = $120k, current = $108k → 10% drawdown
        engine.peak_nav = Decimal('120000.00')
        current_nav = Decimal('108000.00')

        # Target portfolio
        target_weights = {'SPY': 0.60, 'QQQ': 0.40}

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify no de-risk scaling (but may have other constraints)
        # Since drawdown < threshold, de-risk should not apply
        assert engine.current_drawdown < 0.15
        assert engine.derisk_active is False


class TestRiskEngineDrawdownHalt:
    """Test drawdown halt functionality."""

    def test_drawdown_halt_triggered(self):
        """Test that 21% drawdown triggers full position halt."""
        # Setup
        limits = RiskLimits(max_drawdown_halt=0.20)
        engine = RiskEngine(limits=limits)

        # Simulate severe drawdown: peak = $100k, current = $79k → 21% drawdown
        engine.peak_nav = Decimal('100000.00')
        current_nav = Decimal('79000.00')

        # Target portfolio
        target_weights = {'SPY': 0.60, 'QQQ': 0.40}

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify all positions zeroed
        assert constrained['SPY'] == 0.0, "SPY should be zeroed on halt"
        assert constrained['QQQ'] == 0.0, "QQQ should be zeroed on halt"

        # Verify halt flag
        assert engine.halt_active is True

        # Verify violation recorded
        halt_violations = [v for v in violations if v.severity == 'halt']
        assert len(halt_violations) >= 1


class TestRiskEngineMultipleConstraints:
    """Test multiple constraints applied simultaneously."""

    def test_per_asset_then_leverage(self):
        """Test that per-asset caps applied before leverage limit."""
        # Setup
        limits = RiskLimits(
            max_position_size=0.40,
            max_total_leverage=1.20
        )
        engine = RiskEngine(limits=limits)

        # Target: SPY 50%, QQQ 45%, BTC 30% → total 1.25
        # After per-asset caps: SPY 40%, QQQ 40%, BTC 30% → total 1.10 (under leverage)
        target_weights = {'SPY': 0.50, 'QQQ': 0.45, 'BTC': 0.30}
        current_nav = Decimal('100000.00')

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify per-asset caps applied
        assert constrained['SPY'] == 0.40
        assert constrained['QQQ'] == 0.40

        # Total after per-asset caps is 1.10, which is under leverage limit
        total = sum(abs(w) for w in constrained.values())
        assert total <= 1.20

    def test_drawdown_then_asset_caps(self):
        """Test that drawdown de-risk applied before asset caps."""
        # Setup
        limits = RiskLimits(
            max_position_size=0.40,
            max_drawdown_threshold=0.15,
            drawdown_derisk_factor=0.50
        )
        engine = RiskEngine(limits=limits)

        # Simulate drawdown
        engine.peak_nav = Decimal('120000.00')
        current_nav = Decimal('100800.00')  # 16% drawdown

        # Target: SPY 60%
        # After de-risk: SPY 30% (60% * 0.5)
        # Per-asset cap: 30% < 40%, so no further change
        target_weights = {'SPY': 0.60}

        # Execute
        constrained, violations = engine.enforce_constraints(
            target_weights, current_nav
        )

        # Verify
        assert abs(constrained['SPY'] - 0.30) < 0.0001
        assert engine.derisk_active is True


class TestRegimeRiskScaler:
    """Test regime-aware budget scaling."""

    def test_bear_regime_reduces_equity_budgets(self):
        """Test that BEAR regime reduces equity model budgets."""
        # Setup
        regime_budgets = {
            "BEAR": {
                "EquityTrendModel_v1": 0.30,  # Reduce from 60% to 30%
                "CryptoMomentumModel_v1": 0.05  # Reduce from 15% to 5%
            }
        }
        scaler = RegimeRiskScaler(regime_budgets=regime_budgets)

        base_budgets = {
            "EquityTrendModel_v1": 0.60,
            "IndexMeanReversionModel_v1": 0.25,
            "CryptoMomentumModel_v1": 0.15
        }

        regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='bear',
            vol_regime='normal',
            crypto_regime='neutral',
            macro_regime='neutral'
        )

        # Execute
        adjusted = scaler.apply_regime_scaling(base_budgets, regime)

        # Verify
        assert adjusted['EquityTrendModel_v1'] == 0.30
        assert adjusted['IndexMeanReversionModel_v1'] == 0.25  # Unchanged
        assert adjusted['CryptoMomentumModel_v1'] == 0.05

    def test_high_vol_applies_global_multiplier(self):
        """Test that HIGH_VOL regime applies 70% multiplier to all models."""
        # Setup
        regime_budgets = {
            "HIGH_VOL": {
                "all_models": 0.70
            }
        }
        scaler = RegimeRiskScaler(regime_budgets=regime_budgets)

        base_budgets = {
            "EquityTrendModel_v1": 0.60,
            "IndexMeanReversionModel_v1": 0.25,
            "CryptoMomentumModel_v1": 0.15
        }

        regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='neutral',
            vol_regime='high',
            crypto_regime='neutral',
            macro_regime='neutral'
        )

        # Execute
        adjusted = scaler.apply_regime_scaling(base_budgets, regime)

        # Verify - all scaled by 70%
        assert abs(adjusted['EquityTrendModel_v1'] - 0.60 * 0.70) < 0.0001
        assert abs(adjusted['IndexMeanReversionModel_v1'] - 0.25 * 0.70) < 0.0001
        assert abs(adjusted['CryptoMomentumModel_v1'] - 0.15 * 0.70) < 0.0001

    def test_risk_off_zeros_crypto(self):
        """Test that RISK_OFF regime zeros crypto model budget."""
        # Setup
        regime_budgets = {
            "RISK_OFF": {
                "CryptoMomentumModel_v1": 0.0
            }
        }
        scaler = RegimeRiskScaler(regime_budgets=regime_budgets)

        base_budgets = {
            "EquityTrendModel_v1": 0.60,
            "CryptoMomentumModel_v1": 0.15
        }

        regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='neutral',
            vol_regime='normal',
            crypto_regime='risk_off',
            macro_regime='neutral'
        )

        # Execute
        adjusted = scaler.apply_regime_scaling(base_budgets, regime)

        # Verify
        assert adjusted['CryptoMomentumModel_v1'] == 0.0
        assert adjusted['EquityTrendModel_v1'] == 0.60  # Unchanged

    def test_neutral_regime_no_changes(self):
        """Test that neutral regime applies no budget changes."""
        # Setup
        regime_budgets = {
            "BEAR": {"EquityTrendModel_v1": 0.30},
            "RISK_OFF": {"CryptoMomentumModel_v1": 0.0}
        }
        scaler = RegimeRiskScaler(regime_budgets=regime_budgets)

        base_budgets = {
            "EquityTrendModel_v1": 0.60,
            "CryptoMomentumModel_v1": 0.15
        }

        regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='neutral',
            vol_regime='normal',
            crypto_regime='neutral',
            macro_regime='neutral'
        )

        # Execute
        adjusted = scaler.apply_regime_scaling(base_budgets, regime)

        # Verify - no changes
        assert adjusted == base_budgets


class TestRiskEngineDrawdownTracking:
    """Test drawdown calculation and peak NAV tracking."""

    def test_peak_nav_initialization(self):
        """Test that first NAV update sets peak."""
        engine = RiskEngine()

        assert engine.peak_nav is None

        engine.update_nav(Decimal('100000.00'))

        assert engine.peak_nav == Decimal('100000.00')
        assert engine.current_drawdown == 0.0

    def test_peak_nav_updates_on_new_high(self):
        """Test that peak NAV updates when new high reached."""
        engine = RiskEngine()

        engine.update_nav(Decimal('100000.00'))
        assert engine.peak_nav == Decimal('100000.00')

        engine.update_nav(Decimal('95000.00'))  # Decline
        assert engine.peak_nav == Decimal('100000.00')  # Peak unchanged

        engine.update_nav(Decimal('105000.00'))  # New high
        assert engine.peak_nav == Decimal('105000.00')  # Peak updated

    def test_drawdown_calculation(self):
        """Test drawdown calculation from peak."""
        engine = RiskEngine()

        engine.update_nav(Decimal('100000.00'))
        assert engine.current_drawdown == 0.0

        engine.update_nav(Decimal('90000.00'))  # 10% drawdown
        assert abs(engine.current_drawdown - 0.10) < 0.0001

        engine.update_nav(Decimal('85000.00'))  # 15% drawdown
        assert abs(engine.current_drawdown - 0.15) < 0.0001

        engine.update_nav(Decimal('95000.00'))  # Recovery to 5% drawdown
        assert abs(engine.current_drawdown - 0.05) < 0.0001


class TestRiskEngineViolationTracking:
    """Test violation history and reporting."""

    def test_violations_recorded_in_history(self):
        """Test that violations are stored in history."""
        limits = RiskLimits(max_position_size=0.40)
        engine = RiskEngine(limits=limits)

        target_weights = {'SPY': 0.50}
        current_nav = Decimal('100000.00')

        # Execute multiple times
        engine.enforce_constraints(target_weights, current_nav)
        engine.enforce_constraints(target_weights, current_nav)

        # Verify history
        assert len(engine.violation_history) == 2

    def test_get_violation_summary(self):
        """Test violation summary DataFrame generation."""
        limits = RiskLimits(max_position_size=0.40)
        engine = RiskEngine(limits=limits)

        target_weights = {'SPY': 0.50, 'QQQ': 0.45}
        current_nav = Decimal('100000.00')

        engine.enforce_constraints(target_weights, current_nav)

        # Get summary
        summary = engine.get_violation_summary()

        # Verify DataFrame structure
        assert isinstance(summary, pd.DataFrame)
        assert len(summary) == 2  # Two violations (SPY and QQQ)
        assert 'constraint_type' in summary.columns
        assert 'severity' in summary.columns
        assert 'message' in summary.columns


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
