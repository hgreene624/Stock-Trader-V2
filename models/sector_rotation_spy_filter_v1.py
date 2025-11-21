"""
SectorRotationSPYFilter_v1

Enhanced sector rotation strategy with SPY trend filter for improved risk management.

Strategy:
- Universe: 11 S&P sector ETFs + TLT (bonds for defense) + SPY (for trend signal only)
- When SPY > X-day MA: Execute standard sector rotation
  - Ranks sectors by momentum
  - Holds top 3 sectors (equal weight)
  - Goes to TLT if all sectors bearish
- When SPY < X-day MA: Defensive mode
  - Entire allocation goes to TLT (defensive asset)
- Rebalances weekly

Why this should beat SPY:
1. All benefits of sector rotation when market trending up
2. Avoids drawdowns when SPY enters downtrend
3. SPY MA filter reduces whipsaw in choppy markets
4. TLT provides returns during risk-off periods

Key enhancement over v1:
- SPY trend confirmation prevents sector rotation during bear markets
- Reduces drawdowns while maintaining upside capture
"""

import pandas as pd
import numpy as np
from typing import Dict
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationSPYFilter_v1(BaseModel):
    """
    Sector rotation with SPY trend filter for enhanced risk management.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationSPYFilter_v1",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        momentum_period: int = 126,  # ~6 months
        top_n: int = 3,
        min_momentum: float = 0.0,
        target_leverage: float = 1.0,  # 1.0 = no leverage, 1.25 = 25% leverage
        spy_ma_period: int = 200,  # SPY MA period for trend filter
        use_trend_filter: bool = True  # Enable/disable SPY trend filter
    ):
        """
        Initialize SectorRotationSPYFilter_v1.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs (default: 11 S&P sectors)
            defensive_asset: Asset to hold when all sectors bearish or SPY below MA (default: TLT)
            momentum_period: Lookback period for momentum (default: 126 days = 6 months)
            top_n: Number of top sectors to hold (default: 3)
            min_momentum: Minimum momentum to be invested (default: 0.0)
            target_leverage: Target leverage multiplier (default: 1.0 = no leverage)
            spy_ma_period: Period for SPY moving average filter (default: 200)
            use_trend_filter: Whether to use SPY trend filter (default: True)
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
        self.spy_ticker = 'SPY'  # For trend filter only

        # Include SPY in assets for data loading but not for trading
        self.all_assets = self.sectors + [defensive_asset]
        self.assets = self.all_assets + [self.spy_ticker]  # Required for BacktestRunner to load SPY data

        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum
        self.target_leverage = target_leverage
        self.spy_ma_period = spy_ma_period
        self.use_trend_filter = use_trend_filter

        # Initialize base class with universe (excludes SPY from tradeable universe)
        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets  # Tradeable universe excludes SPY
        )

        # Track last rebalance date to implement weekly rebalancing
        self.last_rebalance = None

    def _check_spy_trend(self, context: Context) -> bool:
        """
        Check if SPY is above its moving average.

        Returns:
            True if SPY is above MA (bullish), False otherwise
        """
        if not self.use_trend_filter:
            return True  # Always bullish if filter disabled

        if self.spy_ticker not in context.asset_features:
            # SPY data not available, assume bullish
            return True

        spy_features = context.asset_features[self.spy_ticker]

        # Need enough data for MA calculation
        if len(spy_features) < self.spy_ma_period + 1:
            return True  # Not enough data, assume bullish

        # Get current SPY price and calculate MA
        close_col = 'Close' if 'Close' in spy_features.columns else 'close'
        current_price = spy_features[close_col].iloc[-1]

        # Calculate simple moving average
        ma_values = spy_features[close_col].iloc[-(self.spy_ma_period + 1):-1]
        spy_ma = ma_values.mean()

        if pd.isna(current_price) or pd.isna(spy_ma) or spy_ma == 0:
            return True  # Data issues, assume bullish

        # Return True if SPY above MA, False otherwise
        return current_price > spy_ma

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on sector momentum ranking with SPY trend filter.

        Returns:
            ModelOutput with target weights
        """
        # Weekly rebalancing: only rebalance if 7+ days since last rebalance
        if self.last_rebalance is not None:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < 7:
                # Not time to rebalance yet - hold current positions
                # Filter out SPY from current exposures (it's not tradeable)
                filtered_exposures = {
                    asset: weight
                    for asset, weight in context.current_exposures.items()
                    if asset != self.spy_ticker
                }
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=filtered_exposures,  # NAV exposures as-is
                    hold_current=True  # Signal: don't apply leverage again
                )

        self.last_rebalance = context.timestamp

        # Initialize weights dictionary for all tradeable assets
        weights = {asset: 0.0 for asset in self.all_assets}

        # Check SPY trend filter first
        spy_is_bullish = self._check_spy_trend(context)

        # If SPY is below MA, go fully defensive
        if not spy_is_bullish:
            weights[self.defensive_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights,
                urgency="high"  # Higher urgency for risk-off transitions
            )

        # SPY is bullish - proceed with sector rotation
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
            # No data - go to defensive
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
            weights[self.defensive_asset] = 1.0
        else:
            # Hold top N sectors with positive momentum

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

        # Note: leverage is now applied at the system level (PortfolioEngine/BacktestRunner)
        # Models should return weights that sum to 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"SectorRotationSPYFilter_v1(model_id='{self.model_id}', "
            f"sectors={len(self.sectors)}, top_n={self.top_n}, "
            f"momentum_period={self.momentum_period}, "
            f"spy_ma_period={self.spy_ma_period}, "
            f"use_trend_filter={self.use_trend_filter})"
        )