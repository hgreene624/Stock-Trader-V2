"""
SectorRotationAdaptive_v3

Enhanced adaptive sector rotation with VOLATILITY TARGETING.

Key feature: Scales leverage based on current volatility vs target volatility.
- When VIX is high (>25), reduces exposure to limit drawdowns
- When VIX is normal (<20), stays fully invested
- Preserves upside in calm markets, limits downside in turbulent ones

Based on v1 optimized parameters with added volatility targeting.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationAdaptive_v3(BaseModel):
    """
    Adaptive sector rotation with volatility targeting.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationAdaptive_v3",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        # Volatility targeting parameters
        use_vol_targeting: bool = True,
        target_vol: float = 0.15,  # Target 15% annual volatility
        vol_lookback: int = 20,  # 20-day realized vol
        vix_symbol: str = "^VIX",  # VIX for vol estimation
        max_scale: float = 1.5,  # Max scale up
        min_scale: float = 0.2,  # Min scale down (20% of normal)
        # ATR parameters
        atr_period: int = 12,
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
        bear_top_n: int = 4,
        bear_min_momentum: float = 0.10,
        bear_leverage: float = 1.5,
    ):
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]

        self.defensive_asset = defensive_asset
        self.all_assets = self.sectors + [defensive_asset]
        self.vix_symbol = vix_symbol  # For vol calculation (not traded)

        self.assets = self.all_assets
        self.model_id = model_id

        # Volatility targeting
        self.use_vol_targeting = use_vol_targeting
        self.target_vol = target_vol
        self.vol_lookback = vol_lookback
        self.max_scale = max_scale
        self.min_scale = min_scale

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
            version="3.0.0",
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

    def _calculate_vol_scale(self, context: Context) -> float:
        """
        Calculate volatility scaling factor.

        Uses VIX as a proxy for market volatility.
        Returns scale factor to apply to leverage.
        """
        if not self.use_vol_targeting:
            return 1.0

        # Try to get VIX data
        if self.vix_symbol in context.asset_features:
            vix_features = context.asset_features[self.vix_symbol]
            close_col = 'Close' if 'Close' in vix_features.columns else 'close'

            if len(vix_features) > 0:
                current_vix = vix_features[close_col].iloc[-1]

                # VIX is annualized implied vol in percentage points
                # e.g., VIX=20 means 20% annualized vol
                current_vol = current_vix / 100.0

                if current_vol > 0:
                    scale = self.target_vol / current_vol
                    # Clamp to min/max bounds
                    scale = max(self.min_scale, min(self.max_scale, scale))
                    return scale

        # Fallback: use realized vol from XLK
        if 'XLK' in context.asset_features:
            xlk_features = context.asset_features['XLK']
            close_col = 'Close' if 'Close' in xlk_features.columns else 'close'

            if len(xlk_features) >= self.vol_lookback:
                returns = xlk_features[close_col].pct_change().dropna()
                if len(returns) >= self.vol_lookback:
                    realized_vol = returns.iloc[-self.vol_lookback:].std() * np.sqrt(252)

                    if realized_vol > 0:
                        scale = self.target_vol / realized_vol
                        scale = max(self.min_scale, min(self.max_scale, scale))
                        return scale

        return 1.0  # Default: no scaling

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
        """Generate target weights with volatility-adjusted leverage."""

        # Determine regime using XLK > 200 MA
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
            base_leverage = self.bull_leverage
        else:
            momentum_period = self.bear_momentum_period
            top_n = self.bear_top_n
            min_momentum = self.bear_min_momentum
            base_leverage = self.bear_leverage

        # Apply volatility scaling
        vol_scale = self._calculate_vol_scale(context)
        target_leverage = base_leverage * vol_scale

        # Check for ATR-based exits
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

        # If no sectors have data, go defensive
        if len(sector_momentum) == 0:
            weights[self.defensive_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Rank sectors by momentum
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
        top_sectors = ranked_sectors[:top_n]

        # If all top sectors are bearish, go defensive
        if all(mom < min_momentum for _, mom in top_sectors):
            weights[self.defensive_asset] = 1.0
        else:
            # Hold top N sectors with positive momentum
            positive_sectors = [(s, m) for s, m in top_sectors if m >= min_momentum]

            if len(positive_sectors) > 0:
                # Apply vol-adjusted leverage
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
            f"SectorRotationAdaptive_v3(model_id='{self.model_id}', "
            f"vol_targeting={self.use_vol_targeting}, target_vol={self.target_vol})"
        )
