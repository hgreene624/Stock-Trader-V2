"""
SectorRotationBear_v1

Bear market specialist for sector rotation.

Strategy:
- Only active when equity_regime == 'bear'
- Defensive parameters designed to preserve capital in bear markets
- Longer momentum period (126 days) to filter noise and avoid false signals
- Higher quality filter (min_momentum=0.10) to only hold strong sectors
- Concentrated positions (top_n=2) in only the best sectors
- No leverage (1.0x) to reduce risk

Design Rationale:
- Bear markets are characterized by regime changes and high volatility
- Optimizing on bear market data leads to overfitting (see walk-forward Windows 2, 4)
- Better to use conservative baseline parameters and focus on capital preservation
- Quick exit to TLT when momentum deteriorates
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationBear_v1(BaseModel):
    """
    Bear market specialist - defensive sector rotation.

    Only generates weights when equity_regime == 'bear'.
    Uses conservative parameters to preserve capital.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationBear_v1",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        momentum_period: int = 126,      # Longer to filter noise
        top_n: int = 2,                   # Concentrated in best only
        min_momentum: float = 0.10,       # High quality filter
        target_leverage: float = 1.0      # No leverage in bear markets
    ):
        """
        Initialize Bear Market Sector Rotation Model.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs (default: 11 S&P sectors)
            defensive_asset: Asset to hold when defensive (default: TLT)
            momentum_period: Lookback period (default: 126 days, baseline)
            top_n: Number of top sectors to hold (default: 2, concentrated)
            min_momentum: Minimum momentum threshold (default: 0.10, high filter)
            target_leverage: Target leverage (default: 1.0x, no leverage)
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
        self.assets = self.all_assets  # Required for BacktestRunner to load data
        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum
        self.target_leverage = target_leverage

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        # Track last rebalance date to implement monthly rebalancing
        self.last_rebalance = None

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights - ONLY in bear markets.

        Returns:
            ModelOutput with target weights (empty if not bear regime)
        """
        # REGIME CHECK: Only active in bear markets
        if context.regime.equity_regime != 'bear':
            # Not a bear market - return empty weights (no positions)
            weights = {asset: 0.0 for asset in self.all_assets}
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Rebalancing logic:
        # 1. Always rebalance on first run (last_rebalance is None)
        # 2. Rebalance on first trading day of new month
        # This ensures fresh positions on startup and monthly updates
        current_month = (context.timestamp.year, context.timestamp.month)

        if self.last_rebalance is not None:
            last_month = (self.last_rebalance.year, self.last_rebalance.month)
            if current_month == last_month:
                # Not time to rebalance yet - hold current positions
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=context.current_exposures,
                    hold_current=True
                )

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
            # No data - go to defensive
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Sort sectors by momentum (descending)
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)

        # Check if top sectors meet minimum quality threshold
        top_sectors = ranked_sectors[:self.top_n]

        # In bear markets, be quick to go defensive
        if all(mom < self.min_momentum for _, mom in top_sectors):
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0
        else:
            # Hold top N sectors with sufficient momentum
            weights = {asset: 0.0 for asset in self.all_assets}

            # Filter to only sectors meeting quality threshold
            qualified_sectors = [(s, m) for s, m in top_sectors if m >= self.min_momentum]

            if len(qualified_sectors) > 0:
                # Equal weight across qualified sectors
                weight_per_sector = 1.0 / len(qualified_sectors)
                for sector, _ in qualified_sectors:
                    weights[sector] = weight_per_sector
            else:
                # No sectors qualify - go defensive
                weights[self.defensive_asset] = 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"SectorRotationBear_v1(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"min_momentum={self.min_momentum}, leverage={self.target_leverage})"
        )
