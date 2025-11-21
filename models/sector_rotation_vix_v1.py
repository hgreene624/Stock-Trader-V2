"""
SectorRotationVIX_v1

VIX-based dynamic leverage sector rotation strategy.

Based on SectorRotationModel_v1 but adds dynamic leverage scaling based on VIX levels:
- VIX < 15: Market calm, increase leverage (1.2x multiplier)
- VIX 15-20: Normal conditions (1.0x multiplier)
- VIX 20-25: Elevated volatility, reduce leverage (0.8x multiplier)
- VIX 25-35: High volatility, significant reduction (0.6x multiplier)
- VIX > 35: Extreme fear, minimal exposure (0.4x multiplier)

This approach aims to:
1. Capitalize on calm markets with higher leverage
2. Protect capital during volatile periods
3. Maintain the core momentum strategy while adapting to market conditions

The model gracefully handles missing VIX data by falling back to base leverage.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationVIX_v1(BaseModel):
    """
    Sector rotation with VIX-based dynamic leverage adjustment.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationVIX_v1",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        momentum_period: int = 126,  # ~6 months
        top_n: int = 3,
        min_momentum: float = 0.0,
        base_leverage: float = 1.25,  # Base leverage before VIX adjustment
        use_vol_scaling: bool = True,  # Enable/disable VIX-based scaling
        vix_symbol: str = "^VIX",  # VIX symbol
    ):
        """
        Initialize SectorRotationVIX_v1.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs (default: 11 S&P sectors)
            defensive_asset: Asset to hold when all sectors bearish (default: TLT)
            momentum_period: Lookback period for momentum (default: 126 days = 6 months)
            top_n: Number of top sectors to hold (default: 3)
            min_momentum: Minimum momentum to be invested (default: 0.0)
            base_leverage: Base leverage multiplier before VIX adjustment (default: 1.25)
            use_vol_scaling: Enable VIX-based leverage scaling (default: True)
            vix_symbol: Symbol for VIX data (default: ^VIX)
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
        self.base_leverage = base_leverage
        self.use_vol_scaling = use_vol_scaling
        self.vix_symbol = vix_symbol

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        # Track last rebalance date to implement weekly rebalancing
        self.last_rebalance: Optional[pd.Timestamp] = None

    def _calculate_vix_leverage_multiplier(self, context: Context) -> float:
        """
        Calculate leverage multiplier based on VIX levels.

        Returns:
            Multiplier to apply to base_leverage (0.4 to 1.2)
        """
        if not self.use_vol_scaling:
            return 1.0

        # Try to get VIX data from context
        if self.vix_symbol in context.asset_features:
            vix_features = context.asset_features[self.vix_symbol]

            # Handle both uppercase and lowercase column names
            close_col = 'Close' if 'Close' in vix_features.columns else 'close'

            if len(vix_features) > 0 and close_col in vix_features.columns:
                current_vix = vix_features[close_col].iloc[-1]

                # Check for valid VIX value
                if not pd.isna(current_vix) and current_vix > 0:
                    # Apply VIX-based scaling rules
                    if current_vix < 15:
                        # Low VIX: Market calm, increase leverage
                        return 1.2
                    elif current_vix < 20:
                        # Normal VIX: Standard leverage
                        return 1.0
                    elif current_vix < 25:
                        # Elevated VIX: Reduce leverage moderately
                        return 0.8
                    elif current_vix < 35:
                        # High VIX: Significant leverage reduction
                        return 0.6
                    else:
                        # Extreme VIX (>35): Minimal leverage
                        return 0.4

        # Fallback to no adjustment if VIX data unavailable
        return 1.0

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights with VIX-adjusted leverage.

        Returns:
            ModelOutput with target weights
        """
        # Weekly rebalancing: only rebalance if 7+ days since last rebalance
        if self.last_rebalance is not None:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < 7:
                # Not time to rebalance yet - hold current positions
                # Return current NAV-relative exposures directly with hold_current=True
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=context.current_exposures,  # NAV exposures as-is
                    hold_current=True  # Signal: don't apply leverage again
                )

        self.last_rebalance = context.timestamp

        # Calculate VIX-based leverage multiplier
        vix_multiplier = self._calculate_vix_leverage_multiplier(context)
        adjusted_leverage = self.base_leverage * vix_multiplier

        # Calculate momentum for each sector
        sector_momentum = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]
            if len(features) < self.momentum_period + 1:
                continue

            # Get current and historical prices
            # Use Capital case column names (normalized in production)
            close_col = 'Close' if 'Close' in features.columns else 'close'
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(self.momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            # Calculate momentum
            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum

        # Rank sectors by momentum
        if len(sector_momentum) == 0:
            # No data - go to defensive with adjusted leverage
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = adjusted_leverage
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
            weights[self.defensive_asset] = adjusted_leverage
        else:
            # Hold top N sectors with positive momentum
            weights = {asset: 0.0 for asset in self.all_assets}

            # Filter to only sectors with positive momentum
            positive_sectors = [(s, m) for s, m in top_sectors if m >= self.min_momentum]

            if len(positive_sectors) > 0:
                # Equal weight across selected sectors with VIX-adjusted leverage
                weight_per_sector = adjusted_leverage / len(positive_sectors)
                for sector, _ in positive_sectors:
                    weights[sector] = weight_per_sector
            else:
                # All negative - go defensive with adjusted leverage
                weights[self.defensive_asset] = adjusted_leverage

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"SectorRotationVIX_v1(model_id='{self.model_id}', "
            f"sectors={len(self.sectors)}, top_n={self.top_n}, "
            f"momentum_period={self.momentum_period}, "
            f"base_leverage={self.base_leverage}, "
            f"use_vol_scaling={self.use_vol_scaling})"
        )