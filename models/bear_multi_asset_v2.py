"""
BearMultiAsset_v2

Bear market specialist using multi-asset approach with relative momentum.

Version 2 Improvements:
- Switched from absolute to RELATIVE momentum - always hold top N regardless of sign
- No min_momentum threshold - always stay invested in "least bad" assets
- SHY explicitly in universe (not just fallback)
- Faster momentum period (40 vs 60 days) for quicker response
- Fallback changed from 50/50 TLT/SHY to 100% SHY (only for missing data)
- Avoids the v1 trap of going to TLT during 2022 crash

Strategy:
- Expands beyond equities to include bonds, gold, dollar, defensive sectors, and cash
- Universe: TLT (bonds), IEF (intermediate bonds), GLD (gold), UUP (dollar), XLU, XLP, XLV, SHY (cash)
- Ranks ALL assets by momentum and holds top N performers
- NEW: Always stays invested in top N assets, even if momentum is negative
- NEW: Pure relative momentum - no threshold filtering
- Falls back to 100% SHY only when insufficient data
- Rebalances every N days (default 14)

Design Rationale:
- Bear markets often see rotation into non-equity safe havens
- V2 recognizes that in bear markets, SOMETHING is always least bad
- Relative momentum keeps us invested rather than sitting in crashing bonds
- Including SHY in main universe lets cash compete fairly
- 2022 taught us that absolute thresholds can force us into the worst assets
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearMultiAsset_v2(BaseModel):
    """
    Bear market multi-asset rotation v2 - relative momentum approach.

    Only generates weights when equity_regime == 'bear'.
    V2 uses relative momentum to always stay invested in least-bad assets.
    """

    def __init__(
        self,
        model_id: str = "BearMultiAsset_v2",
        multi_assets: list[str] = None,
        cash_asset: str = "SHY",
        momentum_period: int = 40,  # V2: Faster response (was 60)
        top_n: int = 3,
        rebalance_days: int = 14
    ):
        """
        Initialize Bear Multi-Asset Model v2.

        Args:
            model_id: Unique model identifier
            multi_assets: List of multi-asset ETFs (includes SHY)
            cash_asset: Cash ETF for data fallback only (default: SHY)
            momentum_period: Lookback period for momentum (default: 40 days - faster than v1)
            top_n: Number of top assets to hold (default: 3)
            rebalance_days: Days between rebalances (default: 14)

        Note: V2 removes min_momentum parameter - uses pure relative momentum
        """
        # V2: SHY explicitly included in main universe
        self.multi_assets = multi_assets or [
            'TLT',   # Long-term Treasury bonds
            'IEF',   # Intermediate-term Treasury bonds
            'GLD',   # Gold
            'UUP',   # US Dollar Index
            'XLU',   # Utilities (defensive sector)
            'XLP',   # Consumer Staples (defensive sector)
            'XLV',   # Healthcare (defensive sector)
            'SHY'    # V2: Short-term Treasury (cash) - now in main universe!
        ]

        self.cash_asset = cash_asset

        # Ensure SHY is in the multi_assets list
        if self.cash_asset not in self.multi_assets:
            self.multi_assets.append(self.cash_asset)

        self.all_assets = self.multi_assets
        self.assets = self.all_assets  # Required for BacktestRunner to load data

        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.rebalance_days = rebalance_days
        # V2: No min_momentum parameter - pure relative momentum

        super().__init__(
            name=model_id,
            version="2.0.0",  # V2
            universe=self.all_assets
        )

        # Track last rebalance date
        self.last_rebalance: Optional[pd.Timestamp] = None

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights - ONLY in bear markets.
        V2: Uses relative momentum to always stay invested.

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

        # Calculate momentum for each multi-asset
        asset_momentum = {}

        for asset in self.multi_assets:
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

        # Need at least top_n assets with data to proceed
        if len(asset_momentum) < self.top_n:
            # Insufficient data - use cash fallback
            # V2: Changed from 50/50 TLT/SHY to 100% SHY
            weights[self.cash_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Sort assets by momentum (descending - best first)
        ranked_assets = sorted(asset_momentum.items(), key=lambda x: x[1], reverse=True)

        # V2: ALWAYS take top N assets, regardless of momentum sign
        # This is pure relative momentum - we hold the "least bad" assets
        top_assets = ranked_assets[:self.top_n]

        # Equal weight across top N assets
        # No filtering by threshold - we always stay invested
        weight_per_asset = 1.0 / len(top_assets)
        for asset, momentum_value in top_assets:
            weights[asset] = weight_per_asset
            # Could log: f"Holding {asset} with momentum {momentum_value:.2%}"

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"BearMultiAsset_v2(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"rebalance_days={self.rebalance_days})"
        )