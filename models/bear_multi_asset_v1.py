"""
BearMultiAsset_v1

Bear market specialist using multi-asset approach.

Strategy:
- Expands beyond equities to include bonds, gold, dollar, and defensive sectors
- Universe: TLT (bonds), IEF (intermediate bonds), GLD (gold), UUP (dollar), XLU, XLP, XLV
- Ranks all assets by momentum and holds top performers
- Only holds assets with positive momentum (min_momentum=0.0)
- Falls back to 50% TLT + 50% SGOV when no assets have positive momentum
- Rebalances every N days (default 14)

Design Rationale:
- Bear markets often see rotation into non-equity safe havens
- Different bear markets favor different assets (2008: bonds, 2022: dollar)
- Multi-asset approach captures wherever strength emerges
- Positive momentum filter avoids catching falling knives
- TLT/SGOV fallback provides bond safety with duration diversification
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearMultiAsset_v1(BaseModel):
    """
    Bear market multi-asset rotation - expand beyond equities for safety.

    Only generates weights when equity_regime == 'bear'.
    """

    def __init__(
        self,
        model_id: str = "BearMultiAsset_v1",
        multi_assets: list[str] = None,
        bond_fallback: str = "TLT",
        cash_fallback: str = "SGOV",
        momentum_period: int = 60,
        top_n: int = 3,
        min_momentum: float = 0.0,  # Only positive momentum
        rebalance_days: int = 14
    ):
        """
        Initialize Bear Multi-Asset Model.

        Args:
            model_id: Unique model identifier
            multi_assets: List of multi-asset ETFs
            bond_fallback: Bond ETF for fallback (default: TLT)
            cash_fallback: Cash ETF for fallback (default: SGOV)
            momentum_period: Lookback period for momentum (default: 60 days)
            top_n: Number of top assets to hold (default: 3)
            min_momentum: Minimum momentum threshold (default: 0.0)
            rebalance_days: Days between rebalances (default: 14)
        """
        self.multi_assets = multi_assets or [
            'TLT',   # Long-term Treasury bonds
            'IEF',   # Intermediate-term Treasury bonds
            'GLD',   # Gold
            'UUP',   # US Dollar Index
            'XLU',   # Utilities (defensive sector)
            'XLP',   # Consumer Staples (defensive sector)
            'XLV'    # Healthcare (defensive sector)
        ]

        self.bond_fallback = bond_fallback
        self.cash_fallback = cash_fallback

        # Create universe including fallback assets
        fallback_assets = []
        if bond_fallback not in self.multi_assets:
            fallback_assets.append(bond_fallback)
        if cash_fallback not in self.multi_assets:
            fallback_assets.append(cash_fallback)

        self.all_assets = self.multi_assets + fallback_assets
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
        # REGIME CHECK: Only active in bear markets
        if context.regime.equity_regime != 'bear':
            # Not a bear market - return empty weights (no positions)
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights={}
            )

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

        if len(asset_momentum) == 0:
            # No data available - use fallback allocation
            weights[self.bond_fallback] = 0.5
            weights[self.cash_fallback] = 0.5
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Sort assets by momentum (descending)
        ranked_assets = sorted(asset_momentum.items(), key=lambda x: x[1], reverse=True)

        # Get top N assets
        top_assets = ranked_assets[:self.top_n]

        # Filter to only assets with positive momentum
        positive_assets = [(asset, mom) for asset, mom in top_assets if mom >= self.min_momentum]

        if len(positive_assets) > 0:
            # Equal weight across positive momentum assets
            weight_per_asset = 1.0 / len(positive_assets)
            for asset, _ in positive_assets:
                weights[asset] = weight_per_asset
        else:
            # No assets have positive momentum - use fallback allocation
            # 50% bonds, 50% cash for safety
            weights[self.bond_fallback] = 0.5
            weights[self.cash_fallback] = 0.5

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"BearMultiAsset_v1(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"min_momentum={self.min_momentum}, rebalance_days={self.rebalance_days})"
        )