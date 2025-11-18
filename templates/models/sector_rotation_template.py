"""
{MODEL_NAME}

Momentum-based sector rotation strategy.

TEMPLATE PLACEHOLDERS:
- {MODEL_NAME}: Name of the model class
- {MODEL_ID}: Unique model identifier
- {DESCRIPTION}: Strategy description
- {MOMENTUM_PERIOD}: Lookback period for momentum (days)
- {TOP_N}: Number of top sectors to hold
- {MIN_MOMENTUM}: Minimum momentum threshold

HOW TO USE:
    python3 -m backtest.cli create-model \
        --template sector_rotation \
        --name MySectorRotation \
        --params "momentum_period=90,top_n=4"
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
    - Ranks sectors by momentum over {MOMENTUM_PERIOD} days
    - Holds top {TOP_N} sectors with positive momentum
    - Equal weight across selected sectors
    - Goes defensive (TLT) if all sectors bearish
    """

    def __init__(
        self,
        model_id: str = "{MODEL_ID}",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        momentum_period: int = {MOMENTUM_PERIOD},
        top_n: int = {TOP_N},
        min_momentum: float = {MIN_MOMENTUM}
    ):
        """
        Initialize {MODEL_NAME}.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs (default: 11 S&P sectors)
            defensive_asset: Asset to hold when all sectors bearish
            momentum_period: Lookback period for momentum
            top_n: Number of top sectors to hold
            min_momentum: Minimum momentum to be invested
        """
        self.sectors = sectors or [
            'XLK',   # Technology
            'XLF',   # Financials
            'XLE',   # Energy
            'XLV',   # Healthcare
            'XLI',   # Industrials
            'XLP',   # Consumer Staples
            'XLU',   # Utilities
            'XLY',   # Consumer Discretionary
            'XLC',   # Communications
            'XLB',   # Materials
            'XLRE'   # Real Estate
        ]

        self.defensive_asset = defensive_asset
        self.all_assets = self.sectors + [defensive_asset]
        self.assets = self.all_assets  # Required for BacktestRunner
        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        self.last_rebalance = None

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on sector momentum ranking.

        Returns:
            ModelOutput with target weights
        """
        # Monthly rebalancing
        current_month = (context.timestamp.year, context.timestamp.month)

        if self.last_rebalance is not None:
            last_month = (self.last_rebalance.year, self.last_rebalance.month)
            if current_month == last_month:
                pass  # Could return current positions here

        self.last_rebalance = context.timestamp

        # Calculate momentum for each sector
        sector_momentum = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]
            if len(features) < self.momentum_period + 1:
                continue

            # Get current and historical prices
            current_price = features['close'].iloc[-1]
            past_price = features['close'].iloc[-(self.momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            # Calculate momentum
            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum

        # Rank sectors by momentum
        if len(sector_momentum) == 0:
            # No data - go defensive
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Sort sectors by momentum (descending)
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)

        # Check if top sectors have positive momentum
        top_sectors = ranked_sectors[:self.top_n]

        # If all top sectors are bearish, go defensive
        if all(mom < self.min_momentum for _, mom in top_sectors):
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0
        else:
            # Hold top N sectors with positive momentum
            weights = {asset: 0.0 for asset in self.all_assets}

            # Filter to only sectors with positive momentum
            positive_sectors = [(s, m) for s, m in top_sectors if m >= self.min_momentum]

            if len(positive_sectors) > 0:
                # Equal weight across selected sectors
                weight_per_sector = 1.0 / len(positive_sectors)
                for sector, _ in positive_sectors:
                    weights[sector] = weight_per_sector
            else:
                # All negative - go defensive
                weights[self.defensive_asset] = 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(model_id='{self.model_id}', "
            f"sectors={len(self.sectors)}, top_n={self.top_n}, "
            f"momentum_period={self.momentum_period})"
        )
