"""
SectorRotationRegime_v1

Consolidated regime-switching sector rotation model.

Combines SectorRotationModel_v1, SectorRotationBull_v1, and SectorRotationBear_v1
into a single model that automatically switches parameters based on market regime.

Strategy:
- Detects regime using context.regime.equity_regime
- Bull regime: Aggressive parameters (shorter momentum, more positions, higher leverage)
- Bear regime: Defensive parameters (longer momentum, fewer positions, no leverage)
- Neutral regime: Baseline parameters

This is functionally equivalent to running the three separate models but in a single package.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationRegime_v1(BaseModel):
    """
    Regime-switching sector rotation model.

    Automatically adjusts parameters based on detected market regime.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationRegime_v1",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        # Bull regime parameters
        bull_momentum_period: int = 80,
        bull_top_n: int = 4,
        bull_min_momentum: float = 0.03,
        bull_leverage: float = 1.3,
        # Bear regime parameters
        bear_momentum_period: int = 126,
        bear_top_n: int = 2,
        bear_min_momentum: float = 0.10,
        bear_leverage: float = 1.0,
        # Neutral/default regime parameters
        neutral_momentum_period: int = 126,
        neutral_top_n: int = 3,
        neutral_min_momentum: float = 0.0,
        neutral_leverage: float = 1.25,
        # Rebalancing
        rebalance_days: int = 7,
    ):
        """
        Initialize Regime-Switching Sector Rotation Model.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs (default: 11 S&P sectors)
            defensive_asset: Asset to hold when defensive (default: TLT)

            Bull regime parameters (aggressive):
                bull_momentum_period: 80 days (shorter to catch trends)
                bull_top_n: 4 (more diversification)
                bull_min_momentum: 0.03 (lower threshold to stay invested)
                bull_leverage: 1.3x (amplify gains)

            Bear regime parameters (defensive):
                bear_momentum_period: 126 days (filter noise)
                bear_top_n: 2 (concentrated in best only)
                bear_min_momentum: 0.10 (high quality filter)
                bear_leverage: 1.0x (no leverage)

            Neutral regime parameters (baseline):
                neutral_momentum_period: 126 days
                neutral_top_n: 3
                neutral_min_momentum: 0.0
                neutral_leverage: 1.25x

            rebalance_days: Days between rebalances (default: 7)
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
        self.assets = self.all_assets
        self.model_id = model_id
        self.rebalance_days = rebalance_days

        # Bull parameters
        self.bull_momentum_period = bull_momentum_period
        self.bull_top_n = bull_top_n
        self.bull_min_momentum = bull_min_momentum
        self.bull_leverage = bull_leverage

        # Bear parameters
        self.bear_momentum_period = bear_momentum_period
        self.bear_top_n = bear_top_n
        self.bear_min_momentum = bear_min_momentum
        self.bear_leverage = bear_leverage

        # Neutral parameters
        self.neutral_momentum_period = neutral_momentum_period
        self.neutral_top_n = neutral_top_n
        self.neutral_min_momentum = neutral_min_momentum
        self.neutral_leverage = neutral_leverage

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        # State tracking
        self.last_rebalance: Optional[pd.Timestamp] = None

    def _get_regime_parameters(self, regime: str) -> tuple:
        """
        Get parameters for the current regime.

        Returns:
            (momentum_period, top_n, min_momentum, leverage)
        """
        if regime == 'bull':
            return (
                self.bull_momentum_period,
                self.bull_top_n,
                self.bull_min_momentum,
                self.bull_leverage
            )
        elif regime == 'bear':
            return (
                self.bear_momentum_period,
                self.bear_top_n,
                self.bear_min_momentum,
                self.bear_leverage
            )
        else:  # neutral or unknown
            return (
                self.neutral_momentum_period,
                self.neutral_top_n,
                self.neutral_min_momentum,
                self.neutral_leverage
            )

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on current regime.

        Returns:
            ModelOutput with regime-adjusted target weights
        """
        # Get current regime
        current_regime = getattr(context.regime, 'equity_regime', 'neutral')

        # Get regime-specific parameters
        momentum_period, top_n, min_momentum, target_leverage = \
            self._get_regime_parameters(current_regime)

        # Check rebalancing schedule
        if self.last_rebalance is not None:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < self.rebalance_days:
                # Not time to rebalance - hold current positions
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
            if len(features) < momentum_period + 1:
                continue

            # Handle column name variations
            close_col = 'Close' if 'Close' in features.columns else 'close'
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum

        # Initialize weights
        weights = {asset: 0.0 for asset in self.all_assets}

        # If no sectors have data, go defensive
        if len(sector_momentum) == 0:
            weights[self.defensive_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Rank sectors by momentum (descending)
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
        top_sectors = ranked_sectors[:top_n]

        # Check if top sectors meet minimum momentum threshold
        if all(mom < min_momentum for _, mom in top_sectors):
            # All below threshold - go defensive
            weights[self.defensive_asset] = 1.0
        else:
            # Hold sectors meeting threshold
            qualified_sectors = [(s, m) for s, m in top_sectors if m >= min_momentum]

            if len(qualified_sectors) > 0:
                weight_per_sector = 1.0 / len(qualified_sectors)
                for sector, _ in qualified_sectors:
                    weights[sector] = weight_per_sector
            else:
                weights[self.defensive_asset] = 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"SectorRotationRegime_v1(model_id='{self.model_id}', "
            f"bull=[{self.bull_momentum_period}d/{self.bull_top_n}pos/{self.bull_leverage}x], "
            f"bear=[{self.bear_momentum_period}d/{self.bear_top_n}pos/{self.bear_leverage}x])"
        )
