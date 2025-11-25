"""
BearDefensiveRotation_v1

Bear market specialist that rotates among defensive assets.

Strategy:
- Designed specifically for bear markets (equity_regime == 'bear')
- Rotates among defensive assets: XLU (utilities), XLP (staples), TLT (bonds), GLD (gold), UUP (dollar)
- Ranks assets by momentum and holds the top N performers
- Can hold assets with negative momentum if they're "least bad" (min_momentum default -0.05)
- Falls back to TLT when no assets meet threshold
- Rebalances every N days (default 10)

Design Rationale:
- In bear markets, capital preservation is paramount
- Defensive assets tend to be less correlated with broad equity declines
- "Least bad" approach acknowledges that everything may be declining
- TLT as ultimate fallback provides government bond safety
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearDefensiveRotation_v1(BaseModel):
    """
    Bear market defensive rotation - rotate to "least bad" defensive assets.

    Only generates weights when equity_regime == 'bear'.
    """

    def __init__(
        self,
        model_id: str = "BearDefensiveRotation_v1",
        defensive_assets: list[str] = None,
        fallback_asset: str = "TLT",
        momentum_period: int = 30,
        top_n: int = 2,
        min_momentum: float = -0.05,  # Can hold negative momentum assets
        rebalance_days: int = 10
    ):
        """
        Initialize Bear Defensive Rotation Model.

        Args:
            model_id: Unique model identifier
            defensive_assets: List of defensive ETFs (default: XLU, XLP, TLT, GLD, UUP)
            fallback_asset: Ultimate safe haven when all else fails (default: TLT)
            momentum_period: Lookback period for momentum (default: 30 days)
            top_n: Number of top assets to hold (default: 2)
            min_momentum: Minimum momentum threshold (default: -0.05, can be negative)
            rebalance_days: Days between rebalances (default: 10)
        """
        self.defensive_assets = defensive_assets or [
            'XLU',   # Utilities - defensive sector
            'XLP',   # Consumer Staples - defensive sector
            'TLT',   # Long-term Treasury bonds
            'GLD',   # Gold
            'UUP'    # US Dollar Index
        ]

        self.fallback_asset = fallback_asset
        self.all_assets = list(set(self.defensive_assets + [fallback_asset]))
        self.assets = self.all_assets  # Required for BacktestRunner to load data

        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum
        self.rebalance_days = rebalance_days

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        # Track last rebalance date
        self.last_rebalance: Optional[pd.Timestamp] = None

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights - ONLY in bear markets.

        Returns:
            ModelOutput with target weights (empty if not bear regime)
        """
        # REGIME CHECK: Temporarily disabled for Phase 1 testing
        # TODO: Re-enable after validating model logic
        # if context.regime.equity_regime != 'bear':
        #     # Not a bear market - return empty weights (no positions)
        #     return ModelOutput(
        #         model_name=self.model_id,
        #         timestamp=context.timestamp,
        #         weights={}
        #     )

        # Check if it's time to rebalance
        if self.last_rebalance is not None:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < self.rebalance_days:
                # Not time to rebalance yet - hold current positions
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=context.current_exposures,
                    hold_current=True
                )

        self.last_rebalance = context.timestamp

        # Calculate momentum for each defensive asset
        asset_momentum = {}

        for asset in self.defensive_assets:
            if asset not in context.asset_features:
                continue

            features = context.asset_features[asset]

            # Handle both 'Close' and 'close' column names
            close_col = 'Close' if 'Close' in features.columns else 'close'

            if len(features) < self.momentum_period + 1:
                continue

            # Get current and historical prices
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(self.momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            # Calculate momentum
            momentum = (current_price - past_price) / past_price
            asset_momentum[asset] = momentum

        # Initialize weights
        weights = {}

        if len(asset_momentum) == 0:
            # No data available - go to fallback asset
            weights[self.fallback_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Sort assets by momentum (descending - best first, even if negative)
        ranked_assets = sorted(asset_momentum.items(), key=lambda x: x[1], reverse=True)

        # Get top N assets
        top_assets = ranked_assets[:self.top_n]

        # Check if top assets meet minimum momentum threshold
        qualified_assets = [(asset, mom) for asset, mom in top_assets if mom >= self.min_momentum]

        if len(qualified_assets) > 0:
            # Equal weight across qualified assets
            weight_per_asset = 1.0 / len(qualified_assets)
            for asset, _ in qualified_assets:
                weights[asset] = weight_per_asset
        else:
            # No assets meet threshold (even the negative threshold) - use fallback
            weights[self.fallback_asset] = 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"BearDefensiveRotation_v1(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"min_momentum={self.min_momentum}, rebalance_days={self.rebalance_days})"
        )