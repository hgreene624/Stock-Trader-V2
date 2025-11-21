"""
SectorRotationAdaptive_v1

Unified adaptive sector rotation model with internal bull/bear regime switching,
ATR-based take profit/stop loss, and PDT-aware trading.

Features:
- Single model handles both bull and bear markets internally
- ATR-based take profit (2.5x ATR) and stop loss (1.5x ATR)
- PDT protection: minimum 2-day hold period
- Fee-aware trading: minimum profit threshold to avoid unnecessary churn

Bull Mode (equity_regime == 'bull'):
- Aggressive: 80D momentum, top 4 sectors, 1.3x leverage
- Faster rotation to capture trends

Bear Mode (equity_regime != 'bull'):
- Defensive: 126D momentum, top 2 sectors, 1.0x leverage
- TLT fallback when all sectors bearish

Sectors:
- XLK: Technology
- XLF: Financials
- XLE: Energy
- XLV: Healthcare
- XLI: Industrials
- XLP: Consumer Staples
- XLU: Utilities
- XLY: Consumer Discretionary
- XLC: Communications
- XLB: Materials
- XLRE: Real Estate
- TLT: 20+ Year Treasury Bonds (defensive)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationAdaptive_v1(BaseModel):
    """
    Adaptive sector rotation with ATR-based exits and internal regime switching.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationAdaptive_v1",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        # ATR parameters
        atr_period: int = 14,
        take_profit_atr_mult: float = 2.5,
        stop_loss_atr_mult: float = 1.5,
        # PDT and fee parameters
        min_hold_days: int = 2,
        min_profit_bps: float = 10.0,
        # Bull mode parameters
        bull_momentum_period: int = 80,
        bull_top_n: int = 4,
        bull_min_momentum: float = 0.03,
        bull_leverage: float = 1.3,
        # Bear mode parameters
        bear_momentum_period: int = 126,
        bear_top_n: int = 2,
        bear_min_momentum: float = 0.10,
        bear_leverage: float = 1.0,
    ):
        """
        Initialize SectorRotationAdaptive_v1.

        Args:
            model_id: Unique model identifier
            sectors: List of sector ETFs (default: 11 S&P sectors)
            defensive_asset: Asset to hold when all sectors bearish
            atr_period: Period for ATR calculation
            take_profit_atr_mult: Take profit at entry + X * ATR
            stop_loss_atr_mult: Stop loss at entry - X * ATR
            min_hold_days: Minimum days to hold (PDT protection)
            min_profit_bps: Minimum profit in bps to exit (fee protection)
            bull_momentum_period: Momentum lookback in bull markets
            bull_top_n: Number of sectors in bull markets
            bull_min_momentum: Minimum momentum threshold in bull markets
            bull_leverage: Leverage multiplier in bull markets
            bear_momentum_period: Momentum lookback in bear markets
            bear_top_n: Number of sectors in bear markets
            bear_min_momentum: Minimum momentum threshold in bear markets
            bear_leverage: Leverage multiplier in bear markets
        """
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]

        self.defensive_asset = defensive_asset
        self.all_assets = self.sectors + [defensive_asset]
        self.assets = self.all_assets
        self.model_id = model_id

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
            version="1.0.0",
            universe=self.all_assets
        )

        # State tracking
        self.last_rebalance: Optional[pd.Timestamp] = None
        self.entry_prices: Dict[str, float] = {}  # symbol -> entry price
        self.entry_timestamps: Dict[str, pd.Timestamp] = {}  # symbol -> entry time
        self.entry_atr: Dict[str, float] = {}  # symbol -> ATR at entry

    def _calculate_atr(self, features: pd.DataFrame, period: int = None) -> float:
        """
        Calculate Average True Range.

        Args:
            features: DataFrame with high, low, close columns
            period: ATR period (default: self.atr_period)

        Returns:
            Current ATR value
        """
        period = period or self.atr_period

        # Get column names (handle both cases)
        high_col = 'High' if 'High' in features.columns else 'high'
        low_col = 'Low' if 'Low' in features.columns else 'low'
        close_col = 'Close' if 'Close' in features.columns else 'close'

        high = features[high_col]
        low = features[low_col]
        close = features[close_col]

        # Calculate True Range components
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        # True Range is max of the three
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR is rolling average
        atr = tr.rolling(window=period).mean()

        return atr.iloc[-1] if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else 0.0

    def _get_current_price(self, features: pd.DataFrame) -> float:
        """Get current close price from features."""
        close_col = 'Close' if 'Close' in features.columns else 'close'
        return features[close_col].iloc[-1]

    def _check_exit_conditions(
        self,
        symbol: str,
        current_price: float,
        current_time: pd.Timestamp
    ) -> tuple[bool, str]:
        """
        Check if position should be exited based on ATR targets or stop loss.

        Args:
            symbol: Asset symbol
            current_price: Current price
            current_time: Current timestamp

        Returns:
            Tuple of (should_exit, reason)
        """
        if symbol not in self.entry_prices:
            return False, ""

        entry_price = self.entry_prices[symbol]
        entry_time = self.entry_timestamps[symbol]
        entry_atr = self.entry_atr.get(symbol, 0)

        # PDT protection: check minimum hold period
        days_held = (current_time - entry_time).days
        if days_held < self.min_hold_days:
            return False, "pdt_protection"

        # Calculate P&L in bps
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

        # Fee protection: don't exit for tiny gains
        if pnl_bps > 0 and pnl_bps < self.min_profit_bps:
            return False, "fee_protection"

        return False, ""

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights with internal regime switching and ATR exits.

        Returns:
            ModelOutput with target weights
        """
        # Determine regime using internal detection based on XLK (tech sector as market proxy)
        # Fall back to context.regime if XLK data not available
        is_bull = False
        if 'XLK' in context.asset_features:
            xlk_features = context.asset_features['XLK']
            close_col = 'Close' if 'Close' in xlk_features.columns else 'close'
            if len(xlk_features) >= 200:
                current_price = xlk_features[close_col].iloc[-1]
                ma_200 = xlk_features[close_col].rolling(200).mean().iloc[-1]
                is_bull = current_price > ma_200
        elif context.regime.equity_regime == 'bull':
            is_bull = True

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
                    # Clear entry tracking
                    if symbol in self.entry_prices:
                        del self.entry_prices[symbol]
                    if symbol in self.entry_timestamps:
                        del self.entry_timestamps[symbol]
                    if symbol in self.entry_atr:
                        del self.entry_atr[symbol]

        # Weekly rebalancing check (unless exit triggered)
        if self.last_rebalance is not None and not exits_triggered:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < 7:
                # Hold current positions
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

            # Get current and historical prices
            close_col = 'Close' if 'Close' in features.columns else 'close'
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            # Calculate momentum
            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum

            # Calculate ATR for this sector
            atr = self._calculate_atr(features)
            sector_atr[sector] = atr

        # Rank sectors by momentum
        if len(sector_momentum) == 0:
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Sort sectors by momentum (descending)
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)

        # Initialize weights
        weights = {asset: 0.0 for asset in self.all_assets}

        # Force exit positions that triggered stops
        for symbol in exits_triggered:
            weights[symbol] = 0.0

        # Select top sectors
        top_sectors = ranked_sectors[:top_n]

        # If all top sectors are bearish, go defensive
        if all(mom < min_momentum for _, mom in top_sectors):
            weights[self.defensive_asset] = 1.0
        else:
            # Hold top N sectors with positive momentum
            positive_sectors = [(s, m) for s, m in top_sectors if m >= min_momentum]

            if len(positive_sectors) > 0:
                # Apply leverage to weights (e.g., 1.3x means 130% exposure)
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
            f"SectorRotationAdaptive_v1(model_id='{self.model_id}', "
            f"atr_period={self.atr_period}, "
            f"bull_top_n={self.bull_top_n}, bear_top_n={self.bear_top_n})"
        )
