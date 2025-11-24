"""
SectorRotationConsistent_v5

V5 improvements over v3 (Experiment 007):
1. Tuned crash thresholds (faster detection, quicker recovery)
2. Relative strength filter (only trade sectors > SPY)
3. Correlation-based sizing (reduce weight for correlated sectors)

Target: Beat SPY 14.34% CAGR with DD < 25%
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class SectorRotationConsistent_v5(BaseModel):
    """
    V5: Tuned crash protection + relative strength + correlation sizing.
    """

    def __init__(
        self,
        model_id: str = "SectorRotationConsistent_v5",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",

        # V5: Tuned crash protection (faster detection, quicker recovery)
        crash_drop_threshold: float = -0.05,  # Was -0.07, now -5%
        crash_drop_days: int = 5,
        vix_crash_threshold: float = 30,  # Was 35, now 30
        vix_recovery_threshold: float = 25,
        crash_exposure: float = 0.40,  # Was 0.25, less defensive
        dip_buy_drawdown_threshold: float = -0.15,  # Was -0.20
        dip_buy_weeks: int = 2,  # Was 4, faster recovery

        # V5: Relative strength filter
        use_relative_strength: bool = True,  # Only trade sectors > SPY
        relative_strength_period: int = 63,  # 3-month lookback

        # V5: Correlation-based sizing
        use_correlation_sizing: bool = True,
        correlation_lookback: int = 60,
        correlation_threshold: float = 0.75,  # Reduce weight if corr > 0.75
        correlation_weight_reduction: float = 0.5,  # Reduce to 50% of normal weight

        # Rotation frequency controls
        min_hold_days_low_vol: int = 15,
        min_hold_days_high_vol: int = 5,
        rotation_threshold: float = 0.05,

        # Conservative leverage settings
        bull_leverage: float = 1.2,
        bear_leverage: float = 1.0,
        volatility_leverage_adj: bool = True,

        # Adaptive stop losses
        bull_stop_mult: float = 2.5,
        bear_stop_mult: float = 1.5,
        normal_stop_mult: float = 2.0,

        # Concentration controls
        max_sector_weight: float = 0.5,
        concentration_momentum_threshold: float = 0.8,
        rebalance_threshold: float = 0.15,

        # Trend persistence
        trend_lookback: int = 40,
        momentum_decay: float = 0.95,
        weakness_threshold: float = -0.05,

        # ATR parameters
        atr_period: int = 21,
        take_profit_atr_mult: float = 2.5,

        # Momentum parameters
        momentum_period: int = 126,
        top_n_sectors: int = 4,
        min_momentum: float = 0.10,

        # Volatility regime detection
        vol_lookback: int = 20,
        vol_percentile_low: float = 0.3,
        vol_percentile_high: float = 0.7,
        vix_threshold_low: float = 15,
        vix_threshold_high: float = 25,
    ):
        self.sectors = sectors or [
            'XLK', 'XLF', 'XLE', 'XLV', 'XLI',
            'XLP', 'XLU', 'XLY', 'XLC', 'XLB', 'XLRE'
        ]

        self.defensive_asset = defensive_asset
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

        # V5: New parameters
        self.use_relative_strength = use_relative_strength
        self.relative_strength_period = relative_strength_period
        self.use_correlation_sizing = use_correlation_sizing
        self.correlation_lookback = correlation_lookback
        self.correlation_threshold = correlation_threshold
        self.correlation_weight_reduction = correlation_weight_reduction

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

        # Crash protection state
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
        """Detect current volatility regime (low/normal/high)."""
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

        return 'normal'

    def detect_crash_and_recovery(self, context: Context) -> tuple[bool, float]:
        """V5: Tuned crash detection with faster recovery."""
        if 'SPY' not in context.asset_features:
            return False, 1.0

        spy_data = context.asset_features['SPY']
        if len(spy_data) < self.crash_drop_days + 1:
            return False, 1.0

        current_price = spy_data['close'].iloc[-1]
        current_date = context.timestamp

        if self.spy_peak_price is None:
            self.spy_peak_price = current_price
        else:
            self.spy_peak_price = max(self.spy_peak_price, current_price)

        price_n_days_ago = spy_data['close'].iloc[-self.crash_drop_days - 1]
        recent_return = (current_price - price_n_days_ago) / price_n_days_ago

        drawdown_from_peak = (current_price - self.spy_peak_price) / self.spy_peak_price
        self.max_drawdown_seen = min(self.max_drawdown_seen, drawdown_from_peak)

        current_vix = None
        if '^VIX' in context.asset_features:
            vix_data = context.asset_features['^VIX']
            if len(vix_data) > 0:
                current_vix = vix_data['close'].iloc[-1]

        crash_triggered = (
            recent_return < self.crash_drop_threshold or
            (current_vix is not None and current_vix > self.vix_crash_threshold)
        )

        if crash_triggered and not self.crash_mode_active:
            self.crash_mode_active = True
            self.dip_buy_mode_active = False
            self.dip_buy_start_date = None

        if self.crash_mode_active:
            sma_10 = spy_data['close'].rolling(10).mean().iloc[-1]
            vix_ok = current_vix is None or current_vix < self.vix_recovery_threshold
            price_ok = current_price > sma_10

            if vix_ok and price_ok:
                if self.max_drawdown_seen < self.dip_buy_drawdown_threshold:
                    self.crash_mode_active = False
                    self.dip_buy_mode_active = True
                    self.dip_buy_start_date = current_date
                else:
                    self.crash_mode_active = False

        if self.dip_buy_mode_active:
            if self.dip_buy_start_date is not None:
                days_since_start = (current_date - self.dip_buy_start_date).days
                weeks_elapsed = days_since_start / 7.0

                if weeks_elapsed >= self.dip_buy_weeks:
                    self.dip_buy_mode_active = False
                    self.dip_buy_start_date = None
                    self.max_drawdown_seen = 0.0
                    return False, 1.0
                else:
                    exposure = self.crash_exposure + (1 - self.crash_exposure) * (weeks_elapsed / self.dip_buy_weeks)
                    return False, exposure

        if self.crash_mode_active:
            return True, self.crash_exposure

        return False, 1.0

    def detect_market_regime(self, context: Context) -> str:
        """Detect market regime with 5 states."""
        if 'SPY' not in context.asset_features:
            return 'volatile_bull'

        spy_data = context.asset_features['SPY']
        if len(spy_data) < 200:
            return 'volatile_bull'

        sma_200 = spy_data['close'].rolling(200).mean().iloc[-1]
        sma_50 = spy_data['close'].rolling(50).mean().iloc[-1]
        sma_20 = spy_data['close'].rolling(20).mean().iloc[-1]
        current_price = spy_data['close'].iloc[-1]

        vol_regime = self.detect_volatility_regime(context)

        scores = self.calculate_momentum_scores(context)
        if scores:
            dispersion = self.calculate_sector_dispersion(scores)
            if dispersion > 0.15:
                return 'concentrated'

        if current_price < sma_200 and sma_50 < sma_200:
            if current_price > sma_20 and sma_20 > sma_50:
                return 'recovery'
            return 'bear'
        elif current_price > sma_200 and sma_50 > sma_200:
            if vol_regime == 'low':
                return 'steady_bull'
            else:
                return 'volatile_bull'
        else:
            if current_price > sma_50:
                return 'volatile_bull'
            else:
                return 'recovery'

    def calculate_sector_dispersion(self, scores: Dict[str, float]) -> float:
        """Calculate dispersion of sector momentum scores."""
        if not scores or len(scores) < 2:
            return 0.0

        values = list(scores.values())
        sorted_vals = sorted(values, reverse=True)

        top_score = sorted_vals[0]
        avg_score = np.mean(values)

        if avg_score == 0:
            return 0.0

        dispersion = (top_score - avg_score) / abs(avg_score) if avg_score != 0 else 0
        return max(0, dispersion)

    def calculate_drawdown_protection_factor(self, context: Context) -> float:
        """Calculate position size multiplier based on drawdown protection rules."""
        current_nav = context.portfolio_value if hasattr(context, 'portfolio_value') else None
        if current_nav is None:
            return 1.0

        current_date = context.timestamp
        current_year = current_date.year

        if self.current_year != current_year:
            self.current_year = current_year
            self.ytd_start_nav = current_nav
            self.ytd_high_nav = current_nav
            self.profit_lock_active = False
            self.profit_lock_floor = None

        if self.peak_nav is None:
            self.peak_nav = current_nav
        else:
            self.peak_nav = max(self.peak_nav, current_nav)

        if self.ytd_high_nav is None:
            self.ytd_high_nav = current_nav
        else:
            self.ytd_high_nav = max(self.ytd_high_nav, current_nav)

        drawdown_from_peak = (current_nav - self.peak_nav) / self.peak_nav if self.peak_nav > 0 else 0

        ytd_return = (current_nav - self.ytd_start_nav) / self.ytd_start_nav if self.ytd_start_nav > 0 else 0
        drawdown_from_ytd_high = (current_nav - self.ytd_high_nav) / self.ytd_high_nav if self.ytd_high_nav > 0 else 0

        protection_factor = 1.0

        if drawdown_from_peak < -0.10:
            protection_factor = min(protection_factor, 0.5)
            self.is_in_drawdown_protection = True

        if ytd_return > 0.15:
            self.profit_lock_active = True
            if self.profit_lock_floor is None:
                self.profit_lock_floor = current_nav * 0.95
            else:
                new_floor = current_nav * 0.95
                self.profit_lock_floor = max(self.profit_lock_floor, new_floor)

            if current_nav < self.profit_lock_floor:
                protection_factor = min(protection_factor, 0.5)

        if ytd_return > 0.10 and drawdown_from_ytd_high < -0.05:
            protection_factor = min(protection_factor, 0.5)

        if drawdown_from_peak > -0.05 and self.is_in_drawdown_protection:
            self.is_in_drawdown_protection = False

        return protection_factor

    def calculate_relative_strength(self, context: Context) -> Dict[str, float]:
        """
        V5: Calculate relative strength vs SPY for each sector.
        Returns dict of sector -> relative performance (positive = outperforming SPY)
        """
        relative_strength = {}

        if 'SPY' not in context.asset_features:
            return {sector: 0.0 for sector in self.sectors}

        spy_data = context.asset_features['SPY']
        if len(spy_data) < self.relative_strength_period:
            return {sector: 0.0 for sector in self.sectors}

        spy_return = (
            spy_data['close'].iloc[-1] / spy_data['close'].iloc[-self.relative_strength_period] - 1
        )

        for sector in self.sectors:
            if sector not in context.asset_features:
                relative_strength[sector] = -1.0
                continue

            data = context.asset_features[sector]
            if len(data) < self.relative_strength_period:
                relative_strength[sector] = -1.0
                continue

            sector_return = (
                data['close'].iloc[-1] / data['close'].iloc[-self.relative_strength_period] - 1
            )

            relative_strength[sector] = sector_return - spy_return

        return relative_strength

    def calculate_correlations(self, context: Context) -> Dict[str, Dict[str, float]]:
        """
        V5: Calculate pairwise correlations between sectors.
        """
        correlations = {}
        returns_data = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                continue

            data = context.asset_features[sector]
            if len(data) < self.correlation_lookback:
                continue

            returns = data['close'].pct_change().iloc[-self.correlation_lookback:]
            returns_data[sector] = returns

        for sector in returns_data:
            correlations[sector] = {}
            for other_sector in returns_data:
                if sector == other_sector:
                    correlations[sector][other_sector] = 1.0
                else:
                    corr = returns_data[sector].corr(returns_data[other_sector])
                    correlations[sector][other_sector] = corr if not np.isnan(corr) else 0.0

        return correlations

    def apply_correlation_sizing(self, weights: Dict[str, float], context: Context) -> Dict[str, float]:
        """V5: Reduce weights for highly correlated sectors."""
        if not self.use_correlation_sizing or len(weights) < 2:
            return weights

        correlations = self.calculate_correlations(context)
        if not correlations:
            return weights

        adjusted_weights = weights.copy()
        sectors_in_portfolio = [s for s in weights if s in self.sectors and weights[s] > 0]

        processed_pairs = set()

        for sector in sectors_in_portfolio:
            if sector not in correlations:
                continue

            for other_sector in sectors_in_portfolio:
                if sector == other_sector:
                    continue

                pair = tuple(sorted([sector, other_sector]))
                if pair in processed_pairs:
                    continue
                processed_pairs.add(pair)

                if other_sector not in correlations.get(sector, {}):
                    continue

                corr = correlations[sector][other_sector]

                if corr > self.correlation_threshold:
                    if adjusted_weights.get(sector, 0) < adjusted_weights.get(other_sector, 0):
                        lower_sector = sector
                    else:
                        lower_sector = other_sector

                    if lower_sector in adjusted_weights:
                        adjusted_weights[lower_sector] *= self.correlation_weight_reduction

        return adjusted_weights

    def calculate_momentum_scores(self, context: Context) -> Dict[str, float]:
        """Calculate risk-adjusted momentum scores for each sector."""
        scores = {}

        for sector in self.sectors:
            if sector not in context.asset_features:
                scores[sector] = 0.0
                continue

            data = context.asset_features[sector]
            if len(data) < self.momentum_period:
                scores[sector] = 0.0
                continue

            returns = data['close'].pct_change()

            recent_momentum = returns.iloc[-20:].mean() * 252
            recent_vol = returns.iloc[-20:].std() * (252 ** 0.5)

            medium_momentum = returns.iloc[-60:].mean() * 252
            medium_vol = returns.iloc[-60:].std() * (252 ** 0.5)

            long_momentum = returns.iloc[-self.momentum_period:].mean() * 252
            long_vol = returns.iloc[-self.momentum_period:].std() * (252 ** 0.5)

            eps = 0.01
            recent_score = recent_momentum / max(recent_vol, eps)
            medium_score = medium_momentum / max(medium_vol, eps)
            long_score = long_momentum / max(long_vol, eps)

            score = (
                recent_score * 1.0 +
                medium_score * self.momentum_decay +
                long_score * (self.momentum_decay ** 2)
            ) / (1 + self.momentum_decay + self.momentum_decay ** 2)

            scores[sector] = score

        return scores

    def should_rotate(self, current_sector: str, best_sector: str,
                     scores: Dict[str, float]) -> bool:
        """Determine if rotation is warranted based on score difference."""
        if current_sector not in scores or best_sector not in scores:
            return True

        score_diff = scores[best_sector] - scores[current_sector]

        if scores[current_sector] < self.weakness_threshold:
            return True

        return score_diff > self.rotation_threshold

    def get_adaptive_parameters(self, context: Context) -> Dict:
        """Get adaptive parameters based on current market conditions."""
        market_regime = self.detect_market_regime(context)

        regime_params = {
            'steady_bull': {
                'min_hold_days': 21,
                'leverage_mult': 0.83,
                'top_n_adj': -2,
                'stop_loss_mult': 2.5,
            },
            'volatile_bull': {
                'min_hold_days': 7,
                'leverage_mult': 1.04,
                'top_n_adj': -1,
                'stop_loss_mult': 2.0,
            },
            'recovery': {
                'min_hold_days': 5,
                'leverage_mult': 1.04,
                'top_n_adj': -1,
                'stop_loss_mult': 1.8,
            },
            'bear': {
                'min_hold_days': 5,
                'leverage_mult': 1.0,
                'top_n_adj': -2,
                'stop_loss_mult': 1.5,
                'use_bear_leverage': True,
            },
            'concentrated': {
                'min_hold_days': 14,
                'leverage_mult': 1.04,
                'top_n_adj': -3,
                'stop_loss_mult': 2.0,
                'max_weight': 0.6,
            }
        }

        params = regime_params.get(market_regime, regime_params['volatile_bull'])

        if params.get('use_bear_leverage', False):
            base_leverage = self.bear_leverage
        else:
            base_leverage = self.bull_leverage

        params['leverage'] = base_leverage * params['leverage_mult']
        params['top_n'] = max(1, self.top_n_sectors + params['top_n_adj'])
        params['regime'] = market_regime

        return params

    def apply_concentration_boost(self, weights: Dict[str, float],
                                 scores: Dict[str, float]) -> Dict[str, float]:
        """Allow concentration in strongly trending sectors."""
        if not scores:
            return weights

        best_sector = max(scores, key=scores.get)
        best_score = scores[best_sector]

        min_score = min(scores.values())
        max_score = max(scores.values())
        score_range = max_score - min_score if max_score != min_score else 1.0

        normalized_score = (best_score - min_score) / score_range

        if normalized_score >= self.concentration_momentum_threshold:
            if best_sector in weights:
                original_weight = weights[best_sector]
                boosted_weight = min(original_weight * 1.5, self.max_sector_weight)

                boost_amount = boosted_weight - original_weight
                other_total = sum(w for s, w in weights.items() if s != best_sector)

                if other_total > 0:
                    adjusted_weights = {}
                    for sector, weight in weights.items():
                        if sector == best_sector:
                            adjusted_weights[sector] = boosted_weight
                        else:
                            reduction = (weight / other_total) * boost_amount
                            adjusted_weights[sector] = max(0, weight - reduction)

                    return adjusted_weights

        return weights

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """Generate portfolio weights with V5 improvements."""
        weights = {}
        current_date = context.timestamp

        is_crash_mode, crash_exposure_mult = self.detect_crash_and_recovery(context)
        params = self.get_adaptive_parameters(context)
        protection_factor = self.calculate_drawdown_protection_factor(context)
        effective_exposure = min(crash_exposure_mult, protection_factor)

        scores = self.calculate_momentum_scores(context)

        # V5: Apply relative strength filter
        if self.use_relative_strength:
            relative_strength = self.calculate_relative_strength(context)
            for sector in scores:
                if relative_strength.get(sector, 0) < 0:
                    scores[sector] = 0.0

        sorted_sectors = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_momentum = sorted_sectors[0][1] if sorted_sectors else 0
        top_n = params.get('top_n', self.top_n_sectors)

        if top_momentum < self.min_momentum:
            weights[self.defensive_asset] = params['leverage'] * effective_exposure
        else:
            selected_sectors = []
            for sector, score in sorted_sectors[:top_n]:
                if score >= self.min_momentum:
                    selected_sectors.append(sector)

            if not selected_sectors:
                weights[self.defensive_asset] = params['leverage'] * effective_exposure
            else:
                should_rebalance = False

                if self.last_rotation_date is not None:
                    days_held = (current_date - self.last_rotation_date).days
                    if days_held < params['min_hold_days']:
                        for sector in self.current_positions:
                            if sector in scores and scores[sector] >= self.weakness_threshold:
                                weights[sector] = self.current_positions[sector]

                        if not weights:
                            should_rebalance = True
                    else:
                        should_rebalance = True
                else:
                    should_rebalance = True

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
                    base_weight = (params['leverage'] * effective_exposure) / len(selected_sectors)
                    for sector in selected_sectors:
                        weights[sector] = base_weight

                    weights = self.apply_concentration_boost(weights, scores)
                    weights = self.apply_correlation_sizing(weights, context)

                    self.current_positions = weights.copy()
                    self.last_rotation_date = current_date
                else:
                    weights = {}
                    for sector, weight in self.current_positions.items():
                        weights[sector] = weight * effective_exposure

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

        self.peak_nav = None
        self.ytd_start_nav = None
        self.current_year = None
        self.ytd_high_nav = None
        self.is_in_drawdown_protection = False
        self.profit_lock_active = False
        self.profit_lock_floor = None
        self.last_month_end_nav = None

        self.crash_mode_active = False
        self.dip_buy_mode_active = False
        self.dip_buy_start_date = None
        self.spy_peak_price = None
        self.max_drawdown_seen = 0.0
