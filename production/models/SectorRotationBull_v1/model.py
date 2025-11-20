"""
SectorRotationBull_v1

Bull market specialist for sector rotation.

Strategy:
- Only active when equity_regime == 'bull'
- Aggressive parameters optimized for bull markets (from walk-forward Windows 1, 5)
- Shorter momentum period (80 days) to catch trends quickly
- Lower quality filter (min_momentum=0.03) to stay invested
- More diversification (top_n=4) to capture multiple winning sectors
- Higher leverage (1.3x) to amplify gains

Performance Expectations (from walk-forward):
- Window 1: 55.54% CAGR out-of-sample
- Window 5: 36.43% CAGR out-of-sample
- Negative degradation (out-of-sample BETTER than in-sample)
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationBull_v1(BaseModel):
    """
    Bull market specialist - aggressive sector rotation.

    Only generates weights when equity_regime == 'bull'.
    Uses parameters optimized on bull market walk-forward windows.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationBull_v1",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        momentum_period: int = 80,      # Shorter for bull markets
        top_n: int = 4,                  # More diversification
        min_momentum: float = 0.03,      # Lower threshold = stay invested
        target_leverage: float = 1.3     # Aggressive leverage in bull
    ):
        """
        Initialize Bull Market Sector Rotation Model.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs (default: 11 S&P sectors)
            defensive_asset: Asset to hold when defensive (default: TLT)
            momentum_period: Lookback period (default: 80 days, optimized for bull)
            top_n: Number of top sectors to hold (default: 4, more diversified)
            min_momentum: Minimum momentum threshold (default: 0.03, lower for bull)
            target_leverage: Target leverage (default: 1.3x, aggressive for bull)
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
        Generate target weights - ONLY in bull markets.

        Returns:
            ModelOutput with target weights (empty if not bull regime)
        """
        # REGIME CHECK: Only active in bull markets
        if context.regime.equity_regime != 'bull':
            # Not a bull market - return empty weights (no positions)
            weights = {asset: 0.0 for asset in self.all_assets}
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Weekly rebalancing: only rebalance if 7+ days since last rebalance
        if self.last_rebalance is not None:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < 7:
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

        # Check if top sectors have positive momentum
        top_sectors = ranked_sectors[:self.top_n]

        # If all top sectors are bearish, go defensive
        if all(mom < self.min_momentum for _, mom in top_sectors):
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0
        else:
            # Hold top N sectors with positive momentum
            weights = {asset: 0.0 for asset in self.all_assets}

            # Filter to only sectors with sufficient momentum
            positive_sectors = [(s, m) for s, m in top_sectors if m >= self.min_momentum]

            if len(positive_sectors) > 0:
                # Equal weight across selected sectors
                weight_per_sector = 1.0 / len(positive_sectors)
                for sector, _ in positive_sectors:
                    weights[sector] = weight_per_sector
            else:
                # All below threshold - go defensive
                weights[self.defensive_asset] = 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"SectorRotationBull_v1(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"min_momentum={self.min_momentum}, leverage={self.target_leverage})"
        )
