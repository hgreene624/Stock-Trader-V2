"""
SectorRotationAdaptive_v2

Enhanced adaptive sector rotation with:
1. Better regime detection (market breadth, multiple MAs)
2. Inverse ETF support for bear markets
3. Individual sector trend filters

Improvements over v1:
- Market breadth regime detection (% sectors above 200 MA)
- Optional inverse ETF allocation when all sectors bearish
- Sector-level trend filters (only buy above 200 MA)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationAdaptive_v2(BaseModel):
    """
    Adaptive sector rotation with enhanced regime detection and inverse ETF support.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationAdaptive_v2",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        inverse_asset: str = "SH",  # Inverse S&P 500 ETF
        use_inverse: bool = True,  # Enable inverse ETF in bear markets
        # Regime detection parameters
        breadth_threshold: float = 0.5,  # Go defensive if <50% sectors above 200 MA
        use_breadth_regime: bool = True,  # Use breadth for regime detection
        # Sector trend filter
        require_above_ma: bool = True,  # Only buy sectors above their 200 MA
        sector_ma_period: int = 200,
        # ATR parameters
        atr_period: int = 14,
        take_profit_atr_mult: float = 2.0,
        stop_loss_atr_mult: float = 1.0,
        # PDT and fee parameters
        min_hold_days: int = 2,
        min_profit_bps: float = 10.0,
        # Bull mode parameters
        bull_momentum_period: int = 126,
        bull_top_n: int = 4,
        bull_min_momentum: float = 0.10,
        bull_leverage: float = 1.5,
        # Bear mode parameters
        bear_momentum_period: int = 126,
        bear_top_n: int = 2,
        bear_min_momentum: float = 0.10,
        bear_leverage: float = 0.5,  # Reduced from 1.0
    ):
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]

        self.defensive_asset = defensive_asset
        self.inverse_asset = inverse_asset
        self.use_inverse = use_inverse

        # Build universe
        self.all_assets = self.sectors + [defensive_asset]
        if use_inverse and inverse_asset:
            self.all_assets.append(inverse_asset)

        self.assets = self.all_assets
        self.model_id = model_id

        # Regime detection
        self.breadth_threshold = breadth_threshold
        self.use_breadth_regime = use_breadth_regime

        # Sector trend filter
        self.require_above_ma = require_above_ma
        self.sector_ma_period = sector_ma_period

        # ATR parameters
        self.atr_period = atr_period
        self.take_profit_atr_mult = take_profit_atr_mult
        self.stop_loss_atr_mult = stop_loss_atr_mult

        # PDT and fee parameters
        self.min_hold_days = min_hold_days
        self.min_profit_bps = min_profit_bps

        # Bull mode parameters
        self.bull_momentum_period = bull_momentum_period
        self.bull_top_n = bull_top_n
        self.bull_min_momentum = bull_min_momentum
        self.bull_leverage = bull_leverage

        # Bear mode parameters
        self.bear_momentum_period = bear_momentum_period
        self.bear_top_n = bear_top_n
        self.bear_min_momentum = bear_min_momentum
        self.bear_leverage = bear_leverage

        super().__init__(
            name=model_id,
            version="2.0.0",
            universe=self.all_assets
        )

        # State tracking
        self.last_rebalance: Optional[pd.Timestamp] = None
        self.entry_prices: Dict[str, float] = {}
        self.entry_timestamps: Dict[str, pd.Timestamp] = {}
        self.entry_atr: Dict[str, float] = {}

    def _calculate_atr(self, features: pd.DataFrame, period: int = None) -> float:
        """Calculate Average True Range."""
        period = period or self.atr_period

        high_col = 'High' if 'High' in features.columns else 'high'
        low_col = 'Low' if 'Low' in features.columns else 'low'
        close_col = 'Close' if 'Close' in features.columns else 'close'

        high = features[high_col]
        low = features[low_col]
        close = features[close_col]

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr.iloc[-1] if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else 0.0

    def _get_current_price(self, features: pd.DataFrame) -> float:
        """Get current close price from features."""
        close_col = 'Close' if 'Close' in features.columns else 'close'
        return features[close_col].iloc[-1]

    def _is_above_ma(self, features: pd.DataFrame, period: int = 200) -> bool:
        """Check if current price is above moving average."""
        close_col = 'Close' if 'Close' in features.columns else 'close'
        if len(features) < period:
            return True  # Not enough data, allow trading

        current_price = features[close_col].iloc[-1]
        ma = features[close_col].rolling(period).mean().iloc[-1]

        return current_price > ma

    def _calculate_market_breadth(self, context: Context) -> float:
        """Calculate % of sectors above their 200 MA."""
        above_count = 0
        total_count = 0

        for sector in self.sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]
            if len(features) < 200:
                continue

            total_count += 1
            if self._is_above_ma(features, 200):
                above_count += 1

        if total_count == 0:
            return 0.5  # Neutral if no data

        return above_count / total_count

    def _detect_regime(self, context: Context) -> bool:
        """
        Detect market regime using multiple signals.
        Returns True for bull, False for bear.
        """
        signals = []

        # Signal 1: XLK above 200 MA (original method)
        if 'XLK' in context.asset_features:
            xlk_features = context.asset_features['XLK']
            if len(xlk_features) >= 200:
                signals.append(self._is_above_ma(xlk_features, 200))

        # Signal 2: Market breadth
        if self.use_breadth_regime:
            breadth = self._calculate_market_breadth(context)
            signals.append(breadth >= self.breadth_threshold)

        # Majority vote
        if not signals:
            return True  # Default to bull

        return sum(signals) > len(signals) / 2

    def _check_exit_conditions(
        self,
        symbol: str,
        current_price: float,
        current_time: pd.Timestamp
    ) -> tuple[bool, str]:
        """Check if position should be exited based on ATR targets or stop loss."""
        if symbol not in self.entry_prices:
            return False, ""

        entry_price = self.entry_prices[symbol]
        entry_time = self.entry_timestamps[symbol]
        entry_atr = self.entry_atr.get(symbol, 0)

        # PDT protection
        days_held = (current_time - entry_time).days
        if days_held < self.min_hold_days:
            return False, "pdt_protection"

        # Calculate P&L
        pnl_pct = (current_price - entry_price) / entry_price
        pnl_bps = pnl_pct * 10000

        # Take profit check
        if entry_atr > 0:
            take_profit_price = entry_price + (entry_atr * self.take_profit_atr_mult)
            if current_price >= take_profit_price:
                return True, "take_profit"

            # Stop loss check
            stop_loss_price = entry_price - (entry_atr * self.stop_loss_atr_mult)
            if current_price <= stop_loss_price:
                return True, "stop_loss"

        # Fee protection
        if pnl_bps > 0 and pnl_bps < self.min_profit_bps:
            return False, "fee_protection"

        return False, ""

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Generate target weights with enhanced regime detection and inverse ETF support."""

        # Detect regime
        is_bull = self._detect_regime(context)

        if is_bull:
            momentum_period = self.bull_momentum_period
            top_n = self.bull_top_n
            min_momentum = self.bull_min_momentum
            target_leverage = self.bull_leverage
        else:
            momentum_period = self.bear_momentum_period
            top_n = self.bear_top_n
            min_momentum = self.bear_min_momentum
            target_leverage = self.bear_leverage

        # Check for ATR-based exits on current positions
        exits_triggered = {}
        for symbol, exposure in context.current_exposures.items():
            if exposure > 0 and symbol in context.asset_features:
                features = context.asset_features[symbol]
                current_price = self._get_current_price(features)
                should_exit, reason = self._check_exit_conditions(
                    symbol, current_price, context.timestamp
                )
                if should_exit:
                    exits_triggered[symbol] = reason
                    if symbol in self.entry_prices:
                        del self.entry_prices[symbol]
                    if symbol in self.entry_timestamps:
                        del self.entry_timestamps[symbol]
                    if symbol in self.entry_atr:
                        del self.entry_atr[symbol]

        # Weekly rebalancing check
        if self.last_rebalance is not None and not exits_triggered:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < 7:
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=context.current_exposures,
                    hold_current=True
                )

        self.last_rebalance = context.timestamp

        # Calculate momentum for each sector
        sector_momentum = {}
        sector_atr = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]
            if len(features) < momentum_period + 1:
                continue

            # Apply sector trend filter
            if self.require_above_ma and not self._is_above_ma(features, self.sector_ma_period):
                continue  # Skip sectors below their MA

            close_col = 'Close' if 'Close' in features.columns else 'close'
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum

            atr = self._calculate_atr(features)
            sector_atr[sector] = atr

        # Initialize weights
        weights = {asset: 0.0 for asset in self.all_assets}

        # Force exit positions that triggered stops
        for symbol in exits_triggered:
            weights[symbol] = 0.0

        # If no sectors pass filters, go defensive/inverse
        if len(sector_momentum) == 0:
            if not is_bull and self.use_inverse:
                weights[self.inverse_asset] = 1.0
            else:
                weights[self.defensive_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Rank sectors by momentum
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
        top_sectors = ranked_sectors[:top_n]

        # If all top sectors are bearish, go defensive/inverse
        if all(mom < min_momentum for _, mom in top_sectors):
            if not is_bull and self.use_inverse:
                weights[self.inverse_asset] = 1.0
            else:
                weights[self.defensive_asset] = 1.0
        else:
            # Hold top N sectors with positive momentum
            positive_sectors = [(s, m) for s, m in top_sectors if m >= min_momentum]

            if len(positive_sectors) > 0:
                weight_per_sector = target_leverage / len(positive_sectors)
                for sector, _ in positive_sectors:
                    weights[sector] = weight_per_sector

                    # Track entry for new positions
                    if sector not in self.entry_prices:
                        features = context.asset_features[sector]
                        self.entry_prices[sector] = self._get_current_price(features)
                        self.entry_timestamps[sector] = context.timestamp
                        self.entry_atr[sector] = sector_atr.get(sector, 0)
            else:
                if not is_bull and self.use_inverse:
                    weights[self.inverse_asset] = 1.0
                else:
                    weights[self.defensive_asset] = 1.0

        # Clear tracking for positions we're exiting
        for symbol in list(self.entry_prices.keys()):
            if weights.get(symbol, 0) == 0:
                del self.entry_prices[symbol]
                if symbol in self.entry_timestamps:
                    del self.entry_timestamps[symbol]
                if symbol in self.entry_atr:
                    del self.entry_atr[symbol]

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"SectorRotationAdaptive_v2(model_id='{self.model_id}', "
            f"use_inverse={self.use_inverse}, use_breadth={self.use_breadth_regime})"
        )
