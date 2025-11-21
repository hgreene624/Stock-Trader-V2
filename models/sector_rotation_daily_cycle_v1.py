"""
SectorRotationDailyCycle_v1

Hybrid strategy combining:
- Sector rotation momentum for SELECTION (which ETFs)
- Daily cycle timing for ENTRY/EXIT (capture intraday rallies)

Strategy:
1. Use momentum ranking to identify top sectors
2. Enter on dips (close in bottom portion of daily range)
3. Take profit aggressively (0.5-1% gain next day)
4. Hold minimum overnight (PDT-safe)

Target: Capture daily rally cycles for 1-2% weekly gains.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationDailyCycle_v1(BaseModel):
    """
    Sector rotation with daily cycle timing for entries and exits.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationDailyCycle_v1",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        # Momentum selection parameters
        momentum_period: int = 80,
        top_n: int = 4,
        min_momentum: float = 0.02,
        # Daily cycle parameters
        entry_range_pct: float = 0.30,  # Enter if close in bottom 30% of daily range
        take_profit_pct: float = 0.008,  # Take profit at 0.8% gain
        stop_loss_pct: float = 0.005,  # Stop loss at 0.5% loss
        min_hold_bars: int = 1,  # Minimum bars to hold (1 = overnight)
        # ATR for volatility filter
        atr_period: int = 14,
        max_atr_pct: float = 0.03,  # Skip if ATR > 3% (too volatile)
    ):
        """
        Initialize SectorRotationDailyCycle_v1.
        """
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]

        self.defensive_asset = defensive_asset
        self.all_assets = self.sectors + [defensive_asset]
        self.assets = self.all_assets
        self.model_id = model_id

        # Momentum parameters
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum

        # Daily cycle parameters
        self.entry_range_pct = entry_range_pct
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.min_hold_bars = min_hold_bars

        # Volatility filter
        self.atr_period = atr_period
        self.max_atr_pct = max_atr_pct

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets
        )

        # State tracking
        self.entry_prices: Dict[str, float] = {}
        self.entry_bars: Dict[str, int] = {}
        self.bars_elapsed: int = 0
        self.top_sectors: list = []  # Cache top sectors from momentum ranking

    def _calculate_atr(self, features: pd.DataFrame) -> float:
        """Calculate ATR as percentage of price."""
        high_col = 'High' if 'High' in features.columns else 'high'
        low_col = 'Low' if 'Low' in features.columns else 'low'
        close_col = 'Close' if 'Close' in features.columns else 'close'

        high = features[high_col]
        low = features[low_col]
        close = features[close_col]

        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)

        atr = tr.rolling(self.atr_period).mean().iloc[-1]
        current_price = close.iloc[-1]

        return atr / current_price if current_price > 0 else 0

    def _is_dip_entry(self, features: pd.DataFrame) -> bool:
        """Check if current bar is a dip (close in bottom portion of range)."""
        high_col = 'High' if 'High' in features.columns else 'high'
        low_col = 'Low' if 'Low' in features.columns else 'low'
        close_col = 'Close' if 'Close' in features.columns else 'close'

        high = features[high_col].iloc[-1]
        low = features[low_col].iloc[-1]
        close = features[close_col].iloc[-1]

        if high == low:
            return False

        # Position in daily range (0 = low, 1 = high)
        range_position = (close - low) / (high - low)

        return range_position <= self.entry_range_pct

    def _get_price(self, features: pd.DataFrame) -> float:
        """Get current close price."""
        close_col = 'Close' if 'Close' in features.columns else 'close'
        return features[close_col].iloc[-1]

    def _check_exit(self, symbol: str, current_price: float) -> tuple[bool, str]:
        """Check if position should exit."""
        if symbol not in self.entry_prices:
            return False, ""

        entry_price = self.entry_prices[symbol]
        entry_bar = self.entry_bars[symbol]
        bars_held = self.bars_elapsed - entry_bar

        # Minimum hold period (PDT protection)
        if bars_held < self.min_hold_bars:
            return False, "min_hold"

        # Calculate P&L
        pnl_pct = (current_price - entry_price) / entry_price

        # Take profit
        if pnl_pct >= self.take_profit_pct:
            return True, "take_profit"

        # Stop loss
        if pnl_pct <= -self.stop_loss_pct:
            return True, "stop_loss"

        # Exit after 2 bars if no profit (don't hold losers)
        if bars_held >= 2 and pnl_pct < 0:
            return True, "time_exit"

        return False, ""

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate weights using momentum selection + daily cycle timing.
        """
        self.bars_elapsed += 1

        # Step 1: Rank sectors by momentum (weekly update)
        if self.bars_elapsed % 5 == 1 or not self.top_sectors:
            sector_momentum = {}

            for sector in self.sectors:
                if sector not in context.asset_features:
                    continue

                features = context.asset_features[sector]
                if len(features) < self.momentum_period + 1:
                    continue

                close_col = 'Close' if 'Close' in features.columns else 'close'
                current = features[close_col].iloc[-1]
                past = features[close_col].iloc[-(self.momentum_period + 1)]

                if pd.isna(current) or pd.isna(past) or past == 0:
                    continue

                momentum = (current - past) / past

                # Filter by ATR (skip too volatile)
                atr_pct = self._calculate_atr(features)
                if atr_pct > self.max_atr_pct:
                    continue

                sector_momentum[sector] = momentum

            # Select top sectors with positive momentum
            ranked = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
            self.top_sectors = [s for s, m in ranked[:self.top_n] if m >= self.min_momentum]

        # Step 2: Check exits for current positions
        weights = {asset: 0.0 for asset in self.all_assets}

        for symbol in list(self.entry_prices.keys()):
            if symbol not in context.asset_features:
                continue

            current_price = self._get_price(context.asset_features[symbol])
            should_exit, reason = self._check_exit(symbol, current_price)

            if should_exit:
                # Exit position
                del self.entry_prices[symbol]
                del self.entry_bars[symbol]
            else:
                # Hold position
                weights[symbol] = context.current_exposures.get(symbol, 0)

        # Step 3: Look for new entries in top sectors
        available_slots = self.top_n - len(self.entry_prices)

        if available_slots > 0 and self.top_sectors:
            for sector in self.top_sectors:
                if sector in self.entry_prices:
                    continue  # Already holding
                if available_slots <= 0:
                    break

                if sector not in context.asset_features:
                    continue

                features = context.asset_features[sector]

                # Check for dip entry
                if self._is_dip_entry(features):
                    current_price = self._get_price(features)

                    # Enter position
                    weight_per_position = 1.0 / self.top_n
                    weights[sector] = weight_per_position

                    self.entry_prices[sector] = current_price
                    self.entry_bars[sector] = self.bars_elapsed
                    available_slots -= 1

        # If no positions, go to cash (or defensive)
        total_weight = sum(weights.values())
        if total_weight == 0:
            weights[self.defensive_asset] = 1.0

        # Normalize weights
        if total_weight > 0 and total_weight != 1.0:
            for asset in weights:
                if weights[asset] > 0:
                    weights[asset] = weights[asset] / total_weight

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"SectorRotationDailyCycle_v1(model_id='{self.model_id}', "
            f"top_n={self.top_n}, take_profit={self.take_profit_pct*100:.1f}%)"
        )
