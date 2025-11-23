"""
SectorRotationConsistent_v4

V4 improvements over v3 to reduce drawdowns:
1. Trend confirmation filter - don't buy sectors in downtrends
2. VIX-based position scaling - reduce exposure when VIX > 25
3. Stricter minimum hold enforcement - prevent churning in choppy markets
4. Better minimum hold period logic

Target: Reduce max drawdown while maintaining alpha over SPY
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationConsistent_v4(BaseModel):
    """
    V4: Drawdown reduction focus.

    V4 improvements over v3:
    - Trend confirmation: Only buy sectors above their 20D SMA
    - VIX scaling: Reduce exposure when VIX > 25
    - Stricter holds: Enforce minimum hold periods to prevent churning
    - Smoother rotation: Don't chase momentum in choppy markets

    Philosophy: Reduce drawdowns, accept slightly lower returns for better Sharpe
    """

    def __init__(
        self,
        model_id: str = "SectorRotationConsistent_v4",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",

        # V4: Drawdown reduction parameters
        trend_sma_period: int = 20,  # Must be above 20D SMA to buy
        vix_scale_threshold: float = 25,  # Scale down when VIX > 25
        vix_max_threshold: float = 35,  # Min exposure when VIX > 35
        min_vix_exposure: float = 0.5,  # Minimum exposure at high VIX
        strict_hold_enforcement: bool = True,  # Enforce hold periods strictly

        # Crash protection parameters
        crash_drop_threshold: float = -0.07,  # -7% in 5 days = crash
        crash_drop_days: int = 5,
        vix_crash_threshold: float = 35,  # VIX > 35 = crash
        vix_recovery_threshold: float = 25,  # VIX < 25 = recovery starting
        crash_exposure: float = 0.25,  # Reduce to 25% during crash
        dip_buy_drawdown_threshold: float = -0.20,  # After 20% drop, enable dip buying
        dip_buy_weeks: int = 4,  # Scale in over 4 weeks

        # Rotation frequency controls
        min_hold_days_low_vol: int = 15,  # Hold longer in trending markets
        min_hold_days_high_vol: int = 5,  # Can rotate faster in volatile markets
        rotation_threshold: float = 0.05,  # Min score difference to trigger rotation

        # Conservative leverage settings
        bull_leverage: float = 1.2,  # Max 1.25x for small accounts
        bear_leverage: float = 1.0,  # No leverage in bear markets
        volatility_leverage_adj: bool = True,  # Reduce leverage when vol is high

        # Adaptive stop losses
        bull_stop_mult: float = 2.5,  # Wider stops in bull markets
        bear_stop_mult: float = 1.5,  # Tighter stops in bear markets
        normal_stop_mult: float = 2.0,  # Default

        # Concentration controls
        max_sector_weight: float = 0.5,  # Allow up to 50% in best sector
        concentration_momentum_threshold: float = 0.8,  # Momentum score for concentration
        rebalance_threshold: float = 0.15,  # Rebalance if deviation > 15%

        # Trend persistence
        trend_lookback: int = 40,  # Days to measure trend strength
        momentum_decay: float = 0.95,  # Decay factor for momentum scoring
        weakness_threshold: float = -0.05,  # Rotate out if return < -5%

        # ATR parameters (from optimized v3)
        atr_period: int = 21,  # Optimized from EA
        take_profit_atr_mult: float = 2.5,

        # Momentum parameters
        momentum_period: int = 126,  # 6-month momentum
        top_n_sectors: int = 4,  # Number of sectors to hold
        min_momentum: float = 0.10,  # Minimum momentum to invest

        # Volatility regime detection
        vol_lookback: int = 20,
        vol_percentile_low: float = 0.3,  # Below 30th percentile = low vol
        vol_percentile_high: float = 0.7,  # Above 70th percentile = high vol
        vix_threshold_low: float = 15,  # VIX < 15 = low vol
        vix_threshold_high: float = 25,  # VIX > 25 = high vol
    ):
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]

        self.defensive_asset = defensive_asset
        # Only tradeable assets in universe (SPY/VIX come from profile)
        self.all_assets = self.sectors + [defensive_asset]
        self.assets = self.all_assets
        self.model_id = model_id

        # Store all parameters
        self.min_hold_days_low_vol = min_hold_days_low_vol
        self.min_hold_days_high_vol = min_hold_days_high_vol
        self.rotation_threshold = rotation_threshold

        self.bull_leverage = bull_leverage
        self.bear_leverage = bear_leverage
        self.volatility_leverage_adj = volatility_leverage_adj

        self.bull_stop_mult = bull_stop_mult
        self.bear_stop_mult = bear_stop_mult
        self.normal_stop_mult = normal_stop_mult

        self.max_sector_weight = max_sector_weight
        self.concentration_momentum_threshold = concentration_momentum_threshold
        self.rebalance_threshold = rebalance_threshold

        self.trend_lookback = trend_lookback
        self.momentum_decay = momentum_decay
        self.weakness_threshold = weakness_threshold

        self.atr_period = atr_period
        self.take_profit_atr_mult = take_profit_atr_mult

        self.momentum_period = momentum_period
        self.top_n_sectors = top_n_sectors
        self.min_momentum = min_momentum

        self.vol_lookback = vol_lookback
        self.vol_percentile_low = vol_percentile_low
        self.vol_percentile_high = vol_percentile_high
        self.vix_threshold_low = vix_threshold_low
        self.vix_threshold_high = vix_threshold_high

        # V4: Drawdown reduction parameters
        self.trend_sma_period = trend_sma_period
        self.vix_scale_threshold = vix_scale_threshold
        self.vix_max_threshold = vix_max_threshold
        self.min_vix_exposure = min_vix_exposure
        self.strict_hold_enforcement = strict_hold_enforcement

        # State tracking
        self.current_positions = {}
        self.position_entry_dates = {}
        self.last_rotation_date = None

        # Drawdown protection state
        self.peak_nav = None
        self.ytd_start_nav = None
        self.current_year = None
        self.ytd_high_nav = None
        self.is_in_drawdown_protection = False
        self.profit_lock_active = False
        self.profit_lock_floor = None
        self.last_month_end_nav = None

        # V3: Crash protection state
        self.crash_drop_threshold = crash_drop_threshold
        self.crash_drop_days = crash_drop_days
        self.vix_crash_threshold = vix_crash_threshold
        self.vix_recovery_threshold = vix_recovery_threshold
        self.crash_exposure = crash_exposure
        self.dip_buy_drawdown_threshold = dip_buy_drawdown_threshold
        self.dip_buy_weeks = dip_buy_weeks

        self.crash_mode_active = False
        self.dip_buy_mode_active = False
        self.dip_buy_start_date = None
        self.spy_peak_price = None
        self.max_drawdown_seen = 0.0

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets,
            lifecycle_stage="research"
        )

    def detect_volatility_regime(self, context: Context) -> str:
        """
        Detect current volatility regime (low/normal/high).
        """
        # Try to use VIX if available
        if '^VIX' in context.asset_features:
            vix_data = context.asset_features['^VIX']
            if len(vix_data) > 0:
                current_vix = vix_data['close'].iloc[-1]
                if current_vix < self.vix_threshold_low:
                    return 'low'
                elif current_vix > self.vix_threshold_high:
                    return 'high'
                else:
                    return 'normal'

        # Fallback: Use SPY volatility
        if 'SPY' in context.asset_features:
            spy_data = context.asset_features['SPY']
            if len(spy_data) > self.vol_lookback:
                returns = spy_data['close'].pct_change()
                vol = returns.rolling(self.vol_lookback).std() * np.sqrt(252)
                current_vol = vol.iloc[-1]
                vol_percentile = (vol < current_vol).mean()

                if vol_percentile < self.vol_percentile_low:
                    return 'low'
                elif vol_percentile > self.vol_percentile_high:
                    return 'high'
                else:
                    return 'normal'

        return 'normal'  # Default

    def check_sector_trend(self, sector: str, context: Context) -> bool:
        """
        V4: Check if sector is in an uptrend (above SMA).
        Returns True if sector is above its SMA, False otherwise.
        """
        if sector not in context.asset_features:
            return False

        data = context.asset_features[sector]
        if len(data) < self.trend_sma_period:
            return True  # Not enough data, allow it

        sma = data['close'].rolling(self.trend_sma_period).mean().iloc[-1]
        current_price = data['close'].iloc[-1]

        return current_price > sma

    def get_vix_exposure_scale(self, context: Context) -> float:
        """
        V4: Scale down exposure based on VIX level.
        Returns multiplier between min_vix_exposure and 1.0.
        """
        if '^VIX' not in context.asset_features:
            return 1.0

        vix_data = context.asset_features['^VIX']
        if len(vix_data) == 0:
            return 1.0

        current_vix = vix_data['close'].iloc[-1]

        if current_vix <= self.vix_scale_threshold:
            return 1.0
        elif current_vix >= self.vix_max_threshold:
            return self.min_vix_exposure
        else:
            # Linear interpolation between thresholds
            scale_range = self.vix_max_threshold - self.vix_scale_threshold
            vix_above = current_vix - self.vix_scale_threshold
            exposure = 1.0 - (1.0 - self.min_vix_exposure) * (vix_above / scale_range)
            return max(self.min_vix_exposure, min(1.0, exposure))

    def detect_crash_and_recovery(self, context: Context) -> tuple[bool, float]:
        """
        V3: Fast crash detection and dip-buy recovery logic.

        Returns:
            (is_crash_mode, exposure_multiplier)
            - is_crash_mode: True if we should be defensive
            - exposure_multiplier: 0.25 during crash, gradual scale up during recovery
        """
        if 'SPY' not in context.asset_features:
            return False, 1.0

        spy_data = context.asset_features['SPY']
        if len(spy_data) < self.crash_drop_days + 1:
            return False, 1.0

        current_price = spy_data['close'].iloc[-1]
        current_date = context.timestamp

        # Track SPY peak for drawdown calculation
        if self.spy_peak_price is None:
            self.spy_peak_price = current_price
        else:
            self.spy_peak_price = max(self.spy_peak_price, current_price)

        # Calculate recent drop (5-day return)
        price_n_days_ago = spy_data['close'].iloc[-self.crash_drop_days - 1]
        recent_return = (current_price - price_n_days_ago) / price_n_days_ago

        # Calculate drawdown from peak
        drawdown_from_peak = (current_price - self.spy_peak_price) / self.spy_peak_price
        self.max_drawdown_seen = min(self.max_drawdown_seen, drawdown_from_peak)

        # Get VIX if available
        current_vix = None
        if '^VIX' in context.asset_features:
            vix_data = context.asset_features['^VIX']
            if len(vix_data) > 0:
                current_vix = vix_data['close'].iloc[-1]

        # CRASH DETECTION: SPY down >7% in 5 days OR VIX > 35
        crash_triggered = (
            recent_return < self.crash_drop_threshold or
            (current_vix is not None and current_vix > self.vix_crash_threshold)
        )

        if crash_triggered and not self.crash_mode_active:
            self.crash_mode_active = True
            self.dip_buy_mode_active = False
            self.dip_buy_start_date = None

        # EXIT CRASH MODE: VIX < 25 and SPY above 10D MA
        if self.crash_mode_active:
            sma_10 = spy_data['close'].rolling(10).mean().iloc[-1]
            vix_ok = current_vix is None or current_vix < self.vix_recovery_threshold
            price_ok = current_price > sma_10

            if vix_ok and price_ok:
                # Check if we should enter dip-buy mode (after big drawdown)
                if self.max_drawdown_seen < self.dip_buy_drawdown_threshold:
                    self.crash_mode_active = False
                    self.dip_buy_mode_active = True
                    self.dip_buy_start_date = current_date
                else:
                    # Smaller drawdown, just exit crash mode normally
                    self.crash_mode_active = False

        # DIP-BUY MODE: Gradual scale-in over N weeks
        if self.dip_buy_mode_active:
            if self.dip_buy_start_date is not None:
                days_since_start = (current_date - self.dip_buy_start_date).days
                weeks_elapsed = days_since_start / 7.0

                if weeks_elapsed >= self.dip_buy_weeks:
                    # Fully scaled back in
                    self.dip_buy_mode_active = False
                    self.dip_buy_start_date = None
                    self.max_drawdown_seen = 0.0  # Reset for next crash
                    return False, 1.0
                else:
                    # Gradual scale-in: 25% per week
                    exposure = self.crash_exposure + (1 - self.crash_exposure) * (weeks_elapsed / self.dip_buy_weeks)
                    return False, exposure

        # Return crash mode status
        if self.crash_mode_active:
            return True, self.crash_exposure

        return False, 1.0

    def detect_market_regime(self, context: Context) -> str:
        """
        Detect market regime with 5 states: steady_bull, volatile_bull, recovery, bear, concentrated.

        V2: Added 'recovery' regime for fast detection of post-crash rebounds (like April 2020).
        """
        if 'SPY' not in context.asset_features:
            return 'volatile_bull'  # Default to cautious

        spy_data = context.asset_features['SPY']
        if len(spy_data) < 200:
            return 'volatile_bull'

        # Use multiple timeframe MAs
        sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        sma_50 = spy_data['close'].rolling(50).mean().iloc[-1]
        sma_20 = spy_data['close'].rolling(20).mean().iloc[-1]
        current_price = spy_data['close'].iloc[-1]

        # Get volatility regime
        vol_regime = self.detect_volatility_regime(context)

        # Check for concentrated market (one sector dominates)
        scores = self.calculate_momentum_scores(context)
        if scores:
            dispersion = self.calculate_sector_dispersion(scores)
            if dispersion > 0.15:  # High dispersion = one sector dominates
                return 'concentrated'

        # V2: Detect RECOVERY regime - price below 200D but 50D crossing up
        # This catches the April-May 2020 rebound while still below 200D MA
        if current_price < sma_200 and sma_50 < sma_200:
            # Check if we're recovering: 20D > 50D and price > 20D
            if current_price > sma_20 and sma_20 > sma_50:
                return 'recovery'  # Aggressive during post-crash rebounds
            return 'bear'
        elif current_price > sma_200 and sma_50 > sma_200:
            # Distinguish steady vs volatile bull
            if vol_regime == 'low':
                return 'steady_bull'
            else:
                return 'volatile_bull'
        else:
            # Transitional: use 50D MA for faster regime change
            if current_price > sma_50:
                return 'volatile_bull'
            else:
                return 'recovery'  # Give benefit of doubt to recoveries

    def calculate_sector_dispersion(self, scores: Dict[str, float]) -> float:
        """
        Calculate dispersion of sector momentum scores.
        High dispersion = concentrated market (one sector dominates).
        """
        if not scores or len(scores) < 2:
            return 0.0

        values = list(scores.values())
        sorted_vals = sorted(values, reverse=True)

        # Ratio of top sector to average
        top_score = sorted_vals[0]
        avg_score = np.mean(values)

        if avg_score == 0:
            return 0.0

        # Dispersion = how much top sector exceeds average
        dispersion = (top_score - avg_score) / abs(avg_score) if avg_score != 0 else 0
        return max(0, dispersion)

    def calculate_drawdown_protection_factor(self, context: Context) -> float:
        """
        Calculate position size multiplier based on drawdown protection rules.
        Returns value between 0.0 (full exit) and 1.0 (full position).

        Rules:
        1. If down 10% from peak, reduce to 50%
        2. If up 15% YTD and down 5% from YTD high, reduce to 50%
        3. Never give back more than 5% of previous month's gains
        """
        # Get current NAV from context
        current_nav = context.portfolio_value if hasattr(context, 'portfolio_value') else None
        if current_nav is None:
            return 1.0  # No protection if no NAV available

        current_date = context.timestamp
        current_year = current_date.year

        # Initialize year tracking
        if self.current_year != current_year:
            self.current_year = current_year
            self.ytd_start_nav = current_nav
            self.ytd_high_nav = current_nav
            self.profit_lock_active = False
            self.profit_lock_floor = None

        # Update peaks
        if self.peak_nav is None:
            self.peak_nav = current_nav
        else:
            self.peak_nav = max(self.peak_nav, current_nav)

        if self.ytd_high_nav is None:
            self.ytd_high_nav = current_nav
        else:
            self.ytd_high_nav = max(self.ytd_high_nav, current_nav)

        # Calculate drawdowns
        drawdown_from_peak = (current_nav - self.peak_nav) / self.peak_nav if self.peak_nav > 0 else 0

        ytd_return = (current_nav - self.ytd_start_nav) / self.ytd_start_nav if self.ytd_start_nav > 0 else 0
        drawdown_from_ytd_high = (current_nav - self.ytd_high_nav) / self.ytd_high_nav if self.ytd_high_nav > 0 else 0

        protection_factor = 1.0

        # Rule 1: Down 10% from all-time peak
        if drawdown_from_peak < -0.10:
            protection_factor = min(protection_factor, 0.5)
            self.is_in_drawdown_protection = True

        # Rule 2: Profit lock - if up 15% YTD, protect gains
        if ytd_return > 0.15:
            self.profit_lock_active = True
            if self.profit_lock_floor is None:
                self.profit_lock_floor = current_nav * 0.95  # Lock in 95% of current value
            else:
                # Ratchet up the floor as we make more gains
                new_floor = current_nav * 0.95
                self.profit_lock_floor = max(self.profit_lock_floor, new_floor)

            # If we've fallen below the floor, reduce exposure
            if current_nav < self.profit_lock_floor:
                protection_factor = min(protection_factor, 0.5)

        # Rule 3: Down 5% from YTD high (when we have profits)
        if ytd_return > 0.10 and drawdown_from_ytd_high < -0.05:
            protection_factor = min(protection_factor, 0.5)

        # Exit protection mode if we recover
        if drawdown_from_peak > -0.05 and self.is_in_drawdown_protection:
            self.is_in_drawdown_protection = False

        return protection_factor

    def calculate_momentum_scores(self, context: Context) -> Dict[str, float]:
        """
        Calculate risk-adjusted momentum scores for each sector.
        Uses momentum divided by volatility (Sharpe-like) to favor consistent returns
        over volatile sectors that may be bouncing from extreme lows.
        """
        scores = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                scores[sector] = 0.0
                continue

            data = context.asset_features[sector]
            if len(data) < self.momentum_period:
                scores[sector] = 0.0
                continue

            # Calculate momentum with decay
            returns = data['close'].pct_change()

            # Recent momentum (last 20 days) - higher weight
            recent_momentum = returns.iloc[-20:].mean() * 252
            recent_vol = returns.iloc[-20:].std() * (252 ** 0.5)

            # Medium-term momentum (last 60 days)
            medium_momentum = returns.iloc[-60:].mean() * 252
            medium_vol = returns.iloc[-60:].std() * (252 ** 0.5)

            # Long-term momentum (full period)
            long_momentum = returns.iloc[-self.momentum_period:].mean() * 252
            long_vol = returns.iloc[-self.momentum_period:].std() * (252 ** 0.5)

            # Risk-adjust each momentum component (Sharpe-like)
            # This penalizes volatile sectors like XLE that bounce from extreme lows
            eps = 0.01  # Avoid division by zero
            recent_score = recent_momentum / max(recent_vol, eps)
            medium_score = medium_momentum / max(medium_vol, eps)
            long_score = long_momentum / max(long_vol, eps)

            # Weighted score with decay
            score = (
                recent_score * 1.0 +
                medium_score * self.momentum_decay +
                long_score * (self.momentum_decay ** 2)
            ) / (1 + self.momentum_decay + self.momentum_decay ** 2)

            scores[sector] = score

        return scores

    def should_rotate(self, current_sector: str, best_sector: str,
                     scores: Dict[str, float]) -> bool:
        """
        Determine if rotation is warranted based on score difference.
        """
        if current_sector not in scores or best_sector not in scores:
            return True

        score_diff = scores[best_sector] - scores[current_sector]

        # Check if current sector is showing weakness
        if scores[current_sector] < self.weakness_threshold:
            return True

        # Check if difference exceeds threshold
        return score_diff > self.rotation_threshold

    def get_adaptive_parameters(self, context: Context) -> Dict:
        """
        Get adaptive parameters based on current market conditions.
        Uses 4-state regime system for better consistency.

        Now uses profile parameters (bull_leverage, bear_leverage, top_n_sectors)
        as base values, with regime-specific multipliers.
        """
        market_regime = self.detect_market_regime(context)

        # Regime-specific multipliers that scale profile parameters
        # leverage_mult: multiplier for bull_leverage (or bear_leverage in bear regime)
        # top_n_adj: adjustment to top_n_sectors (-2 to +1)
        regime_params = {
            'steady_bull': {
                'min_hold_days': 21,      # Hold longer in steady trends
                'leverage_mult': 0.83,    # 83% of bull_leverage (was 1.0/1.2)
                'top_n_adj': -2,          # top_n - 2 (concentrate more)
                'stop_loss_mult': 2.5,    # Wider stops
                'description': 'Patient holding in stable uptrends'
            },
            'volatile_bull': {
                'min_hold_days': 7,       # Can rotate faster
                'leverage_mult': 1.04,    # 104% of bull_leverage (was 1.25/1.2)
                'top_n_adj': -1,          # top_n - 1
                'stop_loss_mult': 2.0,    # Normal stops
                'description': 'Active rotation in volatile uptrends'
            },
            'recovery': {
                'min_hold_days': 5,       # Fast rotation during rebounds
                'leverage_mult': 1.04,    # Full leverage - ride the rebound!
                'top_n_adj': -1,          # top_n - 1
                'stop_loss_mult': 1.8,    # Medium-tight stops
                'description': 'Aggressive during post-crash rebounds (like Apr 2020)'
            },
            'bear': {
                'min_hold_days': 5,       # Quick to exit
                'leverage_mult': 1.0,     # Use bear_leverage directly
                'top_n_adj': -2,          # top_n - 2 (only best ideas)
                'stop_loss_mult': 1.5,    # Tight stops
                'use_bear_leverage': True,  # Flag to use bear_leverage instead
                'description': 'Defensive but not too cautious'
            },
            'concentrated': {
                'min_hold_days': 14,      # Medium hold
                'leverage_mult': 1.04,    # Full leverage on concentrated bet
                'top_n_adj': -3,          # top_n - 3 (ride the winner)
                'stop_loss_mult': 2.0,    # Normal stops
                'max_weight': 0.6,        # Allow 60% concentration
                'description': 'Ride dominant sector (like 2024 tech)'
            }
        }

        params = regime_params.get(market_regime, regime_params['volatile_bull'])

        # Calculate actual leverage from profile parameter
        if params.get('use_bear_leverage', False):
            base_leverage = self.bear_leverage
        else:
            base_leverage = self.bull_leverage

        params['leverage'] = base_leverage * params['leverage_mult']

        # Calculate actual top_n from profile parameter
        params['top_n'] = max(1, self.top_n_sectors + params['top_n_adj'])

        # Store regime for debugging
        params['regime'] = market_regime

        return params

    def apply_concentration_boost(self, weights: Dict[str, float],
                                 scores: Dict[str, float]) -> Dict[str, float]:
        """
        Allow concentration in strongly trending sectors.
        """
        if not scores:
            return weights

        # Find the best sector
        best_sector = max(scores, key=scores.get)
        best_score = scores[best_sector]

        # Normalize scores to [0, 1]
        min_score = min(scores.values())
        max_score = max(scores.values())
        score_range = max_score - min_score if max_score != min_score else 1.0

        normalized_score = (best_score - min_score) / score_range

        # If best sector has strong momentum, allow concentration
        if normalized_score >= self.concentration_momentum_threshold:
            if best_sector in weights:
                # Boost weight up to max_sector_weight
                original_weight = weights[best_sector]
                boosted_weight = min(original_weight * 1.5, self.max_sector_weight)

                # Adjust other weights proportionally
                boost_amount = boosted_weight - original_weight
                other_total = sum(w for s, w in weights.items() if s != best_sector)

                if other_total > 0:
                    adjusted_weights = {}
                    for sector, weight in weights.items():
                        if sector == best_sector:
                            adjusted_weights[sector] = boosted_weight
                        else:
                            # Reduce other weights proportionally
                            reduction = (weight / other_total) * boost_amount
                            adjusted_weights[sector] = max(0, weight - reduction)

                    return adjusted_weights

        return weights

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate portfolio weights using adaptive parameters and crash protection.

        V3: Crash protection takes precedence over normal allocation.
        """
        weights = {}
        current_date = context.timestamp

        # V3: Check crash protection FIRST - this overrides everything
        is_crash_mode, crash_exposure_mult = self.detect_crash_and_recovery(context)

        # Get adaptive parameters (now with regime-specific settings)
        params = self.get_adaptive_parameters(context)

        # Get drawdown protection factor
        protection_factor = self.calculate_drawdown_protection_factor(context)

        # V4: Apply VIX-based scaling
        vix_scale = self.get_vix_exposure_scale(context)

        # V3: Apply crash exposure multiplier (lowest of crash, protection, and VIX)
        effective_exposure = min(crash_exposure_mult, protection_factor, vix_scale)

        # Calculate momentum scores
        scores = self.calculate_momentum_scores(context)

        # Sort sectors by momentum
        sorted_sectors = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Check if we should be in defensive mode
        top_momentum = sorted_sectors[0][1] if sorted_sectors else 0

        # Use regime-specific top_n
        top_n = params.get('top_n', self.top_n_sectors)

        if top_momentum < self.min_momentum:
            # Go defensive
            weights[self.defensive_asset] = params['leverage'] * effective_exposure
        else:
            # Select top N sectors (regime-specific) with V4 trend filter
            selected_sectors = []
            for sector, score in sorted_sectors[:top_n * 2]:  # Check more to account for filtered out
                if score >= self.min_momentum:
                    # V4: Only buy if sector is in uptrend
                    if self.check_sector_trend(sector, context):
                        selected_sectors.append(sector)
                        if len(selected_sectors) >= top_n:
                            break

            if not selected_sectors:
                weights[self.defensive_asset] = params['leverage'] * effective_exposure
            else:
                # Check rotation conditions
                should_rebalance = False

                # V4: Stricter minimum hold period enforcement
                if self.last_rotation_date is not None:
                    days_held = (current_date - self.last_rotation_date).days
                    if days_held < params['min_hold_days']:
                        if self.strict_hold_enforcement:
                            # V4: Strictly keep current positions, no exceptions
                            for sector in self.current_positions:
                                weights[sector] = self.current_positions[sector]
                            # Apply effective exposure to current positions
                            for sector in weights:
                                weights[sector] = weights[sector] * effective_exposure / max(effective_exposure, 0.01)
                        else:
                            # Original behavior: keep if above weakness threshold
                            for sector in self.current_positions:
                                if sector in scores and scores[sector] >= self.weakness_threshold:
                                    weights[sector] = self.current_positions[sector]
                            # If no valid current positions, use new selection
                            if not weights:
                                should_rebalance = True
                    else:
                        should_rebalance = True
                else:
                    should_rebalance = True

                # Check if rotation is needed
                if should_rebalance and self.current_positions:
                    for current_sector in self.current_positions:
                        if current_sector not in selected_sectors:
                            best_new_sector = selected_sectors[0] if selected_sectors else None
                            if best_new_sector and self.should_rotate(current_sector, best_new_sector, scores):
                                should_rebalance = True
                                break
                        else:
                            should_rebalance = False

                if should_rebalance or not self.current_positions:
                    # Rebalance portfolio with effective exposure
                    base_weight = (params['leverage'] * effective_exposure) / len(selected_sectors)
                    for sector in selected_sectors:
                        weights[sector] = base_weight

                    # Apply concentration boost if warranted
                    weights = self.apply_concentration_boost(weights, scores)

                    # Update tracking
                    self.current_positions = weights.copy()
                    self.last_rotation_date = current_date
                else:
                    # Keep current positions but apply effective exposure
                    weights = {}
                    for sector, weight in self.current_positions.items():
                        weights[sector] = weight * effective_exposure

        # Calculate stop loss and take profit levels
        stop_losses = {}
        take_profits = {}

        for asset in weights:
            if asset in context.asset_features:
                data = context.asset_features[asset]
                if len(data) > self.atr_period:
                    # Calculate ATR
                    high = data['high'].iloc[-self.atr_period:]
                    low = data['low'].iloc[-self.atr_period:]
                    close = data['close'].iloc[-self.atr_period:]

                    tr = pd.DataFrame()
                    tr['hl'] = high - low
                    tr['hc'] = abs(high - close.shift(1))
                    tr['lc'] = abs(low - close.shift(1))
                    atr = tr.max(axis=1).mean()

                    current_price = close.iloc[-1]
                    stop_losses[asset] = current_price - (atr * params['stop_loss_mult'])
                    take_profits[asset] = current_price + (atr * self.take_profit_atr_mult)

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights,
            confidence=None,
            urgency="normal",
            horizon="position"
        )

    def reset(self):
        """Reset state for new backtest run."""
        self.current_positions = {}
        self.position_entry_dates = {}
        self.last_rotation_date = None

        # Reset drawdown protection state
        self.peak_nav = None
        self.ytd_start_nav = None
        self.current_year = None
        self.ytd_high_nav = None
        self.is_in_drawdown_protection = False
        self.profit_lock_active = False
        self.profit_lock_floor = None
        self.last_month_end_nav = None

        # V3: Reset crash protection state
        self.crash_mode_active = False
        self.dip_buy_mode_active = False
        self.dip_buy_start_date = None
        self.spy_peak_price = None
        self.max_drawdown_seen = 0.0