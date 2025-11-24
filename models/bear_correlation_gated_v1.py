"""
BearCorrelationGated_v1

Bear market specialist using correlation-based crisis detection.

Strategy:
- Monitors average pairwise correlation among S&P 500 sectors
- High correlation (>0.8) indicates crisis/panic selling → Go to cash (SGOV)
- Moderate correlation (0.6-0.8) indicates elevated stress → Mix of cash and defensive
- Low correlation (<0.6) indicates normal diversification → Rotate to top defensive sectors
- Uses SGOV (short-term treasury) as cash proxy for minimal duration risk
- Rebalances frequently (default 7 days) for faster crisis response

Design Rationale:
- In true market panics, all sectors become highly correlated (everything sells off together)
- High correlation is a crisis signal that warrants maximum safety (cash/SGOV)
- As correlation normalizes, gradually re-enter through defensive sectors
- Faster rebalancing allows quicker response to changing crisis conditions
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearCorrelationGated_v1(BaseModel):
    """
    Bear market correlation-gated strategy - uses sector correlation as crisis indicator.

    Only generates weights when equity_regime == 'bear'.
    """

    def __init__(
        self,
        model_id: str = "BearCorrelationGated_v1",
        sectors: list[str] = None,
        defensive_sectors: list[str] = None,
        bond_asset: str = "TLT",
        cash_proxy: str = "SGOV",  # Short-term treasury as cash
        correlation_window: int = 20,
        crisis_correlation: float = 0.8,
        moderate_correlation: float = 0.6,
        defensive_top_n: int = 3,
        rebalance_days: int = 7
    ):
        """
        Initialize Bear Correlation-Gated Model.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs for correlation monitoring
            defensive_sectors: Defensive sectors to rotate into (default: XLU, XLP, XLV)
            bond_asset: Bond ETF (default: TLT)
            cash_proxy: Cash equivalent ETF (default: SGOV)
            correlation_window: Days for correlation calculation (default: 20)
            crisis_correlation: Threshold for crisis mode (default: 0.8)
            moderate_correlation: Threshold for moderate stress (default: 0.6)
            defensive_top_n: Number of defensive sectors to hold (default: 3)
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

        self.defensive_sectors = defensive_sectors or ['XLU', 'XLP', 'XLV']
        self.bond_asset = bond_asset
        self.cash_proxy = cash_proxy

        # Create universe of all assets we might trade
        self.all_assets = list(set(self.sectors + [bond_asset, cash_proxy]))
        self.assets = self.all_assets  # Required for BacktestRunner to load data

        self.model_id = model_id
        self.correlation_window = correlation_window
        self.crisis_correlation = crisis_correlation
        self.moderate_correlation = moderate_correlation
        self.defensive_top_n = defensive_top_n
        self.rebalance_days = rebalance_days

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        # Track last rebalance date
        self.last_rebalance: Optional[pd.Timestamp] = None

    def _calculate_avg_correlation(self, context: Context) -> float:
        """
        Calculate average pairwise correlation among sectors.

        Returns:
            Average correlation coefficient (0 to 1)
        """
        # Collect returns for all available sectors
        returns_data = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]

            # Handle both 'Close' and 'close' column names
            close_col = 'Close' if 'Close' in features.columns else 'close'

            if len(features) < self.correlation_window + 1:
                continue

            # Get recent closing prices
            recent_prices = features[close_col].iloc[-(self.correlation_window + 1):]

            # Calculate returns
            returns = recent_prices.pct_change().dropna()

            if len(returns) >= self.correlation_window - 1:
                returns_data[sector] = returns.values

        # Need at least 2 sectors for correlation
        if len(returns_data) < 2:
            return 0.0

        # Create DataFrame from returns
        returns_df = pd.DataFrame(returns_data)

        # Calculate correlation matrix
        corr_matrix = returns_df.corr()

        # Get upper triangle (excluding diagonal)
        upper_triangle = np.triu(corr_matrix.values, k=1)

        # Calculate average of non-zero correlations
        mask = upper_triangle != 0
        if mask.sum() > 0:
            avg_correlation = np.abs(upper_triangle[mask]).mean()
            return avg_correlation

        return 0.0

    def _rank_defensive_sectors(self, context: Context) -> list[tuple[str, float]]:
        """
        Rank defensive sectors by momentum.

        Returns:
            List of (sector, momentum) tuples sorted by momentum
        """
        sector_momentum = {}

        for sector in self.defensive_sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]

            # Handle both 'Close' and 'close' column names
            close_col = 'Close' if 'Close' in features.columns else 'close'

            if len(features) < 21:  # Need at least 21 days for momentum
                continue

            # Calculate 20-day momentum
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-21]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum

        # Sort by momentum (descending)
        ranked = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on sector correlation levels.

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

        # Calculate average sector correlation
        avg_correlation = self._calculate_avg_correlation(context)

        # Initialize weights
        weights = {}

        # Determine allocation based on correlation level
        if avg_correlation > self.crisis_correlation:
            # HIGH CRISIS MODE: All sectors moving together - go to cash
            weights[self.cash_proxy] = 1.0

        elif avg_correlation > self.moderate_correlation:
            # MODERATE CRISIS: Mix of cash and defensive assets
            weights[self.cash_proxy] = 0.5

            # Allocate remaining to defensive rotation
            defensive_ranked = self._rank_defensive_sectors(context)

            if len(defensive_ranked) > 0:
                # Take top defensive sector
                best_defensive = defensive_ranked[0][0]
                weights[best_defensive] = 0.25
                weights[self.bond_asset] = 0.25
            else:
                # No defensive sectors available - more bonds
                weights[self.bond_asset] = 0.5

        else:
            # NORMAL DIVERSIFICATION: Rotate to top defensive sectors
            defensive_ranked = self._rank_defensive_sectors(context)

            if len(defensive_ranked) > 0:
                # Take top N defensive sectors
                top_defensives = defensive_ranked[:self.defensive_top_n]
                weight_per_sector = 1.0 / len(top_defensives)

                for sector, _ in top_defensives:
                    weights[sector] = weight_per_sector
            else:
                # No sectors available - go to bonds
                weights[self.bond_asset] = 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"BearCorrelationGated_v1(model_id='{self.model_id}', "
            f"correlation_window={self.correlation_window}, "
            f"crisis_correlation={self.crisis_correlation}, "
            f"moderate_correlation={self.moderate_correlation})"
        )