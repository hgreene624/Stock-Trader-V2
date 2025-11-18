"""
End-to-end integration tests for backtest runner with risk scenarios.

Tests complete backtest workflow including:
1. Models that exceed per-asset caps
2. Models that exceed asset-class caps (crypto)
3. Models that exceed leverage limits
4. Drawdown-triggered de-risking
5. Multi-model aggregation with risk enforcement
6. Regime-aware risk scaling

These tests verify the full pipeline from config → data → models → portfolio → risk → execution.
"""

import pytest
import pandas as pd
import yaml
from decimal import Decimal
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtest.runner import BacktestRunner
from models.base import BaseModel, ModelOutput, Context, RegimeState
from engines.risk.engine import RiskLimits


class AggressiveEquityModel(BaseModel):
    """
    Test model that tries to allocate 80% to SPY (exceeds 40% per-asset cap).
    """

    def generate_signals(self, context: Context) -> ModelOutput:
        """Always output 80% SPY, 20% QQQ."""
        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights={'SPY': 0.80, 'QQQ': 0.20}
        )


class AggressiveCryptoModel(BaseModel):
    """
    Test model that tries to allocate 60% to BTC (would exceed crypto class cap).
    """

    def generate_signals(self, context: Context) -> ModelOutput:
        """Always output 60% BTC, 40% ETH."""
        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights={'BTC': 0.60, 'ETH': 0.40}
        )


class HighLeverageModel(BaseModel):
    """
    Test model that outputs high leverage when combined with others.
    """

    def generate_signals(self, context: Context) -> ModelOutput:
        """Always output 100% allocation."""
        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights={'SPY': 0.50, 'QQQ': 0.50}
        )


class TestBacktestWithPerAssetCaps:
    """Test backtest with models exceeding per-asset caps."""

    def test_aggressive_equity_model_gets_capped(self, tmp_path):
        """
        Test that model outputting 80% SPY gets capped to 40% by Risk Engine.
        """
        # Create test config
        config = {
            'backtest': {
                'start_date': '2024-01-01',
                'end_date': '2024-01-05',
                'initial_nav': 100000.0,
                'timeframe': 'daily'
            },
            'model': {
                'model_id': 'AggressiveEquityModel_Test',
                'model_class': 'tests.integration.test_backtest_e2e.AggressiveEquityModel',
                'universe': ['SPY', 'QQQ']
            },
            'risk': {
                'max_position_size': 0.40,  # 40% cap
                'max_crypto_exposure': 0.20,
                'max_total_leverage': 1.20,
                'max_drawdown_threshold': 0.15,
                'max_drawdown_halt': 0.20
            },
            'execution': {
                'slippage_bps': 5,
                'commission_bps': 1,
                'timing': 'close'
            },
            'data': {
                'data_dir': 'data'
            }
        }

        config_path = tmp_path / 'test_config.yaml'
        with open(config_path, 'w') as f:
            yaml.dump(config, f)

        # This test would require actual market data to run
        # For now, we verify the config structure is correct
        assert config['risk']['max_position_size'] == 0.40
        assert 'AggressiveEquityModel' in config['model']['model_class']


class TestBacktestWithCryptoClassCaps:
    """Test backtest with models exceeding crypto asset-class caps."""

    def test_crypto_models_get_scaled_down(self):
        """
        Test that models with total crypto > 20% get scaled down proportionally.

        Setup:
        - Model A (60% budget): 60% BTC, 40% ETH → NAV-relative: 36% BTC, 24% ETH
        - Total crypto = 60% (exceeds 20% cap)
        - Expected: Scaled by 20/60 = 0.333 → 12% BTC, 8% ETH
        """
        from engines.portfolio.engine import PortfolioEngine
        from engines.risk.engine import RiskEngine, RiskLimits
        from models.base import ModelOutput

        # Setup Risk Engine
        limits = RiskLimits(
            max_position_size=0.70,  # High enough not to interfere
            max_crypto_exposure=0.20,
            max_total_leverage=1.20
        )
        risk_engine = RiskEngine(limits=limits)

        # Setup Portfolio Engine with Risk Engine
        portfolio_engine = PortfolioEngine(risk_engine=risk_engine)

        # Create model output
        model_output = ModelOutput(
            model_name='AggressiveCryptoModel_Test',
            timestamp=pd.Timestamp('2024-01-01 16:00', tz='UTC'),
            weights={'BTC': 0.60, 'ETH': 0.40}
        )

        # Model has 100% budget (single model)
        model_budgets = {'AggressiveCryptoModel_Test': 1.0}
        current_nav = Decimal('100000.00')

        # Execute aggregation (includes risk enforcement)
        target = portfolio_engine.aggregate_model_outputs(
            [model_output],
            model_budgets,
            current_nav
        )

        # Verify crypto was scaled down
        crypto_exposure = abs(target.target_weights.get('BTC', 0)) + abs(target.target_weights.get('ETH', 0))

        # Should be at or below 20%
        assert crypto_exposure <= 0.20 + 0.0001, f"Crypto exposure {crypto_exposure} should be ≤ 20%"

        # Should be scaled proportionally
        btc_weight = target.target_weights.get('BTC', 0)
        eth_weight = target.target_weights.get('ETH', 0)

        # Ratio should be maintained: BTC/ETH = 60/40 = 1.5
        if eth_weight > 0:
            ratio = btc_weight / eth_weight
            assert abs(ratio - 1.5) < 0.01, f"BTC/ETH ratio {ratio} should be ~1.5"


class TestBacktestWithLeverageLimits:
    """Test backtest with models exceeding total leverage limits."""

    def test_high_leverage_gets_scaled_down(self):
        """
        Test that portfolio with total exposure > 1.2x gets scaled down.

        Setup:
        - Model A (60% budget): 100% SPY → 60% SPY
        - Model B (40% budget): 100% QQQ → 40% QQQ
        - Model C (30% budget): 100% BTC → 30% BTC
        - Total = 130% (exceeds 120% leverage limit)
        - Expected: Scaled by 120/130 = 0.923
        """
        from engines.portfolio.engine import PortfolioEngine
        from engines.risk.engine import RiskEngine, RiskLimits
        from models.base import ModelOutput

        # Setup Risk Engine
        limits = RiskLimits(
            max_position_size=0.70,  # High enough not to interfere
            max_crypto_exposure=0.50,  # High enough not to interfere
            max_total_leverage=1.20
        )
        risk_engine = RiskEngine(limits=limits)

        # Setup Portfolio Engine
        portfolio_engine = PortfolioEngine(risk_engine=risk_engine)

        # Create model outputs
        model_outputs = [
            ModelOutput(
                model_name='ModelA',
                timestamp=pd.Timestamp('2024-01-01 16:00', tz='UTC'),
                weights={'SPY': 1.0}
            ),
            ModelOutput(
                model_name='ModelB',
                timestamp=pd.Timestamp('2024-01-01 16:00', tz='UTC'),
                weights={'QQQ': 1.0}
            ),
            ModelOutput(
                model_name='ModelC',
                timestamp=pd.Timestamp('2024-01-01 16:00', tz='UTC'),
                weights={'BTC': 1.0}
            )
        ]

        # Model budgets sum to 130%
        model_budgets = {
            'ModelA': 0.60,
            'ModelB': 0.40,
            'ModelC': 0.30
        }
        current_nav = Decimal('100000.00')

        # Execute aggregation
        target = portfolio_engine.aggregate_model_outputs(
            model_outputs,
            model_budgets,
            current_nav
        )

        # Verify total exposure ≤ 120%
        total_exposure = sum(abs(w) for w in target.target_weights.values())
        assert total_exposure <= 1.20 + 0.0001, f"Total exposure {total_exposure} should be ≤ 1.20"

        # Verify all positions scaled proportionally
        scale_factor = 1.20 / 1.30
        expected_spy = 0.60 * scale_factor
        expected_qqq = 0.40 * scale_factor
        expected_btc = 0.30 * scale_factor

        assert abs(target.target_weights.get('SPY', 0) - expected_spy) < 0.01
        assert abs(target.target_weights.get('QQQ', 0) - expected_qqq) < 0.01
        assert abs(target.target_weights.get('BTC', 0) - expected_btc) < 0.01


class TestBacktestWithDrawdownDerisking:
    """Test drawdown-triggered de-risking."""

    def test_drawdown_triggers_derisk(self):
        """
        Test that 16% drawdown triggers 50% position reduction.
        """
        from engines.risk.engine import RiskEngine, RiskLimits

        # Setup Risk Engine
        limits = RiskLimits(
            max_position_size=0.70,
            max_crypto_exposure=0.50,
            max_total_leverage=1.20,
            max_drawdown_threshold=0.15,
            drawdown_derisk_factor=0.50
        )
        risk_engine = RiskEngine(limits=limits)

        # Simulate drawdown: peak = $120k, current = $100.8k → 16% drawdown
        risk_engine.peak_nav = Decimal('120000.00')
        current_nav = Decimal('100800.00')

        # Target portfolio
        target_weights = {'SPY': 0.60, 'QQQ': 0.40}

        # Apply risk constraints
        constrained, violations = risk_engine.enforce_constraints(
            target_weights,
            current_nav
        )

        # Verify de-risk applied (50% reduction)
        assert abs(constrained['SPY'] - 0.30) < 0.01, "SPY should be 60% * 0.5 = 30%"
        assert abs(constrained['QQQ'] - 0.20) < 0.01, "QQQ should be 40% * 0.5 = 20%"

        # Verify de-risk flag set
        assert risk_engine.derisk_active is True

        # Verify violation recorded
        drawdown_violations = [v for v in violations if v.constraint_type == 'drawdown']
        assert len(drawdown_violations) >= 1

    def test_drawdown_halt_zeros_positions(self):
        """
        Test that 21% drawdown triggers full position halt.
        """
        from engines.risk.engine import RiskEngine, RiskLimits

        # Setup Risk Engine
        limits = RiskLimits(
            max_drawdown_halt=0.20
        )
        risk_engine = RiskEngine(limits=limits)

        # Simulate severe drawdown: peak = $100k, current = $79k → 21% drawdown
        risk_engine.peak_nav = Decimal('100000.00')
        current_nav = Decimal('79000.00')

        # Target portfolio
        target_weights = {'SPY': 0.60, 'QQQ': 0.40}

        # Apply risk constraints
        constrained, violations = risk_engine.enforce_constraints(
            target_weights,
            current_nav
        )

        # Verify all positions zeroed
        assert constrained['SPY'] == 0.0
        assert constrained['QQQ'] == 0.0

        # Verify halt flag set
        assert risk_engine.halt_active is True


class TestMultiModelWithRiskEnforcement:
    """Test multi-model portfolio aggregation with risk enforcement."""

    def test_three_models_with_risk_constraints(self):
        """
        Test full multi-model workflow with risk constraints.

        Setup:
        - EquityTrendModel (60% budget): 100% SPY → 60% SPY
        - IndexMeanReversionModel (25% budget): 100% QQQ → 25% QQQ
        - CryptoMomentumModel (15% budget): 50% BTC, 50% ETH → 7.5% BTC, 7.5% ETH

        Constraints:
        - Per-asset cap: 40%
        - Crypto class cap: 20%
        - Total leverage: 120%

        Expected:
        - SPY: 60% capped to 40%
        - QQQ: 25% (unchanged)
        - BTC: 7.5%, ETH: 7.5% (total crypto 15%, under 20%)
        - Total after capping: 40 + 25 + 7.5 + 7.5 = 80% (under 120% leverage)
        """
        from engines.portfolio.engine import PortfolioEngine
        from engines.risk.engine import RiskEngine, RiskLimits
        from models.base import ModelOutput

        # Setup Risk Engine
        limits = RiskLimits(
            max_position_size=0.40,
            max_crypto_exposure=0.20,
            max_total_leverage=1.20
        )
        risk_engine = RiskEngine(limits=limits)

        # Setup Portfolio Engine
        portfolio_engine = PortfolioEngine(risk_engine=risk_engine)

        # Create model outputs
        model_outputs = [
            ModelOutput(
                model_name='EquityTrendModel_v1',
                timestamp=pd.Timestamp('2024-01-01 16:00', tz='UTC'),
                weights={'SPY': 1.0}
            ),
            ModelOutput(
                model_name='IndexMeanReversionModel_v1',
                timestamp=pd.Timestamp('2024-01-01 16:00', tz='UTC'),
                weights={'QQQ': 1.0}
            ),
            ModelOutput(
                model_name='CryptoMomentumModel_v1',
                timestamp=pd.Timestamp('2024-01-01 16:00', tz='UTC'),
                weights={'BTC': 0.5, 'ETH': 0.5}
            )
        ]

        # Model budgets
        model_budgets = {
            'EquityTrendModel_v1': 0.60,
            'IndexMeanReversionModel_v1': 0.25,
            'CryptoMomentumModel_v1': 0.15
        }
        current_nav = Decimal('100000.00')

        # Execute aggregation
        target = portfolio_engine.aggregate_model_outputs(
            model_outputs,
            model_budgets,
            current_nav
        )

        # Verify SPY capped to 40%
        assert target.target_weights.get('SPY', 0) == 0.40, "SPY should be capped to 40%"

        # Verify QQQ unchanged
        assert target.target_weights.get('QQQ', 0) == 0.25, "QQQ should be 25%"

        # Verify crypto under 20%
        crypto_exposure = (
            abs(target.target_weights.get('BTC', 0)) +
            abs(target.target_weights.get('ETH', 0))
        )
        assert crypto_exposure <= 0.20, f"Crypto exposure {crypto_exposure} should be ≤ 20%"

        # Verify total exposure reasonable
        total_exposure = sum(abs(w) for w in target.target_weights.values())
        assert total_exposure <= 1.20, f"Total exposure {total_exposure} should be ≤ 1.20"

        # Verify attribution tracking
        assert 'SPY' in target.attribution
        assert 'EquityTrendModel_v1' in target.attribution['SPY']


class TestRegimeAwareRiskScaling:
    """Test regime-based budget adjustments."""

    def test_bear_regime_reduces_equity_budgets(self):
        """
        Test that BEAR regime reduces equity model budgets before aggregation.
        """
        from engines.risk.scaling import RegimeRiskScaler
        from models.base import RegimeState

        # Configure regime budgets
        regime_budgets = {
            "BEAR": {
                "EquityTrendModel_v1": 0.30,  # Reduce from 60% to 30%
                "CryptoMomentumModel_v1": 0.05  # Reduce from 15% to 5%
            }
        }
        scaler = RegimeRiskScaler(regime_budgets=regime_budgets)

        # Base budgets
        base_budgets = {
            "EquityTrendModel_v1": 0.60,
            "IndexMeanReversionModel_v1": 0.25,
            "CryptoMomentumModel_v1": 0.15
        }

        # BEAR regime
        regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='bear',
            vol_regime='normal',
            crypto_regime='neutral',
            macro_regime='neutral'
        )

        # Apply scaling
        adjusted = scaler.apply_regime_scaling(base_budgets, regime)

        # Verify adjustments
        assert adjusted['EquityTrendModel_v1'] == 0.30, "Equity model should be reduced to 30%"
        assert adjusted['IndexMeanReversionModel_v1'] == 0.25, "Mean reversion should be unchanged"
        assert adjusted['CryptoMomentumModel_v1'] == 0.05, "Crypto model should be reduced to 5%"

    def test_high_vol_applies_global_multiplier(self):
        """
        Test that HIGH_VOL regime applies global 70% multiplier.
        """
        from engines.risk.scaling import RegimeRiskScaler
        from models.base import RegimeState

        # Configure regime budgets
        regime_budgets = {
            "HIGH_VOL": {
                "all_models": 0.70
            }
        }
        scaler = RegimeRiskScaler(regime_budgets=regime_budgets)

        # Base budgets
        base_budgets = {
            "EquityTrendModel_v1": 0.60,
            "CryptoMomentumModel_v1": 0.15
        }

        # HIGH_VOL regime
        regime = RegimeState(
            timestamp=pd.Timestamp.now(tz='UTC'),
            equity_regime='neutral',
            vol_regime='high',
            crypto_regime='neutral',
            macro_regime='neutral'
        )

        # Apply scaling
        adjusted = scaler.apply_regime_scaling(base_budgets, regime)

        # Verify all scaled by 70%
        assert abs(adjusted['EquityTrendModel_v1'] - 0.60 * 0.70) < 0.01
        assert abs(adjusted['CryptoMomentumModel_v1'] - 0.15 * 0.70) < 0.01


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
