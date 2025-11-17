"""
EquityTrendModel_v1

Momentum-based trend following strategy for equity indices (SPY, QQQ).

Signal Logic:
- LONG: Price > 200D MA AND 6-12M momentum > 0
- FLAT: Otherwise

Position Sizing:
- Full allocation (100% of model budget) when LONG
- 0% when FLAT

Assets: SPY, QQQ (equal weight when both signals agree)
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class EquityTrendModel_v1(BaseModel):
    """
    Version 1 of equity trend-following model.

    Strategy:
    - Follows long-term trends in major equity indices
    - Uses 200-day moving average as trend filter
    - Uses 6-12 month momentum for signal confirmation
    - Equal weight allocation across signals
    """

    def __init__(
        self,
        model_id: str = "EquityTrendModel_v1",
        assets: list[str] = None,
        ma_period: int = 200,
        momentum_period: int = 120,  # ~6 months of daily bars
        momentum_threshold: float = 0.0
    ):
        """
        Initialize EquityTrendModel_v1.

        Args:
            model_id: Unique model identifier
            assets: List of assets to trade (default: ["SPY", "QQQ"])
            ma_period: Moving average period in days (default: 200)
            momentum_period: Momentum lookback period in days (default: 120 ≈ 6M)
            momentum_threshold: Minimum momentum to be LONG (default: 0.0)
        """
        self.assets = assets or ["SPY", "QQQ"]
        self.model_id = model_id  # Store for compatibility

        # Initialize base model with required arguments
        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.assets,
            ma_period=ma_period,
            momentum_period=momentum_period,
            momentum_threshold=momentum_threshold
        )

        self.ma_period = ma_period
        self.momentum_period = momentum_period
        self.momentum_threshold = momentum_threshold

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weight allocations.

        Signal Logic:
        - For each asset:
            - LONG if: price > MA(200D) AND momentum(120D) > 0
            - FLAT otherwise
        - Equal weight across LONG signals
        - Weights are relative to model budget

        Args:
            context: Market context with asset features, regime, budget

        Returns:
            ModelOutput with target weights (relative to model budget)

        Example:
            Context has:
            - SPY: price=450, ma_200=440, momentum_120=0.08 → LONG
            - QQQ: price=380, ma_200=390, momentum_120=-0.05 → FLAT

            Output weights (relative to model budget):
            - SPY: 1.0 (100% of model budget to SPY)
            - QQQ: 0.0
        """
        signals = {}
        weights = {}

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

            # Check required columns
            required_cols = ['close', f'daily_ma_{self.ma_period}', f'daily_momentum_{self.momentum_period}']
            missing_cols = [col for col in required_cols if col not in features.columns]

            if missing_cols:
                raise ValueError(
                    f"Missing required features for {symbol}: {missing_cols}. "
                    f"Available columns: {list(features.columns)}"
                )

            # Extract values
            price = current['close']
            ma_200 = current[f'daily_ma_{self.ma_period}']
            momentum = current[f'daily_momentum_{self.momentum_period}']

            # Handle NaN values (insufficient history)
            if pd.isna(price) or pd.isna(ma_200) or pd.isna(momentum):
                signals[symbol] = False
                weights[symbol] = 0.0
                continue

            # Generate signal
            # LONG: price > MA AND momentum > threshold
            is_long = (price > ma_200) and (momentum > self.momentum_threshold)

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
            f"EquityTrendModel_v1(model_id='{self.model_id}', "
            f"assets={self.assets}, ma_period={self.ma_period}, "
            f"momentum_period={self.momentum_period})"
        )


# Example usage and testing
if __name__ == "__main__":
    from models.base import Context, RegimeState
    from decimal import Decimal

    # Create sample context
    # Simulate SPY and QQQ data with features
    spy_data = pd.DataFrame({
        'close': [450, 452, 455],
        'daily_ma_200': [440, 441, 442],
        'daily_momentum_120': [0.08, 0.09, 0.10]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    qqq_data = pd.DataFrame({
        'close': [380, 378, 376],
        'daily_ma_200': [390, 390, 391],
        'daily_momentum_120': [-0.05, -0.06, -0.07]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    # Create context
    context = Context(
        timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
        asset_features={
            'SPY': spy_data,
            'QQQ': qqq_data
        },
        regime=RegimeState(
            equity='BULL',
            volatility='NORMAL',
            crypto='NEUTRAL',
            macro='EXPANSION'
        ),
        model_budget_fraction=0.30,
        model_budget_value=Decimal('30000.00')
    )

    # Initialize model
    model = EquityTrendModel_v1()

    print("=" * 60)
    print("EquityTrendModel_v1 Test")
    print("=" * 60)
    print(f"\nModel: {model}")

    # Generate signals
    output = model.generate_target_weights(context)

    print(f"\nTimestamp: {output.timestamp}")
    print(f"Model Budget: ${context.model_budget_value:,.2f}")

    print("\nSignals:")
    for symbol, signal in output.metadata['signals'].items():
        print(f"  {symbol}: {'LONG' if signal else 'FLAT'}")

    print(f"\nActive Signals: {output.metadata['active_signals']}")

    print("\nTarget Weights (relative to model budget):")
    for symbol, weight in output.target_weights.items():
        print(f"  {symbol}: {weight:.2%} → ${float(context.model_budget_value) * weight:,.2f}")

    print("\n" + "=" * 60)

    # Test with no signals
    print("\nTest Case: No Signals (both assets below MA)")
    print("=" * 60)

    bear_spy = pd.DataFrame({
        'close': [420, 418, 415],
        'daily_ma_200': [440, 441, 442],
        'daily_momentum_120': [-0.08, -0.09, -0.10]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    bear_qqq = pd.DataFrame({
        'close': [360, 358, 356],
        'daily_ma_200': [390, 390, 391],
        'daily_momentum_120': [-0.15, -0.16, -0.17]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    bear_context = Context(
        timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
        asset_features={
            'SPY': bear_spy,
            'QQQ': bear_qqq
        },
        regime=RegimeState(
            equity='BEAR',
            volatility='HIGH',
            crypto='NEUTRAL',
            macro='CONTRACTION'
        ),
        model_budget_fraction=0.30,
        model_budget_value=Decimal('30000.00')
    )

    bear_output = model.generate_target_weights(bear_context)

    print("\nSignals:")
    for symbol, signal in bear_output.metadata['signals'].items():
        print(f"  {symbol}: {'LONG' if signal else 'FLAT'}")

    print(f"\nActive Signals: {bear_output.metadata['active_signals']}")

    print("\nTarget Weights (relative to model budget):")
    for symbol, weight in bear_output.target_weights.items():
        print(f"  {symbol}: {weight:.2%}")

    print("\n✓ All tests passed")
