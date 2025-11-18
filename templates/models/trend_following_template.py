"""
{MODEL_NAME}

Trend-following strategy based on moving averages and momentum.

TEMPLATE PLACEHOLDERS:
- {MODEL_NAME}: Name of the model class
- {MODEL_ID}: Unique model identifier
- {DESCRIPTION}: Strategy description
- {MA_PERIOD}: Moving average period (days)
- {MOMENTUM_PERIOD}: Momentum lookback period (days)
- {MOMENTUM_THRESHOLD}: Minimum momentum to enter

HOW TO USE:
    python3 -m backtest.cli create-model \
        --template trend_following \
        --name MyTrendFollower \
        --params "ma_period=200,momentum_period=120"
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class {MODEL_NAME}(BaseModel):
    """
    {DESCRIPTION}

    Strategy:
    - LONG when price > {MA_PERIOD}D MA AND momentum > {MOMENTUM_THRESHOLD}
    - Equal weight across all assets meeting criteria
    - Cash when no assets meet criteria
    """

    def __init__(
        self,
        model_id: str = "{MODEL_ID}",
        assets: list[str] = None,
        ma_period: int = {MA_PERIOD},
        momentum_period: int = {MOMENTUM_PERIOD},
        momentum_threshold: float = {MOMENTUM_THRESHOLD},
        equal_weight: bool = True
    ):
        """
        Initialize {MODEL_NAME}.

        Args:
            model_id: Unique model identifier
            assets: List of assets to trade
            ma_period: Moving average period
            momentum_period: Momentum lookback period
            momentum_threshold: Minimum momentum to enter
            equal_weight: Equal weight positions (vs momentum-weighted)
        """
        self.assets = assets or ["SPY", "QQQ"]
        self.model_id = model_id
        self.ma_period = ma_period
        self.momentum_period = momentum_period
        self.momentum_threshold = momentum_threshold
        self.equal_weight = equal_weight

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.assets
        )

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on trend-following logic.

        Returns:
            ModelOutput with target weights
        """
        weights = {}
        candidates = []

        for asset in self.assets:
            if asset not in context.asset_features:
                weights[asset] = 0.0
                continue

            features = context.asset_features[asset]

            # Check if we have enough data
            if len(features) < max(self.ma_period, self.momentum_period) + 1:
                weights[asset] = 0.0
                continue

            # Get current price and moving average
            current_price = features['close'].iloc[-1]
            ma = features['close'].rolling(self.ma_period).mean().iloc[-1]

            # Calculate momentum
            past_price = features['close'].iloc[-(self.momentum_period + 1)]
            momentum = (current_price - past_price) / past_price if past_price != 0 else 0

            # Check trend conditions
            if current_price > ma and momentum > self.momentum_threshold:
                candidates.append((asset, momentum))
            else:
                weights[asset] = 0.0

        # Allocate to candidates
        if len(candidates) > 0:
            if self.equal_weight:
                # Equal weight
                weight_per_asset = 1.0 / len(candidates)
                for asset, _ in candidates:
                    weights[asset] = weight_per_asset
            else:
                # Momentum-weighted
                total_momentum = sum(mom for _, mom in candidates)
                if total_momentum > 0:
                    for asset, momentum in candidates:
                        weights[asset] = max(0, momentum) / total_momentum
                else:
                    # Fall back to equal weight if all momentum negative
                    weight_per_asset = 1.0 / len(candidates)
                    for asset, _ in candidates:
                        weights[asset] = weight_per_asset

        # Ensure all assets have weights
        for asset in self.assets:
            if asset not in weights:
                weights[asset] = 0.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(model_id='{self.model_id}', "
            f"assets={self.assets}, ma_period={self.ma_period}, "
            f"momentum_period={self.momentum_period})"
        )
