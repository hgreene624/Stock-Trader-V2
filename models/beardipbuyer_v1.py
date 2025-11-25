"""
BearDipBuyer_v1

A bear market specialist that buys extreme panic dips with quality filters.

Experiment 013's flagship model combining the best features from Exp 012 models:
- Panic detection system with VIX, RSI, and price signals (NEW)
- Quality filters from BearDefensiveRotation_v5 (trend strength, correlation)
- Risk management from BearDefensiveRotation_v3 (volatility scalar, circuit breaker)
- Fast recovery timing from BearDefensiveRotation_v2 (momentum periods)

Strategy:
- Detects three levels of market panic using VIX, RSI, and price vs MA
- Extreme panic (Level 3): VIX>35, RSI<20 → Buy growth aggressively (size=1.0)
- High panic (Level 2): VIX>30, RSI<25 → Buy with quality filters (size=0.7)
- Moderate panic (Level 1): VIX>25 → Tactical rebounds only (size=0.3)
- Applies volatility scaling and circuit breaker for risk management
- Uses trend strength and correlation filters to improve signal quality

Design Philosophy:
- Bear markets create the best buying opportunities at panic extremes
- Combines quantitative panic indicators with quality/risk filters
- Scales position size based on panic level and market conditions
- Preserves capital with circuit breaker during sustained drawdowns
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearDipBuyer_v1(BaseModel):
    """
    Bear market dip buyer - buys extreme panic with quality filters.

    Combines panic detection with proven risk management from Exp 012 models.
    Temporarily ignores regime checks for testing (like Exp 012).
    """

    def __init__(
        self,
        model_id: str = "BearDipBuyer_v1",
        universe: list[str] = None,
        # Panic detection parameters (NEW)
        vix_threshold: float = 30.0,
        vix_extreme_threshold: float = 35.0,
        rsi_period: int = 14,
        rsi_oversold: float = 25.0,
        rsi_extreme: float = 20.0,
        price_ma_period: int = 200,
        price_below_ma_pct: float = 10.0,
        volume_spike_multiplier: float = 2.0,
        # Quality filters (from V5)
        min_trend_strength: float = -0.3,  # Allow mild downtrends for panic buys
        correlation_lookback: int = 20,
        min_correlation: float = 0.3,
        # Risk management (from V3)
        vol_window: int = 20,
        max_volatility: float = 0.05,  # 5% daily vol max
        circuit_breaker_threshold: float = -0.08,  # -8% drawdown
        # Recovery timing (from V2)
        fast_momentum_period: int = 10,
        slow_momentum_period: int = 30,
        rebalance_days: int = 5  # More frequent during volatility
    ):
        """
        Initialize BearDipBuyer_v1 model.

        Args:
            model_id: Unique model identifier
            universe: Trading universe (default: SPY, QQQ, TLT, GLD, UUP, SHY)
            vix_threshold: VIX level for moderate panic (default: 30)
            vix_extreme_threshold: VIX level for extreme panic (default: 35)
            rsi_period: RSI calculation period (default: 14)
            rsi_oversold: RSI oversold threshold (default: 25)
            rsi_extreme: RSI extreme oversold threshold (default: 20)
            price_ma_period: MA period for price distance (default: 200)
            price_below_ma_pct: % below MA for panic signal (default: 10%)
            volume_spike_multiplier: Volume spike detection (default: 2x)
            min_trend_strength: Minimum trend consistency (from V5, default: -0.3)
            correlation_lookback: Correlation calculation period (from V5, default: 20)
            min_correlation: Correlation threshold (from V5, default: 0.3)
            vol_window: Volatility calculation window (from V3, default: 20)
            max_volatility: Maximum daily volatility (from V3, default: 0.05)
            circuit_breaker_threshold: Drawdown threshold (from V3, default: -0.08)
            fast_momentum_period: Fast momentum for entries (from V2, default: 10)
            slow_momentum_period: Slow momentum for confirmation (default: 30)
            rebalance_days: Days between rebalances (default: 5)
        """
        # Universe includes growth assets and safe havens
        self.universe = universe or [
            'SPY',   # S&P 500 - primary growth asset
            'QQQ',   # NASDAQ - tech growth
            'TLT',   # Long-term bonds - safe haven
            'GLD',   # Gold - safe haven
            'UUP',   # US Dollar - safe haven
            'SHY'    # Cash equivalent
        ]

        self.growth_assets = ['SPY', 'QQQ']
        self.safe_assets = ['TLT', 'GLD', 'UUP']
        self.cash_asset = 'SHY'

        # VIX is used for panic detection but NOT traded
        self.vix_symbol = '^VIX'
        # IMPORTANT: Do NOT include VIX in tradeable assets - it's only for reading
        self.all_assets = self.universe.copy()  # Tradeable assets only
        self.assets = self.all_assets  # Required for BacktestRunner

        self.model_id = model_id

        # Panic detection parameters (NEW)
        self.vix_threshold = vix_threshold
        self.vix_extreme_threshold = vix_extreme_threshold
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_extreme = rsi_extreme
        self.price_ma_period = price_ma_period
        self.price_below_ma_pct = price_below_ma_pct
        self.volume_spike_multiplier = volume_spike_multiplier

        # Quality filters (from V5)
        self.min_trend_strength = min_trend_strength
        self.correlation_lookback = correlation_lookback
        self.min_correlation = min_correlation

        # Risk management (from V3)
        self.vol_window = vol_window
        self.max_volatility = max_volatility
        self.circuit_breaker_threshold = circuit_breaker_threshold

        # Recovery timing (from V2)
        self.fast_momentum_period = fast_momentum_period
        self.slow_momentum_period = slow_momentum_period
        self.rebalance_days = rebalance_days

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=self.all_assets  # Now excludes VIX
        )

        # State tracking
        self.last_rebalance: Optional[pd.Timestamp] = None
        self.max_nav = 100000.0  # For circuit breaker (from V3)
        self.circuit_breaker_active = False

    def calculate_panic_level(self, context: Context) -> int:
        """
        Calculate market panic level (0-3).

        Level 0: No panic
        Level 1: Moderate panic (VIX > 25)
        Level 2: High panic (VIX > 30, RSI < 25)
        Level 3: Extreme panic (VIX > 35, RSI < 20)

        Returns:
            Panic level 0-3
        """
        panic_level = 0
        panic_signals = []

        # Get VIX data
        vix_level = 20.0  # Default if VIX not available
        if self.vix_symbol in context.asset_features:
            vix_data = context.asset_features[self.vix_symbol]
            if len(vix_data) > 0:
                close_col = 'Close' if 'Close' in vix_data.columns else 'close'
                vix_level = vix_data[close_col].iloc[-1]

        # DIAGNOSTIC: Print VIX level
        print(f"[{context.timestamp.date()}] VIX={vix_level:.2f}", end="")

        # Get SPY data for RSI and price checks
        spy_data = context.asset_features.get('SPY')
        if spy_data is not None and len(spy_data) > self.rsi_period:
            close_col = 'Close' if 'Close' in spy_data.columns else 'close'

            # Calculate RSI
            rsi = self.calculate_rsi(spy_data[close_col], self.rsi_period)

            # DIAGNOSTIC: Print RSI
            print(f", RSI={rsi:.1f}", end="")

            # Calculate price vs MA
            if len(spy_data) >= self.price_ma_period:
                ma_200 = spy_data[close_col].rolling(self.price_ma_period).mean().iloc[-1]
                current_price = spy_data[close_col].iloc[-1]
                price_vs_ma = ((current_price - ma_200) / ma_200) * 100
            else:
                price_vs_ma = 0
                ma_200 = None

            # Check volume spike (capitulation signal)
            if 'Volume' in spy_data.columns or 'volume' in spy_data.columns:
                vol_col = 'Volume' if 'Volume' in spy_data.columns else 'volume'
                recent_vol = spy_data[vol_col].iloc[-1]
                avg_vol = spy_data[vol_col].tail(20).mean()
                volume_spike = recent_vol > (avg_vol * self.volume_spike_multiplier)
            else:
                volume_spike = False

            # Level 3: Extreme panic (FIX: VIX alone can trigger)
            if vix_level > 50.0:  # Once-in-decade panic (2020: VIX=82)
                panic_level = 3
                panic_signals.append('VIX_GENERATIONAL')
                if rsi < self.rsi_extreme:
                    panic_signals.append('RSI_EXTREME')
                if price_vs_ma < -self.price_below_ma_pct:
                    panic_signals.append('PRICE_EXTREME')
                if volume_spike:
                    panic_signals.append('VOLUME_CAPITULATION')
            elif vix_level > self.vix_extreme_threshold and rsi < self.rsi_extreme:
                panic_level = 3
                panic_signals.extend(['VIX_EXTREME', 'RSI_EXTREME'])
                if price_vs_ma < -self.price_below_ma_pct:
                    panic_signals.append('PRICE_EXTREME')
                if volume_spike:
                    panic_signals.append('VOLUME_CAPITULATION')

            # Level 2: High panic
            elif vix_level > self.vix_threshold and rsi < self.rsi_oversold:
                panic_level = 2
                panic_signals.extend(['VIX_HIGH', 'RSI_OVERSOLD'])
                if price_vs_ma < -self.price_below_ma_pct:
                    panic_signals.append('PRICE_BELOW_MA')

            # Level 1: Moderate panic
            elif vix_level > 25.0:  # Hardcoded moderate threshold
                panic_level = 1
                panic_signals.append('VIX_MODERATE')

        else:
            # Fallback to VIX-only detection
            if vix_level > self.vix_extreme_threshold:
                panic_level = 3
                panic_signals.append('VIX_EXTREME_ONLY')
            elif vix_level > self.vix_threshold:
                panic_level = 2
                panic_signals.append('VIX_HIGH_ONLY')
            elif vix_level > 25.0:
                panic_level = 1
                panic_signals.append('VIX_MODERATE_ONLY')

        # DIAGNOSTIC: Print final panic level
        print(f", PANIC_LEVEL={panic_level}, signals={panic_signals}")

        return panic_level

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """
        Calculate RSI (Relative Strength Index).

        Args:
            prices: Price series
            period: RSI period (default: 14)

        Returns:
            RSI value (0-100)
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral if insufficient data

        # Calculate price changes
        deltas = prices.diff()

        # Separate gains and losses
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)

        # Calculate average gains and losses
        avg_gain = gains.rolling(window=period, min_periods=period).mean().iloc[-1]
        avg_loss = losses.rolling(window=period, min_periods=period).mean().iloc[-1]

        # Calculate RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi)

    def calculate_trend_strength(self, features: pd.DataFrame, period: int) -> float:
        """
        Calculate trend consistency score (from V5).
        Returns score 0-1 (1 = very consistent trend).

        This filter reduces whipsaw trades by ensuring trend consistency.
        """
        if len(features) < period + 10:
            return 0.0

        # Handle column name variations
        close_col = 'Close' if 'Close' in features.columns else 'close'

        # Calculate momentum over two sub-periods
        # Short momentum (last 10 days)
        short_mom = (features[close_col].iloc[-1] / features[close_col].iloc[-11] - 1)

        # Long momentum (last period days)
        long_mom = (features[close_col].iloc[-1] / features[close_col].iloc[-(period+1)] - 1)

        # Consistent if both same sign and similar magnitude
        if (short_mom * long_mom) > 0:  # Same sign
            # Calculate consistency score
            if abs(short_mom) < 1e-6 or abs(long_mom) < 1e-6:
                return 0.0
            ratio = min(abs(short_mom), abs(long_mom)) / max(abs(short_mom), abs(long_mom))
            return ratio
        else:
            return 0.0  # Different signs = inconsistent

    def calculate_volatility_scalar(self, context: Context) -> float:
        """
        Scale positions based on realized volatility (from V3).
        High volatility → smaller positions.

        Returns:
            Scalar between 0 and 1 to multiply weights by
        """
        # Use SPY as market proxy for volatility
        spy_features = context.asset_features.get('SPY')
        if spy_features is None or len(spy_features) < self.vol_window + 1:
            return 1.0  # No scaling if insufficient data

        # Handle both 'Close' and 'close' column names
        close_col = 'Close' if 'Close' in spy_features.columns else 'close'

        # Calculate realized volatility
        prices = spy_features[close_col].tail(self.vol_window + 1)
        returns = prices.pct_change().dropna()

        if len(returns) < self.vol_window:
            return 1.0

        # Daily volatility
        daily_vol = returns.std()

        # Scale inversely: higher vol → lower scalar
        if daily_vol > 0:
            vol_scalar = min(1.0, self.max_volatility / daily_vol)
        else:
            vol_scalar = 1.0

        return vol_scalar

    def check_circuit_breaker(self, current_nav: float) -> bool:
        """
        Check if drawdown threshold breached (from V3).
        Returns True if should exit to cash.

        FIX: Reset circuit breaker when drawdown improves, not just at new highs.

        Args:
            current_nav: Current portfolio NAV

        Returns:
            True if circuit breaker should activate, False otherwise
        """
        # Convert to float if it's a Decimal
        current_nav = float(current_nav)

        # Update peak NAV if we're at new highs
        if current_nav > self.max_nav:
            self.max_nav = current_nav
            self.circuit_breaker_active = False  # Reset if making new highs

        # Calculate current drawdown
        if self.max_nav > 0:
            drawdown = (current_nav - self.max_nav) / self.max_nav
        else:
            drawdown = 0.0

        # Activate breaker if threshold crossed
        if drawdown < self.circuit_breaker_threshold:
            self.circuit_breaker_active = True
            return True

        # FIX: Reset breaker if drawdown improves to half the threshold
        # E.g., if threshold is -8%, reset when drawdown improves to -4%
        reset_threshold = self.circuit_breaker_threshold / 2.0
        if self.circuit_breaker_active and drawdown > reset_threshold:
            self.circuit_breaker_active = False
            print(f"  → Circuit breaker RESET (drawdown improved to {drawdown*100:.1f}%)")
            return False

        return self.circuit_breaker_active

    def calculate_sector_correlation(self, context: Context) -> float:
        """
        Calculate average pairwise correlation among growth assets (from V5).
        Used to adjust position sizing based on diversification.

        Returns:
            Average correlation (0-1)
        """
        sectors = [s for s in self.growth_assets if s in context.asset_features]
        if len(sectors) < 2:
            return 0.0

        # Build returns matrix
        returns_data = {}
        for symbol in sectors:
            features = context.asset_features[symbol]
            close_col = 'Close' if 'Close' in features.columns else 'close'

            if len(features) < self.correlation_lookback + 1:
                continue

            # Calculate returns for correlation period
            prices = features[close_col].tail(self.correlation_lookback + 1)
            returns = prices.pct_change().dropna()

            if len(returns) >= self.correlation_lookback - 1:
                returns_data[symbol] = returns.values

        if len(returns_data) < 2:
            return 0.0

        # Create DataFrame and calculate correlation
        try:
            # Align all returns series to same length
            min_len = min(len(v) for v in returns_data.values())
            aligned_data = {k: v[-min_len:] for k, v in returns_data.items()}
            returns_df = pd.DataFrame(aligned_data)

            if len(returns_df) < 10:  # Need minimum data
                return 0.0

            corr_matrix = returns_df.corr()

            # Get average of upper triangle
            upper_triangle = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)]
            avg_corr = np.nanmean(upper_triangle)

            return avg_corr if not np.isnan(avg_corr) else 0.0
        except:
            return 0.0

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights based on panic level and quality filters.

        Combines panic detection with risk management from Exp 012 models.

        Returns:
            ModelOutput with target weights
        """
        # REGIME CHECK: Temporarily disabled for Phase 1 testing
        # TODO: Re-enable after validating model logic
        # if context.regime.equity_regime != 'bear':
        #     return ModelOutput(
        #         model_name=self.model_id,
        #         timestamp=context.timestamp,
        #         weights={}
        #     )

        # Calculate panic level FIRST to decide if circuit breaker should apply
        panic_level = self.calculate_panic_level(context)

        # FIX: Disable circuit breaker during panic periods (we WANT volatility then)
        # Only check breaker when NOT in panic mode
        if panic_level == 0:
            current_nav = float(getattr(context, 'model_budget_value', 100000.0))
            drawdown_pct = ((current_nav - self.max_nav) / self.max_nav * 100) if self.max_nav > 0 else 0
            if self.check_circuit_breaker(current_nav):
                # Circuit breaker activated - exit to 100% cash
                print(f"  → CIRCUIT BREAKER ACTIVE (NAV=${current_nav:.2f}, max_nav=${self.max_nav:.2f}, DD={drawdown_pct:.1f}%)")
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights={self.cash_asset: 1.0}
                )

        # Check if it's time to rebalance
        if self.last_rebalance is not None:
            days_since_rebalance = (context.timestamp - self.last_rebalance).days
            if days_since_rebalance < self.rebalance_days:
                # Not time to rebalance yet - hold current positions
                # (No print here to avoid clutter)
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=context.current_exposures,
                    hold_current=True
                )

        self.last_rebalance = context.timestamp

        # Panic level already calculated above for circuit breaker check
        # (prints diagnostic info internally)

        # Initialize weights
        weights = {}

        # Panic level logic
        if panic_level == 3:
            # EXTREME PANIC: Buy growth aggressively with quality filters
            print(f"  → EXTREME PANIC (Level 3) - checking growth assets")
            qualified_assets = []

            for asset in self.growth_assets:
                if asset not in context.asset_features:
                    continue

                features = context.asset_features[asset]

                # Calculate trend strength (from V5)
                trend_strength = self.calculate_trend_strength(features, self.slow_momentum_period)

                # In extreme panic, relax trend strength requirement
                if trend_strength >= self.min_trend_strength:
                    # Calculate fast momentum for timing
                    close_col = 'Close' if 'Close' in features.columns else 'close'
                    if len(features) > self.fast_momentum_period:
                        fast_momentum = (features[close_col].iloc[-1] /
                                       features[close_col].iloc[-(self.fast_momentum_period+1)] - 1)
                        qualified_assets.append((asset, fast_momentum, trend_strength))
                        print(f"     ✓ {asset}: trend_strength={trend_strength:.3f}, fast_mom={fast_momentum:.3f}")
                else:
                    print(f"     ✗ {asset}: trend_strength={trend_strength:.3f} < {self.min_trend_strength:.3f}")

            if qualified_assets:
                # Sort by momentum (best bounce candidates first)
                qualified_assets.sort(key=lambda x: x[1], reverse=True)

                # Equal weight qualified growth assets
                base_weight = 1.0 / len(qualified_assets)
                for asset, _, _ in qualified_assets:
                    weights[asset] = base_weight

                # FIX: NO volatility scaling during extreme panic - we WANT to buy high vol
                # During extreme panic, high volatility is the opportunity, not the risk
                print(f"     No vol scaling during extreme panic (buying the chaos)")
                # weights stay at full size (1.0x)
            else:
                # No qualified assets even in extreme panic - stay in cash
                print(f"     No qualified assets - staying in cash")
                weights[self.cash_asset] = 1.0

        elif panic_level == 2:
            # HIGH PANIC: Buy mix of growth and safe havens with quality filters
            qualified_growth = []
            qualified_safe = []

            # Check growth assets
            for asset in self.growth_assets:
                if asset not in context.asset_features:
                    continue
                features = context.asset_features[asset]
                trend_strength = self.calculate_trend_strength(features, self.slow_momentum_period)
                if trend_strength >= self.min_trend_strength:
                    close_col = 'Close' if 'Close' in features.columns else 'close'
                    if len(features) > self.fast_momentum_period:
                        fast_momentum = (features[close_col].iloc[-1] /
                                       features[close_col].iloc[-(self.fast_momentum_period+1)] - 1)
                        qualified_growth.append((asset, fast_momentum))

            # Check safe havens
            for asset in self.safe_assets:
                if asset not in context.asset_features:
                    continue
                features = context.asset_features[asset]
                close_col = 'Close' if 'Close' in features.columns else 'close'
                if len(features) > self.slow_momentum_period:
                    momentum = (features[close_col].iloc[-1] /
                              features[close_col].iloc[-(self.slow_momentum_period+1)] - 1)
                    if momentum > 0:  # Safe havens should be positive in panic
                        qualified_safe.append((asset, momentum))

            # Allocate 60% to growth, 40% to safe havens
            if qualified_growth:
                growth_weight = 0.6 / len(qualified_growth)
                for asset, _ in qualified_growth:
                    weights[asset] = growth_weight

            if qualified_safe:
                safe_weight = 0.4 / len(qualified_safe)
                for asset, _ in qualified_safe:
                    weights[asset] = safe_weight

            if not weights:
                weights[self.cash_asset] = 1.0
            else:
                # FIX: Reduce volatility scaling during high panic (0.7 base size only)
                # Use moderate vol scalar to prevent extreme positions but still buy opportunity
                vol_scalar = self.calculate_volatility_scalar(context)
                vol_scalar = max(vol_scalar, 0.5)  # Floor at 0.5 (don't reduce below 50%)
                print(f"     Vol scalar: {vol_scalar:.3f} (floored at 0.5)")
                weights = {k: v * vol_scalar * 0.7 for k, v in weights.items()}

        elif panic_level == 1:
            # MODERATE PANIC: Buy best safe havens (FIX: no momentum requirement)
            print(f"  → MODERATE PANIC (Level 1) - buying safe havens")
            best_safe_havens = []

            for asset in self.safe_assets:
                if asset not in context.asset_features:
                    continue
                features = context.asset_features[asset]
                close_col = 'Close' if 'Close' in features.columns else 'close'

                if len(features) > self.slow_momentum_period:
                    momentum = (features[close_col].iloc[-1] /
                              features[close_col].iloc[-(self.slow_momentum_period+1)] - 1)
                    best_safe_havens.append((asset, momentum))
                    print(f"     {asset}: momentum={momentum:.3f}")

            if best_safe_havens:
                # Sort by momentum and take top 2
                best_safe_havens.sort(key=lambda x: x[1], reverse=True)
                top_safe = best_safe_havens[:2]

                # 50% in safe havens, 50% cash
                safe_weight = 0.5 / len(top_safe)
                for asset, _ in top_safe:
                    weights[asset] = safe_weight
                weights[self.cash_asset] = 0.5
                print(f"     Allocated 50% to safe havens, 50% cash")
            else:
                weights[self.cash_asset] = 1.0
                print(f"     No safe havens available - staying in cash")

        else:
            # NO PANIC: Stay in cash
            weights[self.cash_asset] = 1.0

        # Apply correlation adjustment if we have growth positions (from V5)
        total_growth_weight = sum(weights.get(asset, 0) for asset in self.growth_assets)
        if total_growth_weight > 0:
            avg_corr = self.calculate_sector_correlation(context)
            if avg_corr > self.min_correlation:
                # High correlation - reduce positions
                excess_corr = avg_corr - self.min_correlation
                max_reduction = 0.4  # Maximum 40% reduction
                corr_scalar = 1.0 - min(excess_corr, max_reduction)

                for asset in self.growth_assets:
                    if asset in weights:
                        weights[asset] *= corr_scalar

        # Ensure weights sum to 1 (put remainder in cash)
        total_weight = sum(weights.values())
        if total_weight < 1.0:
            weights[self.cash_asset] = weights.get(self.cash_asset, 0) + (1.0 - total_weight)

        # DIAGNOSTIC: Print final weights
        if weights:
            weights_str = ", ".join([f"{k}={v:.3f}" for k, v in weights.items() if v > 0.001])
            print(f"  → FINAL WEIGHTS: {weights_str}")
        else:
            print(f"  → FINAL WEIGHTS: Empty (will hold current)")

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights
        )

    def __repr__(self):
        return (
            f"BearDipBuyer_v1(model_id='{self.model_id}', "
            f"vix_threshold={self.vix_threshold}, "
            f"rsi_oversold={self.rsi_oversold}, "
            f"circuit_breaker={self.circuit_breaker_threshold})"
        )