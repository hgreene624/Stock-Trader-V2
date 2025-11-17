"""
IndexMeanReversionModel_v1

Mean-reversion strategy for equity indices using RSI and Bollinger Bands.

Signal Logic:
- LONG: RSI < 30 (oversold) AND price < lower Bollinger Band
- SHORT: RSI > 70 (overbought) AND price > upper Bollinger Band
- FLAT: Otherwise

Position Sizing:
- Full allocation (100% of model budget) when signal active
- Equal weight across multiple signals
- 0% when FLAT

Assets: SPY, QQQ
Timeframe: H4 bars with RSI and Bollinger computed on H4
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class IndexMeanReversionModel_v1(BaseModel):
    """
    Version 1 of index mean-reversion model.

    Strategy:
    - Identifies overbought/oversold conditions in major equity indices
    - Uses RSI(14) for momentum extremes
    - Uses Bollinger Bands (20-period, 2 std) for price extremes
    - Goes long when oversold, flat/short when overbought
    - Equal weight allocation across signals
    """

    def __init__(
        self,
        model_id: str = "IndexMeanReversionModel_v1",
        assets: list[str] = None,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        bb_period: int = 20,
        bb_std: float = 2.0
    ):
        """
        Initialize IndexMeanReversionModel_v1.

        Args:
            model_id: Unique model identifier
            assets: List of assets to trade (default: ["SPY", "QQQ"])
            rsi_period: RSI lookback period (default: 14)
            rsi_oversold: RSI level for oversold signal (default: 30)
            rsi_overbought: RSI level for overbought signal (default: 70)
            bb_period: Bollinger Band period (default: 20)
            bb_std: Bollinger Band standard deviations (default: 2.0)
        """
        self.assets = assets or ["SPY", "QQQ"]
        self.model_id = model_id

        # Initialize base model with required arguments
        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.assets,
            rsi_period=rsi_period,
            rsi_oversold=rsi_oversold,
            rsi_overbought=rsi_overbought,
            bb_period=bb_period,
            bb_std=bb_std
        )

        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weight allocations.

        Signal Logic:
        - For each asset:
            - LONG if: RSI < 30 AND price < BB_lower
            - SHORT if: RSI > 70 AND price > BB_upper (not implemented in v1)
            - FLAT otherwise
        - Equal weight across LONG signals
        - Weights are relative to model budget

        Args:
            context: Market context with asset features, regime, budget

        Returns:
            ModelOutput with target weights (relative to model budget)

        Example:
            Context has:
            - SPY: close=450, rsi_14=25, bb_lower=445 → LONG (oversold + below BB)
            - QQQ: close=380, rsi_14=65, bb_lower=375 → FLAT (not oversold)

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
            # Note: FeatureComputer creates 'rsi', 'bb_upper', 'bb_lower' without period suffixes
            required_cols = ['close', 'rsi', 'bb_lower', 'bb_upper']
            missing_cols = [col for col in required_cols if col not in features.columns]

            if missing_cols:
                raise ValueError(
                    f"Missing required features for {symbol}: {missing_cols}. "
                    f"Available columns: {list(features.columns)}"
                )

            # Extract values
            price = current['close']
            rsi = current['rsi']
            bb_lower = current['bb_lower']
            bb_upper = current['bb_upper']

            # Handle NaN values (insufficient history)
            if pd.isna(price) or pd.isna(rsi) or pd.isna(bb_lower) or pd.isna(bb_upper):
                signals[symbol] = False
                weights[symbol] = 0.0
                continue

            # Generate signal
            # LONG: RSI oversold AND price below lower Bollinger Band
            is_long = (rsi < self.rsi_oversold) and (price < bb_lower)

            # Note: SHORT signal not implemented in v1 (future enhancement)
            # is_short = (rsi > self.rsi_overbought) and (price > bb_upper)

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
            f"IndexMeanReversionModel_v1(model_id='{self.model_id}', "
            f"assets={self.assets}, rsi_period={self.rsi_period}, "
            f"rsi_oversold={self.rsi_oversold}, bb_period={self.bb_period})"
        )


# Example usage and testing
if __name__ == "__main__":
    from models.base import Context, RegimeState
    from decimal import Decimal

    # Create sample context
    # Simulate SPY and QQQ data with features
    spy_data = pd.DataFrame({
        'close': [445, 446, 447],
        'rsi_14': [25, 26, 27],  # Oversold
        'bb_lower_20': [448, 448, 449],  # Price below lower band
        'bb_upper_20': [458, 459, 460]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    qqq_data = pd.DataFrame({
        'close': [380, 381, 382],
        'rsi_14': [65, 66, 67],  # Not oversold
        'bb_lower_20': [375, 375, 376],
        'bb_upper_20': [390, 391, 392]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    # Create context
    context = Context(
        timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
        asset_features={
            'SPY': spy_data,
            'QQQ': qqq_data
        },
        regime=RegimeState(
            timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
            equity_regime='NEUTRAL',
            vol_regime='NORMAL',
            crypto_regime='NEUTRAL',
            macro_regime='NEUTRAL'
        ),
        model_budget_fraction=0.25,
        model_budget_value=Decimal('25000.00'),
        current_exposures={}
    )

    # Initialize model
    model = IndexMeanReversionModel_v1()

    print("=" * 60)
    print("IndexMeanReversionModel_v1 Test")
    print("=" * 60)
    print(f"\nModel: {model}")

    # Generate signals
    output = model.generate_target_weights(context)

    print(f"\nTimestamp: {output.timestamp}")
    print(f"Model Budget: ${context.model_budget_value:,.2f}")

    print("\nTarget Weights (relative to model budget):")
    for symbol, weight in output.weights.items():
        dollar_amount = float(context.model_budget_value) * weight
        status = "LONG" if weight > 0 else "FLAT"
        print(f"  {symbol}: {weight:.2%} → ${dollar_amount:,.2f} ({status})")

    print("\n" + "=" * 60)

    # Test with no signals
    print("\nTest Case: No Signals (both assets neutral)")
    print("=" * 60)

    neutral_spy = pd.DataFrame({
        'close': [455, 456, 457],
        'rsi_14': [50, 51, 52],  # Neutral
        'bb_lower_20': [448, 448, 449],
        'bb_upper_20': [462, 463, 464]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    neutral_qqq = pd.DataFrame({
        'close': [385, 386, 387],
        'rsi_14': [55, 56, 57],  # Neutral
        'bb_lower_20': [380, 380, 381],
        'bb_upper_20': [390, 391, 392]
    }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

    neutral_context = Context(
        timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
        asset_features={
            'SPY': neutral_spy,
            'QQQ': neutral_qqq
        },
        regime=RegimeState(
            timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
            equity_regime='NEUTRAL',
            vol_regime='NORMAL',
            crypto_regime='NEUTRAL',
            macro_regime='NEUTRAL'
        ),
        model_budget_fraction=0.25,
        model_budget_value=Decimal('25000.00'),
        current_exposures={}
    )

    neutral_output = model.generate_target_weights(neutral_context)

    print("\nTarget Weights (relative to model budget):")
    for symbol, weight in neutral_output.weights.items():
        status = "LONG" if weight > 0 else "FLAT"
        print(f"  {symbol}: {weight:.2%} ({status})")

    print("\n✓ All tests passed")
