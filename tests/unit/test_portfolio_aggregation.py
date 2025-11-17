"""
Unit Tests for Portfolio Aggregation and Attribution

Tests:
- Portfolio Engine aggregation logic
- Attribution tracking accuracy
- Budget allocation correctness
- Edge cases and error handling
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
import sys
sys.path.append('../..')
from models.base import ModelOutput, RegimeState
from engines.portfolio.engine import PortfolioEngine, PortfolioTarget
from engines.portfolio.attribution import AttributionTracker


class TestPortfolioAggregation:
    """Test portfolio aggregation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = PortfolioEngine()
        self.timestamp = pd.Timestamp('2025-01-15 16:00', tz='UTC')
        self.nav = Decimal('100000.00')

    def test_single_model_aggregation(self):
        """Test aggregation with a single model."""
        # Model A: 60% budget, 100% to SPY
        model_outputs = [
            ModelOutput(
                model_name="EquityTrendModel_v1",
                timestamp=self.timestamp,
                weights={'SPY': 1.0, 'QQQ': 0.0}
            )
        ]

        model_budgets = {"EquityTrendModel_v1": 0.60}

        target = self.engine.aggregate_model_outputs(
            model_outputs,
            model_budgets,
            self.nav
        )

        # Check NAV-relative weights
        assert target.target_weights['SPY'] == pytest.approx(0.60)
        assert target.target_weights['QQQ'] == pytest.approx(0.0)

        # Check exposure metrics
        assert target.total_exposure == pytest.approx(0.60)
        assert target.long_exposure == pytest.approx(0.60)
        assert target.short_exposure == pytest.approx(0.0)

        # Check attribution
        assert 'EquityTrendModel_v1' in target.attribution['SPY']
        assert target.attribution['SPY']['EquityTrendModel_v1'] == pytest.approx(0.60)

    def test_multi_model_aggregation_non_overlapping(self):
        """Test aggregation with multiple models targeting different assets."""
        model_outputs = [
            # Model A: 60% budget, 100% to SPY
            ModelOutput(
                model_name="EquityTrendModel_v1",
                timestamp=self.timestamp,
                weights={'SPY': 1.0, 'QQQ': 0.0}
            ),
            # Model B: 25% budget, 100% to QQQ
            ModelOutput(
                model_name="IndexMeanReversionModel_v1",
                timestamp=self.timestamp,
                weights={'SPY': 0.0, 'QQQ': 1.0}
            ),
            # Model C: 15% budget, 50% BTC, 50% ETH
            ModelOutput(
                model_name="CryptoMomentumModel_v1",
                timestamp=self.timestamp,
                weights={'BTC': 0.5, 'ETH': 0.5}
            )
        ]

        model_budgets = {
            "EquityTrendModel_v1": 0.60,
            "IndexMeanReversionModel_v1": 0.25,
            "CryptoMomentumModel_v1": 0.15
        }

        target = self.engine.aggregate_model_outputs(
            model_outputs,
            model_budgets,
            self.nav
        )

        # Check NAV-relative weights
        assert target.target_weights['SPY'] == pytest.approx(0.60)
        assert target.target_weights['QQQ'] == pytest.approx(0.25)
        assert target.target_weights['BTC'] == pytest.approx(0.075)  # 0.5 * 0.15
        assert target.target_weights['ETH'] == pytest.approx(0.075)  # 0.5 * 0.15

        # Check total exposure
        expected_total = 0.60 + 0.25 + 0.075 + 0.075
        assert target.total_exposure == pytest.approx(expected_total)

        # Check attribution
        assert target.attribution['SPY']['EquityTrendModel_v1'] == pytest.approx(0.60)
        assert target.attribution['QQQ']['IndexMeanReversionModel_v1'] == pytest.approx(0.25)
        assert target.attribution['BTC']['CryptoMomentumModel_v1'] == pytest.approx(0.075)
        assert target.attribution['ETH']['CryptoMomentumModel_v1'] == pytest.approx(0.075)

    def test_multi_model_aggregation_overlapping(self):
        """Test aggregation when multiple models target the same asset."""
        model_outputs = [
            # Model A: 60% budget, 100% to SPY
            ModelOutput(
                model_name="EquityTrendModel_v1",
                timestamp=self.timestamp,
                weights={'SPY': 1.0}
            ),
            # Model B: 25% budget, 100% to SPY (same asset!)
            ModelOutput(
                model_name="IndexMeanReversionModel_v1",
                timestamp=self.timestamp,
                weights={'SPY': 1.0}
            )
        ]

        model_budgets = {
            "EquityTrendModel_v1": 0.60,
            "IndexMeanReversionModel_v1": 0.25
        }

        target = self.engine.aggregate_model_outputs(
            model_outputs,
            model_budgets,
            self.nav
        )

        # Check that weights sum correctly
        assert target.target_weights['SPY'] == pytest.approx(0.85)  # 0.60 + 0.25

        # Check attribution tracks both models
        assert 'EquityTrendModel_v1' in target.attribution['SPY']
        assert 'IndexMeanReversionModel_v1' in target.attribution['SPY']
        assert target.attribution['SPY']['EquityTrendModel_v1'] == pytest.approx(0.60)
        assert target.attribution['SPY']['IndexMeanReversionModel_v1'] == pytest.approx(0.25)

    def test_budget_sum_verification(self):
        """Test that budgets sum correctly (critical invariant)."""
        model_outputs = [
            ModelOutput(
                model_name="Model_A",
                timestamp=self.timestamp,
                weights={'SPY': 0.5, 'QQQ': 0.5}  # Uses full budget
            ),
            ModelOutput(
                model_name="Model_B",
                timestamp=self.timestamp,
                weights={'BTC': 1.0}  # Uses full budget
            ),
            ModelOutput(
                model_name="Model_C",
                timestamp=self.timestamp,
                weights={'ETH': 0.8}  # Uses 80% of budget
            )
        ]

        model_budgets = {
            "Model_A": 0.40,
            "Model_B": 0.30,
            "Model_C": 0.30
        }

        target = self.engine.aggregate_model_outputs(
            model_outputs,
            model_budgets,
            self.nav
        )

        # Verify total budgets = 100%
        assert sum(model_budgets.values()) == pytest.approx(1.0)

        # Calculate actual exposures
        expected_exposures = {
            'SPY': 0.40 * 0.5,  # 0.20
            'QQQ': 0.40 * 0.5,  # 0.20
            'BTC': 0.30 * 1.0,  # 0.30
            'ETH': 0.30 * 0.8   # 0.24
        }

        for symbol, expected in expected_exposures.items():
            assert target.target_weights[symbol] == pytest.approx(expected)

    def test_zero_weights_handling(self):
        """Test handling of zero weights (no position)."""
        model_outputs = [
            ModelOutput(
                model_name="Model_A",
                timestamp=self.timestamp,
                weights={'SPY': 0.0, 'QQQ': 0.0}  # All zeros
            )
        ]

        model_budgets = {"Model_A": 0.60}

        target = self.engine.aggregate_model_outputs(
            model_outputs,
            model_budgets,
            self.nav
        )

        # Zero weights should still be in target
        assert target.target_weights['SPY'] == pytest.approx(0.0)
        assert target.target_weights['QQQ'] == pytest.approx(0.0)

        # No exposure
        assert target.total_exposure == pytest.approx(0.0)

        # Zero weights should not appear in attribution
        assert 'Model_A' not in target.attribution.get('SPY', {})
        assert 'Model_A' not in target.attribution.get('QQQ', {})

    def test_portfolio_validation(self):
        """Test portfolio validation constraints."""
        # Create target that exceeds limits
        target = PortfolioTarget(
            timestamp=self.timestamp,
            target_weights={'SPY': 0.80, 'QQQ': 0.60},  # Total = 1.40 (exceeds 1.2 limit)
            attribution={},
            total_exposure=1.40,
            long_exposure=1.40,
            short_exposure=0.0,
            num_active_models=2
        )

        is_valid, violations = self.engine.validate_portfolio(
            target,
            max_total_exposure=1.2
        )

        assert not is_valid
        assert len(violations) > 0
        assert any("Total exposure" in v for v in violations)


class TestAttributionTracking:
    """Test attribution tracking functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = AttributionTracker()
        self.timestamp = pd.Timestamp('2025-01-15 16:00', tz='UTC')
        self.nav = Decimal('100000.00')

    def test_attribution_sum_equals_position(self):
        """Test that sum of attributions equals actual position (critical invariant)."""
        positions = {
            'SPY': 0.60,
            'QQQ': 0.25,
            'BTC': 0.15
        }

        attribution = {
            'SPY': {
                'Model_A': 0.40,
                'Model_B': 0.20  # Sum = 0.60 ✓
            },
            'QQQ': {
                'Model_B': 0.25  # Sum = 0.25 ✓
            },
            'BTC': {
                'Model_C': 0.15  # Sum = 0.15 ✓
            }
        }

        model_budgets = {
            'Model_A': 0.40,
            'Model_B': 0.45,
            'Model_C': 0.15
        }

        # Record attribution
        snapshot = self.tracker.record_attribution(
            timestamp=self.timestamp,
            positions=positions,
            attribution=attribution,
            model_budgets=model_budgets,
            nav=self.nav
        )

        # Validate
        is_valid, violations = self.tracker.validate_attribution(positions, attribution)

        assert is_valid, f"Validation failed: {violations}"
        assert len(violations) == 0

    def test_attribution_mismatch_detection(self):
        """Test detection of attribution that doesn't match position."""
        positions = {
            'SPY': 0.60
        }

        # Attribution sums to 0.65 instead of 0.60
        attribution = {
            'SPY': {
                'Model_A': 0.40,
                'Model_B': 0.25  # Sum = 0.65 ≠ 0.60 ✗
            }
        }

        is_valid, violations = self.tracker.validate_attribution(positions, attribution)

        assert not is_valid
        assert len(violations) > 0
        assert any("SPY" in v and "0.65" in v for v in violations)

    def test_position_without_attribution(self):
        """Test detection of position without attribution."""
        positions = {
            'SPY': 0.60,
            'QQQ': 0.25  # Has position but no attribution
        }

        attribution = {
            'SPY': {
                'Model_A': 0.60
            }
            # Missing QQQ attribution
        }

        is_valid, violations = self.tracker.validate_attribution(positions, attribution)

        assert not is_valid
        assert any("QQQ" in v for v in violations)

    def test_attribution_without_position(self):
        """Test detection of attribution without position."""
        positions = {
            'SPY': 0.60
        }

        attribution = {
            'SPY': {
                'Model_A': 0.60
            },
            'QQQ': {
                'Model_B': 0.25  # Has attribution but no position
            }
        }

        is_valid, violations = self.tracker.validate_attribution(positions, attribution)

        assert not is_valid
        assert any("QQQ" in v for v in violations)

    def test_model_exposure_extraction(self):
        """Test extracting exposure for a specific model."""
        positions = {
            'SPY': 0.60,
            'QQQ': 0.25,
            'BTC': 0.15
        }

        attribution = {
            'SPY': {'Model_A': 0.40, 'Model_B': 0.20},
            'QQQ': {'Model_B': 0.25},
            'BTC': {'Model_C': 0.15}
        }

        model_budgets = {'Model_A': 0.40, 'Model_B': 0.45, 'Model_C': 0.15}

        snapshot = self.tracker.record_attribution(
            self.timestamp, positions, attribution, model_budgets, self.nav
        )

        # Extract Model_B exposure
        model_b_exposure = self.tracker.get_model_exposure(snapshot, 'Model_B')

        assert 'SPY' in model_b_exposure
        assert 'QQQ' in model_b_exposure
        assert 'BTC' not in model_b_exposure

        assert model_b_exposure['SPY'] == pytest.approx(0.20)
        assert model_b_exposure['QQQ'] == pytest.approx(0.25)

    def test_attribution_report_generation(self):
        """Test attribution report generation."""
        positions = {'SPY': 0.60, 'QQQ': 0.25}
        attribution = {
            'SPY': {'Model_A': 0.40, 'Model_B': 0.20},
            'QQQ': {'Model_B': 0.25}
        }
        model_budgets = {'Model_A': 0.40, 'Model_B': 0.60}

        snapshot = self.tracker.record_attribution(
            self.timestamp, positions, attribution, model_budgets, self.nav
        )

        report = self.tracker.generate_attribution_report(snapshot)

        assert len(report) == 3  # 3 attribution entries
        assert 'symbol' in report.columns
        assert 'model' in report.columns
        assert 'contribution' in report.columns
        assert 'dollar_value' in report.columns

    def test_model_summary_generation(self):
        """Test per-model summary generation."""
        positions = {'SPY': 0.60, 'QQQ': 0.25, 'BTC': 0.15}
        attribution = {
            'SPY': {'Model_A': 0.60},
            'QQQ': {'Model_B': 0.25},
            'BTC': {'Model_C': 0.15}
        }
        model_budgets = {
            'Model_A': 0.60,
            'Model_B': 0.25,
            'Model_C': 0.15
        }

        snapshot = self.tracker.record_attribution(
            self.timestamp, positions, attribution, model_budgets, self.nav
        )

        summary = self.tracker.get_model_summary(snapshot)

        assert len(summary) == 3  # 3 models
        assert 'model' in summary.columns
        assert 'budget' in summary.columns
        assert 'total_exposure' in summary.columns
        assert 'utilization_pct' in summary.columns

        # Model_A should have 100% utilization (budget = exposure = 0.60)
        model_a_row = summary[summary['model'] == 'Model_A'].iloc[0]
        assert model_a_row['utilization_pct'] == pytest.approx(100.0)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, '-v'])
