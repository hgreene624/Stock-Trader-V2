class SectorRotationConsistent_v2(BaseModel):
    """
    Consistent yearly alpha through adaptive parameter selection.

    V2 improvements:
    - Faster regime recovery detection (uses 50D MA in addition to 200D)
    - Less defensive in bear markets (0.75x instead of 0.5x)
    - Added "recovery" regime for post-crash rebounds
    """

    def __init__(
        self,
        model_id: str = "SectorRotationConsistent_v2",
        sectors: list[str] = None,
        defensive_asset: str = "TLT",

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
        Calculate momentum scores for each sector with decay factor.
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

            # Medium-term momentum (last 60 days)
            medium_momentum = returns.iloc[-60:].mean() * 252

            # Long-term momentum (full period)
            long_momentum = returns.iloc[-self.momentum_period:].mean() * 252

            # Weighted score with decay
            score = (
                recent_momentum * 1.0 +
                medium_momentum * self.momentum_decay +
                long_momentum * (self.momentum_decay ** 2)
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
        """
        market_regime = self.detect_market_regime(context)

        # Regime-specific parameter sets optimized for consistency
        # V2: Added 'recovery' regime and increased bear leverage
        regime_params = {
            'steady_bull': {
                'min_hold_days': 21,      # Hold longer in steady trends
                'leverage': 1.0,          # Lower leverage - don't over-trade
                'top_n': 2,               # Concentrate in top 2
                'stop_loss_mult': 2.5,    # Wider stops
                'description': 'Patient holding in stable uptrends'
            },
            'volatile_bull': {
                'min_hold_days': 7,       # Can rotate faster
                'leverage': 1.25,         # Use available leverage
                'top_n': 3,               # Diversify a bit more
                'stop_loss_mult': 2.0,    # Normal stops
                'description': 'Active rotation in volatile uptrends'
            },
            'recovery': {
                'min_hold_days': 5,       # Fast rotation during rebounds
                'leverage': 1.25,         # Full leverage - ride the rebound!
                'top_n': 3,               # Diversify across recovering sectors
                'stop_loss_mult': 1.8,    # Medium-tight stops
                'description': 'Aggressive during post-crash rebounds (like Apr 2020)'
            },
            'bear': {
                'min_hold_days': 5,       # Quick to exit
                'leverage': 0.75,         # V2: Increased from 0.5 - don't miss rebounds
                'top_n': 2,               # Only best ideas
                'stop_loss_mult': 1.5,    # Tight stops
                'description': 'Defensive but not too cautious'
            },
            'concentrated': {
                'min_hold_days': 14,      # Medium hold
                'leverage': 1.25,         # Full leverage on concentrated bet
                'top_n': 1,               # Ride the winner
                'stop_loss_mult': 2.0,    # Normal stops
                'max_weight': 0.6,        # Allow 60% concentration
                'description': 'Ride dominant sector (like 2024 tech)'
            }
        }

        params = regime_params.get(market_regime, regime_params['volatile_bull'])

        # Never exceed max leverage for small accounts
        params['leverage'] = min(params['leverage'], 1.25)

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
        Generate portfolio weights using adaptive parameters and drawdown protection.
        """
        weights = {}
        current_date = context.timestamp

        # Get adaptive parameters (now with regime-specific settings)
        params = self.get_adaptive_parameters(context)

        # Get drawdown protection factor
        protection_factor = self.calculate_drawdown_protection_factor(context)

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
            weights[self.defensive_asset] = params['leverage'] * protection_factor
        else:
            # Select top N sectors (regime-specific)
            selected_sectors = []
            for sector, score in sorted_sectors[:top_n]:
                if score >= self.min_momentum:
                    selected_sectors.append(sector)

            if not selected_sectors:
                weights[self.defensive_asset] = params['leverage'] * protection_factor
            else:
                # Check rotation conditions
                should_rebalance = False

                # Check minimum hold period
                if self.last_rotation_date is not None:
                    days_held = (current_date - self.last_rotation_date).days
                    if days_held < params['min_hold_days']:
                        # Keep current positions
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
                    # Rebalance portfolio with protection factor
                    base_weight = (params['leverage'] * protection_factor) / len(selected_sectors)
                    for sector in selected_sectors:
                        weights[sector] = base_weight

                    # Apply concentration boost if warranted
                    weights = self.apply_concentration_boost(weights, scores)

                    # Update tracking
                    self.current_positions = weights.copy()
                    self.last_rotation_date = current_date
                else:
                    # Keep current positions but apply protection factor
                    weights = {}
                    for sector, weight in self.current_positions.items():
                        weights[sector] = weight * protection_factor

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
