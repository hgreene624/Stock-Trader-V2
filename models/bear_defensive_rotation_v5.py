"""
BearDefensiveRotation_v5

Bear market specialist with QUALITY FILTERS to reduce whipsaws.

Version 5 Improvements (based on V2, not V3):
- Trend strength filter: Only trade assets with consistent trends
- Correlation-adjusted sizing: Reduce exposure when sectors move together
- Designed to reduce false signals and improve consistency
- Focus on quality over quantity of trades

Strategy:
- Base strategy same as V2 (defensive rotation with cash option)
- NEW: Filter assets by trend consistency score
- NEW: Scale positions based on inter-sector correlation
- Fewer, higher-quality trades with better risk management

Design Rationale:
- V3's excessive trading (548 trades in 2022) showed need for quality filters
- V5 focuses on signal quality to reduce whipsaws
- Correlation adjustment prevents concentration risk in similar assets
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearDefensiveRotation_v5(BaseModel):
    """
    Bear market defensive rotation v5 - quality filters for consistency.

    Only generates weights when equity_regime == 'bear'.
    V5 adds trend strength and correlation filters to reduce false signals.
    """

    def __init__(
        self,
        model_id: str = "BearDefensiveRotation_v5",
        defensive_assets: list[str] = None,
        momentum_period: int = 20,  # Same as V2
        top_n: int = 2,
        min_momentum: float = -0.05,
        cash_threshold: float = -0.10,
        min_trend_strength: float = 0.3,  # V5: NEW - minimum trend consistency
        correlation_lookback: int = 20,  # V5: NEW - correlation calculation period
        correlation_threshold: float = 0.3,  # V5: NEW - correlation reduction threshold
        rebalance_days: int = 10
    ):
        """
        Initialize Bear Defensive Rotation Model v5.

        Args:
            model_id: Unique model identifier
            defensive_assets: List of defensive ETFs (default: XLU, XLP, TLT, GLD, UUP, SHY)
            momentum_period: Lookback period for momentum (default: 20 days)
            top_n: Number of top assets to hold (default: 2)
            min_momentum: Minimum momentum threshold (default: -0.05, can be negative)
            cash_threshold: If ALL assets below this, go 100% SHY (default: -0.10)
            min_trend_strength: Minimum trend consistency score (default: 0.3)
            correlation_lookback: Period for correlation calculation (default: 20)
            correlation_threshold: Correlation level to start reducing weights (default: 0.3)
            rebalance_days: Days between rebalances (default: 10)
        """
        # Same defensive assets as V2
        self.defensive_assets = defensive_assets or [
            'XLU',   # Utilities - defensive sector
            'XLP',   # Consumer Staples - defensive sector
            'TLT',   # Long-term Treasury bonds
            'GLD',   # Gold
            'UUP',   # US Dollar Index
            'SHY'    # Short-term Treasury (cash proxy)
        ]

        self.cash_asset = 'SHY'

        # Ensure SHY is in the list
        if self.cash_asset not in self.defensive_assets:
            self.defensive_assets.append(self.cash_asset)

        self.all_assets = self.defensive_assets
        self.assets = self.all_assets  # Required for BacktestRunner to load data

        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum
        self.cash_threshold = cash_threshold
        self.min_trend_strength = min_trend_strength  # V5: NEW
        self.correlation_lookback = correlation_lookback  # V5: NEW
        self.correlation_threshold = correlation_threshold  # V5: NEW
        self.rebalance_days = rebalance_days

        super().__init__(
            name=model_id,
            version="5.0.0",  # V5
            universe=self.all_assets
        )

        # Track last rebalance date
        self.last_rebalance: Optional[pd.Timestamp] = None

    def calculate_trend_strength(self, features: pd.DataFrame, period: int) -> float:
        """
        Calculate trend consistency score.
        Returns score 0-1 (1 = very consistent trend).

        V5 NEW: This filter reduces whipsaw trades.
        """
        if len(features) < period + 10:
            return 0.0

        # Handle column name variations
        close_col = 'Close' if 'Close' in features.columns else 'close'

        # Calculate momentum over two sub-periods
        # Short momentum (last 10 days)
        short_mom = (features[close_col].iloc[-1] / features[close_col].iloc[-11] - 1)

        # Long momentum (last period days)
        long_mom = (features[close_col].iloc[-1] / features[close_col].iloc[-(period+1)] - 1)

        # Consistent if both same sign and similar magnitude
        if (short_mom * long_mom) > 0:  # Same sign
            # Calculate consistency score
            if abs(short_mom) < 1e-6 or abs(long_mom) < 1e-6:
                return 0.0
            ratio = min(abs(short_mom), abs(long_mom)) / max(abs(short_mom), abs(long_mom))
            return ratio
        else:
            return 0.0  # Different signs = inconsistent

    def calculate_sector_correlation(self, context: Context) -> float:
        """
        Calculate average pairwise correlation among sectors.

        V5 NEW: Used to adjust position sizing based on diversification.
        """
        sectors = [s for s in self.defensive_assets if s in context.asset_features and s != self.cash_asset]
        if len(sectors) < 2:
            return 0.0

        # Build returns matrix
        returns_data = {}
        for symbol in sectors:
            features = context.asset_features[symbol]
            close_col = 'Close' if 'Close' in features.columns else 'close'

            if len(features) < self.correlation_lookback + 1:
                continue

            # Calculate returns for correlation period
            prices = features[close_col].tail(self.correlation_lookback + 1)
            returns = prices.pct_change().dropna()

            if len(returns) >= self.correlation_lookback - 1:
                returns_data[symbol] = returns.values

        if len(returns_data) < 2:
            return 0.0

        # Create DataFrame and calculate correlation
        try:
            # Align all returns series to same length
            min_len = min(len(v) for v in returns_data.values())
            aligned_data = {k: v[-min_len:] for k, v in returns_data.items()}
            returns_df = pd.DataFrame(aligned_data)

            if len(returns_df) < 10:  # Need minimum data for meaningful correlation
                return 0.0

            corr_matrix = returns_df.corr()

            # Get average of upper triangle (unique pairs)
            upper_triangle = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)]
            avg_corr = np.nanmean(upper_triangle)

            return avg_corr if not np.isnan(avg_corr) else 0.0
        except:
            return 0.0

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights - ONLY in bear markets.
        V5: Includes quality filters for better consistency.

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

        # Calculate momentum and trend strength for each defensive asset
        qualified_assets: List[Tuple[str, float, float]] = []

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

            # V5: Calculate trend strength
            trend_strength = self.calculate_trend_strength(features, self.momentum_period)

            # V5: Only consider if trend strength meets threshold
            if trend_strength >= self.min_trend_strength:
                qualified_assets.append((asset, momentum, trend_strength))

        # Initialize weights
        weights = {}

        if len(qualified_assets) == 0:
            # No assets qualify - go to cash (SHY)
            weights[self.cash_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # V5: Sort by momentum, then by trend strength as tiebreaker
        qualified_assets.sort(key=lambda x: (x[1], x[2]), reverse=True)

        # Check if ALL qualified assets are below cash threshold
        max_momentum = max(asset[1] for asset in qualified_assets)
        if max_momentum < self.cash_threshold:
            # Everything is crashing badly - go to pure cash
            weights[self.cash_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Get top N assets from qualified list
        top_assets = qualified_assets[:self.top_n]

        # Filter by minimum momentum
        final_assets = [(asset, mom) for asset, mom, _ in top_assets if mom >= self.min_momentum]

        if len(final_assets) == 0:
            # No assets meet minimum momentum - use cash
            weights[self.cash_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Calculate base equal weights
        base_weight = 1.0 / len(final_assets)
        base_weights = {asset: base_weight for asset, _ in final_assets}

        # V5: Calculate correlation adjustment
        avg_corr = self.calculate_sector_correlation(context)

        # Lower correlation → full weights
        # Higher correlation → reduced weights (move excess to cash)
        corr_scalar = 1.0
        if avg_corr > self.correlation_threshold:
            # Linear reduction: at threshold=0.3, start reducing
            # at corr=0.7, reduce by 40% (scalar=0.6)
            excess_corr = avg_corr - self.correlation_threshold
            max_reduction = 0.4  # Maximum 40% reduction
            corr_scalar = 1.0 - min(excess_corr, max_reduction)

        # Apply correlation scaling
        for symbol in base_weights:
            if symbol != self.cash_asset:
                weights[symbol] = base_weights[symbol] * corr_scalar

        # Put remainder in cash if correlation adjustment applied
        total_risk = sum(weights.values())
        if total_risk < 1.0:
            weights[self.cash_asset] = weights.get(self.cash_asset, 0.0) + (1.0 - total_risk)

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"BearDefensiveRotation_v5(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"min_momentum={self.min_momentum}, cash_threshold={self.cash_threshold}, "
            f"min_trend_strength={self.min_trend_strength}, "
            f"correlation_threshold={self.correlation_threshold}, "
            f"rebalance_days={self.rebalance_days})"
        )