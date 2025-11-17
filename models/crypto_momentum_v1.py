"""
CryptoMomentumModel_v1

Momentum-based strategy for major cryptocurrencies with regime gating.

Signal Logic:
- LONG: 30-60D momentum > 0 AND crypto regime == RISK_ON
- FLAT: Otherwise

Position Sizing:
- Full allocation (100% of model budget) when LONG
- Equal weight across multiple signals
- 0% when FLAT or regime == RISK_OFF

Assets: BTC, ETH
Timeframe: H4 bars with daily momentum features
Regime Gating: Only trades when crypto_regime == RISK_ON
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class CryptoMomentumModel_v1(BaseModel):
    """
    Version 1 of crypto momentum model.

    Strategy:
    - Follows medium-term momentum in major cryptocurrencies
    - Uses 30-60 day momentum for signal generation
    - Regime-aware: only trades when crypto regime is RISK_ON
    - Equal weight allocation across active signals
    - Flat when regime is RISK_OFF (risk management)
    """

    def __init__(
        self,
        model_id: str = "CryptoMomentumModel_v1",
        assets: list[str] = None,
        momentum_short_period: int = 30,  # ~30 days
        momentum_long_period: int = 60,   # ~60 days
        momentum_threshold: float = 0.0,
        regime_gating: bool = True
    ):
        """
        Initialize CryptoMomentumModel_v1.

        Args:
            model_id: Unique model identifier
            assets: List of assets to trade (default: ["BTC", "ETH"])
            momentum_short_period: Short momentum lookback in days (default: 30)
            momentum_long_period: Long momentum lookback in days (default: 60)
            momentum_threshold: Minimum momentum to be LONG (default: 0.0)
            regime_gating: Whether to use crypto regime for filtering (default: True)
        """
        self.assets = assets or ["BTC", "ETH"]
        self.model_id = model_id

        # Initialize base model with required arguments
        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.assets,
            momentum_short_period=momentum_short_period,
            momentum_long_period=momentum_long_period,
            momentum_threshold=momentum_threshold,
            regime_gating=regime_gating
        )

        self.momentum_short_period = momentum_short_period
        self.momentum_long_period = momentum_long_period
        self.momentum_threshold = momentum_threshold
        self.regime_gating = regime_gating

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weight allocations.

        Signal Logic:
        - For each asset:
            - LONG if: momentum_60D > 0 AND crypto_regime == 'RISK_ON'
            - FLAT otherwise
        - If regime_gating enabled and crypto_regime != 'RISK_ON', all weights = 0
        - Equal weight across LONG signals
        - Weights are relative to model budget

        Args:
            context: Market context with asset features, regime, budget

        Returns:
            ModelOutput with target weights (relative to model budget)

        Example:
            Context has crypto_regime = 'RISK_ON':
            - BTC: momentum_60=0.25 → LONG
            - ETH: momentum_60=0.15 → LONG

            Output weights (relative to model budget):
            - BTC: 0.5 (50% of model budget)
            - ETH: 0.5 (50% of model budget)

            Context has crypto_regime = 'RISK_OFF':
            - All weights = 0.0 (regime gate blocks trades)
        """
        signals = {}
        weights = {}

        # Check regime gating first
        if self.regime_gating:
            crypto_regime = context.regime.crypto_regime.upper()

            # Only trade when crypto regime is RISK_ON
            if crypto_regime != 'RISK_ON' and crypto_regime != 'RISK-ON':
                # Regime gate: go flat
                for symbol in self.assets:
                    weights[symbol] = 0.0

                output = ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=weights
                )
                return output

        # Evaluate signal for each asset
        for symbol in self.assets:
            if symbol not in context.asset_features:
                # No data available for this asset
                signals[symbol] = False
                weights[symbol] = 0.0
                continue

            # Get asset features
            features = context.asset_features[symbol]

            # Ensure we have required features
            if len(features) == 0:
                signals[symbol] = False
                weights[symbol] = 0.0
                continue

            # Get current bar (most recent)
            current = features.iloc[-1]

            # Check required columns (use long period momentum as primary signal)
            required_cols = ['close', f'daily_momentum_{self.momentum_long_period}']
            missing_cols = [col for col in required_cols if col not in features.columns]

            if missing_cols:
                raise ValueError(
                    f"Missing required features for {symbol}: {missing_cols}. "
                    f"Available columns: {list(features.columns)}"
                )

            # Extract values
            price = current['close']
            momentum = current[f'daily_momentum_{self.momentum_long_period}']

            # Handle NaN values (insufficient history)
            if pd.isna(price) or pd.isna(momentum):
                signals[symbol] = False
                weights[symbol] = 0.0
                continue

            # Generate signal
            # LONG: momentum > threshold
            is_long = momentum > self.momentum_threshold

            signals[symbol] = is_long

        # Count active signals
        active_signals = sum(signals.values())

        # Allocate equal weight to active signals
        if active_signals > 0:
            weight_per_signal = 1.0 / active_signals

            for symbol in self.assets:
                if signals[symbol]:
                    weights[symbol] = weight_per_signal
                else:
                    weights[symbol] = 0.0
        else:
            # No signals → all weights are 0
            for symbol in self.assets:
                weights[symbol] = 0.0

        # Create ModelOutput
        output = ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

        return output

    def __repr__(self):
        return (
            f"CryptoMomentumModel_v1(model_id='{self.model_id}', "
            f"assets={self.assets}, momentum_period={self.momentum_long_period}, "
            f"regime_gating={self.regime_gating})"
        )


# Example usage and testing
if __name__ == "__main__":
    from models.base import Context, RegimeState
    from decimal import Decimal

    # Test Case 1: RISK_ON regime with positive momentum
    print("=" * 60)
    print("CryptoMomentumModel_v1 Test")
    print("=" * 60)

    btc_data = pd.DataFrame({
        'close': [65000, 66000, 67000],
        'daily_momentum_30': [0.15, 0.16, 0.17],
        'daily_momentum_60': [0.25, 0.26, 0.27]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    eth_data = pd.DataFrame({
        'close': [3500, 3550, 3600],
        'daily_momentum_30': [0.10, 0.11, 0.12],
        'daily_momentum_60': [0.18, 0.19, 0.20]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    # Create context with RISK_ON regime
    risk_on_context = Context(
        timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
        asset_features={
            'BTC': btc_data,
            'ETH': eth_data
        },
        regime=RegimeState(
            timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
            equity_regime='NEUTRAL',
            vol_regime='NORMAL',
            crypto_regime='RISK_ON',  # Favorable crypto regime
            macro_regime='NEUTRAL'
        ),
        model_budget_fraction=0.15,
        model_budget_value=Decimal('15000.00'),
        current_exposures={}
    )

    # Initialize model
    model = CryptoMomentumModel_v1()

    print(f"\nModel: {model}")

    # Generate signals
    output = model.generate_target_weights(risk_on_context)

    print(f"\nTimestamp: {output.timestamp}")
    print(f"Model Budget: ${risk_on_context.model_budget_value:,.2f}")
    print(f"Crypto Regime: {risk_on_context.regime.crypto_regime}")

    print("\nTarget Weights (relative to model budget):")
    for symbol, weight in output.weights.items():
        dollar_amount = float(risk_on_context.model_budget_value) * weight
        status = "LONG" if weight > 0 else "FLAT"
        print(f"  {symbol}: {weight:.2%} → ${dollar_amount:,.2f} ({status})")

    print("\n" + "=" * 60)

    # Test Case 2: RISK_OFF regime (should be flat regardless of momentum)
    print("\nTest Case: RISK_OFF Regime (regime gate blocks trades)")
    print("=" * 60)

    # Same data, but RISK_OFF regime
    risk_off_context = Context(
        timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
        asset_features={
            'BTC': btc_data,
            'ETH': eth_data
        },
        regime=RegimeState(
            timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
            equity_regime='BEAR',
            vol_regime='HIGH',
            crypto_regime='RISK_OFF',  # Unfavorable crypto regime
            macro_regime='RECESSION'
        ),
        model_budget_fraction=0.15,
        model_budget_value=Decimal('15000.00'),
        current_exposures={}
    )

    risk_off_output = model.generate_target_weights(risk_off_context)

    print(f"\nCrypto Regime: {risk_off_context.regime.crypto_regime}")

    print("\nTarget Weights (relative to model budget):")
    for symbol, weight in risk_off_output.weights.items():
        status = "LONG" if weight > 0 else "FLAT"
        print(f"  {symbol}: {weight:.2%} ({status})")

    print("\n" + "=" * 60)

    # Test Case 3: Negative momentum (should be flat)
    print("\nTest Case: Negative Momentum (no signals)")
    print("=" * 60)

    btc_bear = pd.DataFrame({
        'close': [60000, 59000, 58000],
        'daily_momentum_30': [-0.10, -0.11, -0.12],
        'daily_momentum_60': [-0.15, -0.16, -0.17]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    eth_bear = pd.DataFrame({
        'close': [3200, 3150, 3100],
        'daily_momentum_30': [-0.08, -0.09, -0.10],
        'daily_momentum_60': [-0.12, -0.13, -0.14]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    bear_context = Context(
        timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
        asset_features={
            'BTC': btc_bear,
            'ETH': eth_bear
        },
        regime=RegimeState(
            timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
            equity_regime='NEUTRAL',
            vol_regime='NORMAL',
            crypto_regime='RISK_ON',  # Regime allows trading
            macro_regime='NEUTRAL'
        ),
        model_budget_fraction=0.15,
        model_budget_value=Decimal('15000.00'),
        current_exposures={}
    )

    bear_output = model.generate_target_weights(bear_context)

    print(f"\nCrypto Regime: {bear_context.regime.crypto_regime}")

    print("\nTarget Weights (relative to model budget):")
    for symbol, weight in bear_output.weights.items():
        status = "LONG" if weight > 0 else "FLAT"
        print(f"  {symbol}: {weight:.2%} ({status})")

    print("\n✓ All tests passed")
