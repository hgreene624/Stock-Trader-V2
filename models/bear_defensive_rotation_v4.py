"""
BearDefensiveRotation_v4

Bear market specialist with RECOVERY ENHANCEMENT features.

Version 4 Improvements (based on V2, not V3):
- VIX-based recovery detection: Identify when panic is subsiding
- Faster momentum period (15 vs 20 days) for quicker response
- Override cash threshold during recovery phases to capture rebounds
- Designed to improve 2020-type recovery performance

Strategy:
- Base strategy same as V2 (defensive rotation with cash option)
- NEW: Monitors VIX for spike/decline patterns indicating recovery
- NEW: When recovery detected, becomes more aggressive (less cash)
- Faster momentum allows quicker rotation into recovering sectors

Design Rationale:
- V3's risk management helped 2018 but hurt 2020 recovery
- V4 aims to capture more of the rebound without sacrificing too much defense
- VIX patterns are reliable indicators of market panic cycles
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearDefensiveRotation_v4(BaseModel):
    """
    Bear market defensive rotation v4 - enhanced recovery detection.

    Only generates weights when equity_regime == 'bear'.
    V4 adds VIX-based recovery signals to capture rebounds better.
    """

    def __init__(
        self,
        model_id: str = "BearDefensiveRotation_v4",
        defensive_assets: list[str] = None,
        momentum_period: int = 15,  # V4: FASTER (was 20 in v2)
        top_n: int = 2,
        min_momentum: float = -0.05,
        cash_threshold: float = -0.10,
        vix_spike_threshold: float = 40.0,  # V4: NEW - VIX spike level
        vix_decline_threshold: float = -0.30,  # V4: NEW - VIX decline percent for recovery
        rebalance_days: int = 10
    ):
        """
        Initialize Bear Defensive Rotation Model v4.

        Args:
            model_id: Unique model identifier
            defensive_assets: List of defensive ETFs (default: XLU, XLP, TLT, GLD, UUP, SHY)
            momentum_period: Lookback period for momentum (default: 15 days - faster than v2)
            top_n: Number of top assets to hold (default: 2)
            min_momentum: Minimum momentum threshold (default: -0.05, can be negative)
            cash_threshold: If ALL assets below this, go 100% SHY (default: -0.10)
            vix_spike_threshold: VIX level indicating panic (default: 40.0)
            vix_decline_threshold: VIX decline percent for recovery signal (default: -0.30)
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

        # Add VIX to universe for monitoring (but not trading)
        self.all_assets = self.defensive_assets + ['^VIX']
        self.assets = self.all_assets  # Required for BacktestRunner to load data

        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum
        self.cash_threshold = cash_threshold
        self.vix_spike_threshold = vix_spike_threshold  # V4: NEW
        self.vix_decline_threshold = vix_decline_threshold  # V4: NEW
        self.rebalance_days = rebalance_days

        super().__init__(
            name=model_id,
            version="4.0.0",  # V4
            universe=self.all_assets
        )

        # Track last rebalance date
        self.last_rebalance: Optional[pd.Timestamp] = None

    def detect_recovery_signal(self, context: Context) -> bool:
        """
        Detect if market is in recovery phase using VIX.
        Returns True if should be aggressive (override conservative positioning).

        V4 NEW: This is the key innovation for capturing rebounds.
        """
        # Need VIX data in context - if not available, return False
        vix_features = context.asset_features.get('^VIX')
        if vix_features is None or len(vix_features) < 30:
            return False

        # Handle column name variations
        close_col = 'Close' if 'Close' in vix_features.columns else 'close'

        # Get VIX current and 30-day peak
        vix_current = vix_features[close_col].iloc[-1]
        vix_peak_30d = vix_features[close_col].tail(30).max()

        # Recovery signal: VIX spiked above threshold and now declining significantly
        if vix_peak_30d > self.vix_spike_threshold:
            vix_decline_pct = (vix_current - vix_peak_30d) / vix_peak_30d
            if vix_decline_pct < self.vix_decline_threshold:  # VIX down >30% from peak
                return True

        return False

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights - ONLY in bear markets.
        V4: Includes recovery detection for better rebound capture.

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

        # V4: Check for recovery signal
        recovery_mode = self.detect_recovery_signal(context)

        # V4: Adjust cash threshold based on recovery signal
        effective_cash_threshold = self.cash_threshold
        if recovery_mode:
            # Be more aggressive - double the negative threshold
            # e.g., -0.10 becomes -0.20, allowing more risk-taking
            effective_cash_threshold = self.cash_threshold * 2

        # Calculate momentum for each defensive asset (excluding VIX)
        asset_momentum = {}

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
            asset_momentum[asset] = momentum

        # Initialize weights
        weights = {}

        if len(asset_momentum) == 0:
            # No data available - go to cash (SHY)
            weights[self.cash_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Check if ALL assets are below effective cash threshold
        max_momentum = max(asset_momentum.values())
        if max_momentum < effective_cash_threshold:
            # Everything is crashing badly - go to pure cash
            # V4: Unless in recovery mode, then use original threshold
            if not recovery_mode or max_momentum < self.cash_threshold:
                weights[self.cash_asset] = 1.0
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=weights
                )

        # Sort assets by momentum (descending - best first, even if negative)
        ranked_assets = sorted(asset_momentum.items(), key=lambda x: x[1], reverse=True)

        # Get top N assets
        top_assets = ranked_assets[:self.top_n]

        # V4: In recovery mode, be more lenient with minimum momentum
        effective_min_momentum = self.min_momentum
        if recovery_mode:
            # Allow slightly worse momentum in recovery
            effective_min_momentum = self.min_momentum - 0.02  # e.g., -0.05 becomes -0.07

        # Check if top assets meet minimum momentum threshold
        qualified_assets = [(asset, mom) for asset, mom in top_assets if mom >= effective_min_momentum]

        if len(qualified_assets) > 0:
            # Equal weight across qualified assets
            weight_per_asset = 1.0 / len(qualified_assets)
            for asset, _ in qualified_assets:
                weights[asset] = weight_per_asset
        else:
            # No assets meet minimum threshold - use cash (SHY)
            weights[self.cash_asset] = 1.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"BearDefensiveRotation_v4(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"min_momentum={self.min_momentum}, cash_threshold={self.cash_threshold}, "
            f"vix_spike_threshold={self.vix_spike_threshold}, "
            f"vix_decline_threshold={self.vix_decline_threshold}, "
            f"rebalance_days={self.rebalance_days})"
        )