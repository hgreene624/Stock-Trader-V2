"""
EquityTrendModel_v1_Daily

Daily bar version of the equity trend-following strategy.

Differences from 4H version:
- Rebalances once per day (at close) instead of every 4H
- Uses same signal logic: LONG if price > MA200 AND momentum > 0
- More data available (full 2020-2024 period)
- Lower transaction costs (fewer rebalances)
- More stable signals (less noise)

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


class EquityTrendModel_v1_Daily(BaseModel):
    """
    Daily version of equity trend-following model.

    Strategy:
    - Follows long-term trends in major equity indices
    - Uses 200-day moving average as trend filter
    - Uses 6-12 month momentum for signal confirmation
    - Equal weight allocation across signals
    - Rebalances once per day (at close)
    """

    def __init__(
        self,
        model_id: str = "EquityTrendModel_v1_Daily",
        assets: list[str] = None,
        ma_period: int = 200,
        momentum_period: int = 120,  # ~6 months of daily bars
        momentum_threshold: float = 0.0
    ):
        """
        Initialize EquityTrendModel_v1_Daily.

        Args:
            model_id: Unique model identifier
            assets: List of assets to trade (default: ["SPY", "QQQ"])
            ma_period: Moving average period in days (default: 200)
            momentum_period: Momentum lookback period in days (default: 120 ≈ 6M)
            momentum_threshold: Minimum momentum to be LONG (default: 0.0)
        """
        self.assets = assets or ["SPY", "QQQ"]
        self.model_id = model_id

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
            required_cols = ['close', f'ma_{self.ma_period}', f'momentum_{self.momentum_period}']
            missing_cols = [col for col in required_cols if col not in features.columns]

            if missing_cols:
                raise ValueError(
                    f"Missing required features for {symbol}: {missing_cols}. "
                    f"Available columns: {list(features.columns)}"
                )

            # Extract values
            price = current['close']
            ma_200 = current[f'ma_{self.ma_period}']
            momentum = current[f'momentum_{self.momentum_period}']

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
            f"EquityTrendModel_v1_Daily(model_id='{self.model_id}', "
            f"assets={self.assets}, ma_period={self.ma_period}, "
            f"momentum_period={self.momentum_period})"
        )
