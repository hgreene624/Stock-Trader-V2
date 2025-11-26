"""
AdaptiveRegimeSwitcher_v4

More robust version designed to fix v3's overfitting issues.

Key Changes from v3 (addressing validation failures):
1. Reduced bull leverage: 2.0x → 1.25x (more conservative, less curve-fit)
2. More conservative VIX thresholds: 28/40 → 30/45 (less sensitive to noise)
3. Removed ATR stops (they were overfit to 2020-2024 volatility patterns)
4. Added market breadth filter (only bull mode if >50% of sectors positive)
5. Monthly rebalancing (from weekly) to reduce churn and costs

Validation Strategy:
- Train on 2018-2022 (avoid 2020-2024 that v3 used)
- Validate with monkey tests
- Test on 2023-2024 out-of-sample
- Must beat SPY and pass monkey test (>90% of random variants)

Design Philosophy:
- Simplicity over complexity (removed ATR stops)
- Conservative leverage (1.25x max vs v3's 2.0x)
- Robust thresholds (less sensitive to specific periods)
- Market breadth confirmation (avoid false bull signals)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class AdaptiveRegimeSwitcher_v4(BaseModel):
    """
    Robust regime-switching model with conservative parameters.

    Designed to work across different market conditions, not just 2020-2024.
    """

    def __init__(
        self,
        model_id: str = "AdaptiveRegimeSwitcher_v4",
        # Sector universe
        sectors: list[str] = None,
        defensive_asset: str = "TLT",
        # VIX thresholds (MORE CONSERVATIVE than v3's 28/40)
        vix_defensive: float = 30.0,    # VIX > 30: Consider defensive (if price weak)
        vix_extreme: float = 45.0,       # VIX > 45: Full defensive (if price weak)
        # Price confirmation (same as v3 - this worked)
        use_price_confirmation: bool = True,
        spy_symbol: str = "SPY",
        price_ma_period: int = 200,
        defensive_price_threshold: float = 0.98,
        extreme_price_threshold: float = 0.95,
        # Bull mode parameters
        bull_momentum_period: int = 126,
        bull_top_n: int = 4,
        bull_min_momentum: float = 0.10,
        bull_leverage: float = 1.25,     # REDUCED from v3's 2.0x
        bull_breadth_threshold: float = 0.5,  # NEW: Require >50% sectors positive
        # Defensive mode parameters
        defensive_sectors: list[str] = None,
        defensive_top_n: int = 2,
        defensive_leverage: float = 1.0,
        # Rebalancing (MONTHLY vs v3's WEEKLY)
        rebalance_days: int = 30,        # Rebalance monthly to reduce churn
    ):
        """
        Initialize AdaptiveRegimeSwitcher v4 with robust parameters.

        Args:
            model_id: Unique model identifier
            sectors: Full sector universe
            defensive_asset: Safe haven asset (TLT)
            vix_defensive: VIX threshold for defensive (30, up from v3's 28)
            vix_extreme: VIX threshold for full defensive (45, up from v3's 40)
            bull_leverage: Maximum leverage in bull mode (1.25x, down from v3's 2.0x)
            bull_breadth_threshold: Minimum fraction of sectors positive (NEW)
            rebalance_days: Days between rebalances (30, up from v3's 7)
        """
        self.model_id = model_id

        # Universe
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]
        self.defensive_asset = defensive_asset
        self.all_assets = self.sectors + [defensive_asset]
        self.assets = self.all_assets

        # Defensive sectors
        self.defensive_sectors = defensive_sectors or ['XLP', 'XLU', defensive_asset]

        # VIX thresholds (MORE CONSERVATIVE)
        self.vix_defensive = vix_defensive
        self.vix_extreme = vix_extreme

        # Price confirmation
        self.use_price_confirmation = use_price_confirmation
        self.spy_symbol = spy_symbol
        self.price_ma_period = price_ma_period
        self.defensive_price_threshold = defensive_price_threshold
        self.extreme_price_threshold = extreme_price_threshold

        # Bull mode
        self.bull_momentum_period = bull_momentum_period
        self.bull_top_n = bull_top_n
        self.bull_min_momentum = bull_min_momentum
        self.bull_leverage = bull_leverage
        self.bull_breadth_threshold = bull_breadth_threshold  # NEW

        # Defensive mode
        self.defensive_top_n = defensive_top_n
        self.defensive_leverage = defensive_leverage

        # Rebalancing (REDUCED FREQUENCY)
        self.rebalance_days = rebalance_days

        super().__init__(
            name=model_id,
            version="4.0.0",
            universe=self.all_assets
        )

        # State tracking
        self.last_rebalance: Optional[pd.Timestamp] = None

        print(f"[AdaptiveRegimeSwitcher_v4] Initialized with ROBUST parameters")
        print(f"  Universe: {sorted(self.all_assets)}")
        print(f"  VIX thresholds: {self.vix_defensive}/{self.vix_extreme} (more conservative)")
        print(f"  Bull leverage: {self.bull_leverage}x (reduced from v3's 2.0x)")
        print(f"  Breadth threshold: {self.bull_breadth_threshold*100:.0f}% (NEW)")
        print(f"  Rebalance frequency: {self.rebalance_days} days (reduced from v3's 7)")
        print(f"  ATR stops: REMOVED (simplified)")

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

        Returns:
            True if price is weak (below threshold * MA), False otherwise
        """
        if not self.use_price_confirmation:
            return True

        spy_features = context.asset_features.get(self.spy_symbol)
        if spy_features is None or len(spy_features) < self.price_ma_period:
            return True

        close_col = 'Close' if 'Close' in spy_features.columns else 'close'
        current_price = spy_features[close_col].iloc[-1]
        ma = spy_features[close_col].rolling(window=self.price_ma_period).mean().iloc[-1]

        if pd.isna(current_price) or pd.isna(ma) or ma == 0:
            return True

        return current_price < (ma * threshold)

    def _calculate_market_breadth(self, context: Context) -> float:
        """
        Calculate market breadth (fraction of sectors with positive momentum).

        This is NEW in v4 - helps avoid false bull signals.
        """
        positive_count = 0
        total_count = 0

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
            total_count += 1
            if momentum > 0:
                positive_count += 1

        if total_count == 0:
            return 0.0

        return positive_count / total_count

    def _get_current_price(self, features: pd.DataFrame) -> float:
        """Get current close price."""
        close_col = 'Close' if 'Close' in features.columns else 'close'
        return features[close_col].iloc[-1]

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on VIX regime with breadth confirmation.
        """
        vix_level = self._get_vix_level(context)
        breadth = self._calculate_market_breadth(context)

        # Detect regime with VIX + price + breadth confirmation
        price_weak = self._check_price_weakness(context, self.defensive_price_threshold)
        extreme_price_weak = self._check_price_weakness(context, self.extreme_price_threshold)
        breadth_ok = breadth >= self.bull_breadth_threshold

        if vix_level >= self.vix_extreme and extreme_price_weak:
            regime = "extreme"
            mode_description = f"EXTREME (VIX={vix_level:.1f}, price weak)"
        elif vix_level >= self.vix_defensive and price_weak:
            regime = "defensive"
            mode_description = f"DEFENSIVE (VIX={vix_level:.1f}, price weak)"
        elif not breadth_ok:
            # NEW: If breadth is poor, stay defensive even with low VIX
            regime = "defensive"
            mode_description = f"DEFENSIVE (breadth={breadth:.1%} < {self.bull_breadth_threshold:.0%})"
        else:
            regime = "bull"
            mode_description = f"BULL (VIX={vix_level:.1f}, breadth={breadth:.1%})"

        print(f"  [RegimeSwitcher_v4] {mode_description}")

        # Monthly rebalancing check (REDUCED from v3's weekly)
        if self.last_rebalance is not None:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < self.rebalance_days:
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=context.current_exposures,
                    hold_current=True
                )

        self.last_rebalance = context.timestamp

        # Generate weights based on regime
        if regime == "extreme":
            weights = {asset: 0.0 for asset in self.all_assets}
            weights[self.defensive_asset] = 1.0

        elif regime == "defensive":
            weights = self._generate_defensive_weights(context)

        else:  # bull
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
        """Generate weights for bull mode - aggressive but LESS LEVERAGE than v3."""
        sector_momentum = {}

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
            # Allocate with REDUCED leverage (1.25x vs v3's 2.0x)
            weight_per_sector = self.bull_leverage / len(positive_sectors)
            for sector, _ in positive_sectors:
                weights[sector] = weight_per_sector
        else:
            weights[self.defensive_asset] = 1.0

        return weights

    def _generate_defensive_weights(self, context: Context) -> Dict[str, float]:
        """Generate weights for defensive mode."""
        sector_momentum = {}

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

        # Initialize weights
        weights = {asset: 0.0 for asset in self.all_assets}

        if len(sector_momentum) == 0:
            weights[self.defensive_asset] = 1.0
            return weights

        # Rank by momentum
        ranked_sectors = sorted(sector_momentum.items(), key=lambda x: x[1], reverse=True)
        top_sectors = ranked_sectors[:self.defensive_top_n]

        # Allocate with 1.0x leverage (no leverage in defensive)
        weight_per_sector = self.defensive_leverage / len(top_sectors)
        for sector, _ in top_sectors:
            weights[sector] = weight_per_sector

        return weights

    def __repr__(self):
        return (
            f"AdaptiveRegimeSwitcher_v4(model_id='{self.model_id}', "
            f"vix=[{self.vix_defensive}, {self.vix_extreme}], "
            f"leverage={self.bull_leverage}x, "
            f"breadth_filter={self.bull_breadth_threshold:.0%})"
        )
