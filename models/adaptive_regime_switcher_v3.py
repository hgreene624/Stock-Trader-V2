"""
AdaptiveRegimeSwitcher_v3

Enhanced version with PRICE TREND CONFIRMATION to prevent false VIX signals.

Key Changes from v2:
1. Adds SPY price trend confirmation to regime detection
2. Requires BOTH high VIX AND price weakness for defensive mode
3. Filters false volatility spikes (e.g., GameStop Jan 2021)
4. Raised VIX thresholds: 28/40 (from 25/35)
5. Preserves crash protection while avoiding false defensive positioning

Strategy:
- VIX < 28 OR SPY > 200 MA: Aggressive sector rotation (all sectors, 2x leverage)
- VIX 28-40 AND SPY weak: Defensive sector rotation (XLP, XLU, TLT, 1x leverage)
- VIX > 40 AND SPY < 95% of 200 MA: Full defensive (100% TLT)

Design Goal: Beat standalone SectorRotation by protecting capital during REAL crashes
while staying aggressive during volatility-only events.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class AdaptiveRegimeSwitcher_v3(BaseModel):
    """
    Adaptive regime-switching model with price trend confirmation.

    Uses same sector ETFs in all regimes, with VIX + price confirmation.
    """

    def __init__(
        self,
        model_id: str = "AdaptiveRegimeSwitcher_v3",
        # Sector universe (same for all modes)
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        # VIX thresholds (raised from v2's 25/35)
        vix_defensive: float = 28.0,    # VIX > 28: Defensive mode (if price weak)
        vix_extreme: float = 40.0,       # VIX > 40: Full defensive (if price weak)
        # Price confirmation parameters
        use_price_confirmation: bool = True,  # Require price weakness for defensive
        spy_symbol: str = "SPY",
        price_ma_period: int = 200,
        defensive_price_threshold: float = 0.98,  # SPY must be < 98% of 200 MA
        extreme_price_threshold: float = 0.95,    # SPY must be < 95% of 200 MA
        # Bull mode parameters (VIX < 25)
        bull_momentum_period: int = 126,
        bull_top_n: int = 4,
        bull_min_momentum: float = 0.10,
        bull_leverage: float = 2.0,
        # Defensive mode parameters (VIX 25-35)
        defensive_sectors: list[str] = None,  # Defensive sectors to rotate
        defensive_top_n: int = 2,
        defensive_leverage: float = 1.0,
        # ATR exit parameters (same for all modes)
        atr_period: int = 21,
        take_profit_atr_mult: float = 2.48,
        stop_loss_atr_mult: float = 1.6,
        min_hold_days: int = 2,
    ):
        """
        Initialize AdaptiveRegimeSwitcher v3 with price trend confirmation.

        Args:
            model_id: Unique model identifier
            sectors: Full sector universe (used in bull mode)
            defensive_asset: Safe haven asset (TLT)
            vix_defensive: VIX threshold for defensive mode (default: 28, raised from v2's 25)
            vix_extreme: VIX threshold for full defensive (default: 40, raised from v2's 35)
            use_price_confirmation: Enable price trend confirmation (default: True)
            spy_symbol: Symbol to use for price confirmation (default: SPY)
            price_ma_period: MA period for price trend (default: 200)
            defensive_price_threshold: Price must be < this * MA for defensive (default: 0.98)
            extreme_price_threshold: Price must be < this * MA for extreme (default: 0.95)
            bull_*: Parameters for bull mode
            defensive_*: Parameters for defensive mode
            atr_*: ATR-based exit parameters
        """
        self.model_id = model_id

        # Unified sector universe
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]
        self.defensive_asset = defensive_asset
        self.all_assets = self.sectors + [defensive_asset]
        self.assets = self.all_assets  # For BacktestRunner compatibility

        # Defensive sectors (consumer staples, utilities, bonds)
        self.defensive_sectors = defensive_sectors or ['XLP', 'XLU', defensive_asset]

        # VIX thresholds (raised from v2)
        self.vix_defensive = vix_defensive
        self.vix_extreme = vix_extreme

        # Price confirmation parameters (NEW in v3)
        self.use_price_confirmation = use_price_confirmation
        self.spy_symbol = spy_symbol
        self.price_ma_period = price_ma_period
        self.defensive_price_threshold = defensive_price_threshold
        self.extreme_price_threshold = extreme_price_threshold

        # Bull mode parameters
        self.bull_momentum_period = bull_momentum_period
        self.bull_top_n = bull_top_n
        self.bull_min_momentum = bull_min_momentum
        self.bull_leverage = bull_leverage

        # Defensive mode parameters
        self.defensive_top_n = defensive_top_n
        self.defensive_leverage = defensive_leverage

        # ATR parameters
        self.atr_period = atr_period
        self.take_profit_atr_mult = take_profit_atr_mult
        self.stop_loss_atr_mult = stop_loss_atr_mult
        self.min_hold_days = min_hold_days

        super().__init__(
            name=model_id,
            version="3.0.0",
            universe=self.all_assets
        )

        # State tracking (preserved across regime changes)
        self.last_rebalance: Optional[pd.Timestamp] = None
        self.entry_prices: Dict[str, float] = {}
        self.entry_timestamps: Dict[str, pd.Timestamp] = {}
        self.entry_atr: Dict[str, float] = {}

        print(f"[AdaptiveRegimeSwitcher_v3] Initialized with price-confirmed regime switching")
        print(f"  Unified universe: {sorted(self.all_assets)}")
        print(f"  Bull sectors: {sorted(self.sectors)}")
        print(f"  Defensive sectors: {sorted(self.defensive_sectors)}")
        print(f"  VIX thresholds: {self.vix_defensive}/{self.vix_extreme}")
        print(f"  Price confirmation: {'ENABLED' if self.use_price_confirmation else 'DISABLED'}")

    def _get_vix_level(self, context: Context) -> float:
        """Get current VIX level."""
        vix_features = context.asset_features.get('^VIX')
        if vix_features is None or len(vix_features) == 0:
            return 0.0

        close_col = 'Close' if 'Close' in vix_features.columns else 'close'
        return float(vix_features[close_col].iloc[-1])

    def _check_price_weakness(self, context: Context, threshold: float) -> bool:
        """
        Check if SPY price shows weakness relative to its MA.

        Args:
            context: Current market context
            threshold: Price must be < threshold * MA (e.g., 0.98 = below 98% of MA)

        Returns:
            True if price is weak (below threshold * MA), False otherwise
        """
        if not self.use_price_confirmation:
            return True  # If price confirmation disabled, always return True

        spy_features = context.asset_features.get(self.spy_symbol)
        if spy_features is None or len(spy_features) < self.price_ma_period:
            return True  # If no SPY data, default to allowing defensive (conservative)

        close_col = 'Close' if 'Close' in spy_features.columns else 'close'
        current_price = spy_features[close_col].iloc[-1]
        ma = spy_features[close_col].rolling(window=self.price_ma_period).mean().iloc[-1]

        if pd.isna(current_price) or pd.isna(ma) or ma == 0:
            return True  # Default to allowing defensive if data issues

        # Price is weak if it's below threshold * MA
        return current_price < (ma * threshold)

    def _calculate_atr(self, features: pd.DataFrame) -> float:
        """Calculate Average True Range."""
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
        atr = tr.rolling(window=self.atr_period).mean()

        return atr.iloc[-1] if len(atr) > 0 and not pd.isna(atr.iloc[-1]) else 0.0

    def _get_current_price(self, features: pd.DataFrame) -> float:
        """Get current close price."""
        close_col = 'Close' if 'Close' in features.columns else 'close'
        return features[close_col].iloc[-1]

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

        # ATR-based exits
        if entry_atr > 0:
            take_profit_price = entry_price + (entry_atr * self.take_profit_atr_mult)
            if current_price >= take_profit_price:
                return True, "take_profit"

            stop_loss_price = entry_price - (entry_atr * self.stop_loss_atr_mult)
            if current_price <= stop_loss_price:
                return True, "stop_loss"

        return False, ""

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on VIX regime.

        Uses SAME universe in all modes, changes strategy not assets.
        """
        vix_level = self._get_vix_level(context)

        # Detect regime based on VIX + price confirmation (v3 enhancement)
        # Require BOTH high VIX AND price weakness for defensive modes
        if vix_level >= self.vix_extreme and self._check_price_weakness(context, self.extreme_price_threshold):
            regime = "extreme"
            mode_description = f"EXTREME DEFENSIVE (VIX={vix_level:.2f}, price weak)"
        elif vix_level >= self.vix_defensive and self._check_price_weakness(context, self.defensive_price_threshold):
            regime = "defensive"
            mode_description = f"DEFENSIVE (VIX={vix_level:.2f}, price weak)"
        else:
            regime = "bull"
            if vix_level >= self.vix_defensive:
                mode_description = f"BULL (VIX={vix_level:.2f}, price strong - overriding VIX)"
            else:
                mode_description = f"BULL (VIX={vix_level:.2f})"

        print(f"  [RegimeSwitcher_v3] {mode_description}")

        # Check for ATR-based exits (applies to all regimes)
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

        # Generate weights based on regime
        if regime == "extreme":
            # VIX > 35: Full defensive (100% TLT)
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0

        elif regime == "defensive":
            # VIX 25-35: Defensive sector rotation
            weights = self._generate_defensive_weights(context)

        else:  # bull
            # VIX < 25: Aggressive sector rotation
            weights = self._generate_bull_weights(context)

        # Log final weights
        if weights:
            weights_str = ", ".join([f"{k}={v:.3f}" for k, v in sorted(weights.items(), key=lambda x: -x[1])[:5]])
            print(f"       Top weights: {weights_str}")

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights,
            hold_current=False
        )

    def _generate_bull_weights(self, context: Context) -> Dict[str, float]:
        """Generate weights for bull mode (VIX < 25) - aggressive rotation."""
        # Calculate momentum for all sectors
        sector_momentum = {}
        sector_atr = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]
            if len(features) < self.bull_momentum_period + 1:
                continue

            close_col = 'Close' if 'Close' in features.columns else 'close'
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(self.bull_momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum
            sector_atr[sector] = self._calculate_atr(features)

        # Initialize weights
        weights = {asset: 0.0 for asset in self.all_assets}

        if len(sector_momentum) == 0:
            weights[self.defensive_asset] = 1.0
            return weights

        # Rank by momentum
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
        top_sectors = ranked_sectors[:self.bull_top_n]

        # Filter by minimum momentum
        positive_sectors = [(s, m) for s, m in top_sectors if m >= self.bull_min_momentum]

        if len(positive_sectors) > 0:
            # Allocate to top momentum sectors with leverage
            weight_per_sector = self.bull_leverage / len(positive_sectors)
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

        # Clear tracking for exited positions
        for symbol in list(self.entry_prices.keys()):
            if weights.get(symbol, 0) == 0:
                del self.entry_prices[symbol]
                if symbol in self.entry_timestamps:
                    del self.entry_timestamps[symbol]
                if symbol in self.entry_atr:
                    del self.entry_atr[symbol]

        return weights

    def _generate_defensive_weights(self, context: Context) -> Dict[str, float]:
        """Generate weights for defensive mode (VIX 25-35) - defensive sectors."""
        # Calculate momentum for defensive sectors only
        sector_momentum = {}
        sector_atr = {}

        for sector in self.defensive_sectors:
            if sector not in context.asset_features:
                continue

            features = context.asset_features[sector]
            if len(features) < self.bull_momentum_period + 1:
                continue

            close_col = 'Close' if 'Close' in features.columns else 'close'
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(self.bull_momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            momentum = (current_price - past_price) / past_price
            sector_momentum[sector] = momentum
            sector_atr[sector] = self._calculate_atr(features)

        # Initialize weights
        weights = {asset: 0.0 for asset in self.all_assets}

        if len(sector_momentum) == 0:
            weights[self.defensive_asset] = 1.0
            return weights

        # Rank by momentum (even in defensive, prefer strength)
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
        top_sectors = ranked_sectors[:self.defensive_top_n]

        # Allocate with reduced leverage
        weight_per_sector = self.defensive_leverage / len(top_sectors)
        for sector, _ in top_sectors:
            weights[sector] = weight_per_sector

            # Track entry for new positions
            if sector not in self.entry_prices:
                features = context.asset_features[sector]
                self.entry_prices[sector] = self._get_current_price(features)
                self.entry_timestamps[sector] = context.timestamp
                self.entry_atr[sector] = sector_atr.get(sector, 0)

        # Clear tracking for exited positions
        for symbol in list(self.entry_prices.keys()):
            if weights.get(symbol, 0) == 0:
                del self.entry_prices[symbol]
                if symbol in self.entry_timestamps:
                    del self.entry_timestamps[symbol]
                if symbol in self.entry_atr:
                    del self.entry_atr[symbol]

        return weights

    def __repr__(self):
        return (
            f"AdaptiveRegimeSwitcher_v3(model_id='{self.model_id}', "
            f"vix_thresholds=[{self.vix_defensive}, {self.vix_extreme}], "
            f"price_confirmation={'ON' if self.use_price_confirmation else 'OFF'}, "
            f"unified_universe={len(self.all_assets)} assets)"
        )
