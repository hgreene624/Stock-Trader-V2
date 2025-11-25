"""
BearDefensiveRotation_v3

Bear market specialist with enhanced risk management features.

Version 3 Improvements (Risk Management):
- Volatility-based position sizing: Scales exposure inversely to market volatility
- Drawdown circuit breaker: Exits to cash if model drawdown exceeds threshold
- Preserves all v2 functionality when risk parameters are permissive

Strategy:
- Designed specifically for bear markets (equity_regime == 'bear')
- Rotates among defensive assets: XLU (utilities), XLP (staples), TLT (bonds), GLD (gold), UUP (dollar), SHY (cash)
- Ranks assets by momentum and holds the top N performers
- Can hold assets with negative momentum if they're "least bad" (min_momentum default -0.05)
- Goes to 100% SHY when all assets are below cash_threshold (-0.10)
- NEW in v3: Scales positions based on market volatility
- NEW in v3: Circuit breaker exits to cash if drawdown exceeds threshold
- Rebalances every N days (default 10)

Risk Management Features:
1. Volatility Scaling: When realized vol > target vol, positions are scaled down
2. Drawdown Protection: Hard exit to cash if portfolio drawdown exceeds threshold
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class BearDefensiveRotation_v3(BaseModel):
    """
    Bear market defensive rotation v3 - v2 plus volatility scaling and drawdown protection.

    Only generates weights when equity_regime == 'bear'.
    V3 adds risk management: volatility-based sizing and drawdown circuit breaker.
    """

    def __init__(
        self,
        model_id: str = "BearDefensiveRotation_v3",
        defensive_assets: list[str] = None,
        momentum_period: int = 20,
        top_n: int = 2,
        min_momentum: float = -0.05,
        cash_threshold: float = -0.10,
        rebalance_days: int = 10,
        target_volatility: float = 0.15,  # NEW in v3: 15% annualized vol target
        drawdown_threshold: float = -0.10,  # NEW in v3: -10% max drawdown before exit
    ):
        """
        Initialize Bear Defensive Rotation Model v3.

        Args:
            model_id: Unique model identifier
            defensive_assets: List of defensive ETFs (default: XLU, XLP, TLT, GLD, UUP, SHY)
            momentum_period: Lookback period for momentum (default: 20 days)
            top_n: Number of top assets to hold (default: 2)
            min_momentum: Minimum momentum threshold (default: -0.05, can be negative)
            cash_threshold: If ALL assets below this, go 100% SHY (default: -0.10)
            rebalance_days: Days between rebalances (default: 10)
            target_volatility: Target annualized volatility for position sizing (default: 0.15)
            drawdown_threshold: Maximum drawdown before circuit breaker activates (default: -0.10)
        """
        # V2 parameters
        self.defensive_assets = defensive_assets or [
            'XLU',   # Utilities - defensive sector
            'XLP',   # Consumer Staples - defensive sector
            'TLT',   # Long-term Treasury bonds
            'GLD',   # Gold
            'UUP',   # US Dollar Index
            'SHY'    # Short-term Treasury (cash proxy)
        ]

        self.cash_asset = 'SHY'

        # Ensure SHY is in the list
        if self.cash_asset not in self.defensive_assets:
            self.defensive_assets.append(self.cash_asset)

        self.all_assets = self.defensive_assets + ['SPY']  # Add SPY for volatility calculation
        self.assets = self.all_assets  # Required for BacktestRunner to load data

        self.model_id = model_id
        self.momentum_period = momentum_period
        self.top_n = top_n
        self.min_momentum = min_momentum
        self.cash_threshold = cash_threshold
        self.rebalance_days = rebalance_days

        # V3: New risk management parameters
        self.target_volatility = target_volatility
        self.drawdown_threshold = drawdown_threshold

        # V3: Track for circuit breaker
        self.max_nav = 100000.0  # Initialize to starting NAV
        self.circuit_breaker_active = False

        super().__init__(
            name=model_id,
            version="3.0.0",  # V3
            universe=self.all_assets
        )

        # Track last rebalance date
        self.last_rebalance: Optional[pd.Timestamp] = None

    def calculate_volatility_scalar(self, context: Context) -> float:
        """
        Scale positions based on realized volatility vs baseline.
        High volatility → smaller positions

        Returns:
            Scalar between 0 and 1 to multiply weights by
        """
        # Use SPY as market proxy for volatility
        spy_features = context.asset_features.get('SPY')
        if spy_features is None or len(spy_features) < 21:
            return 1.0  # No scaling if insufficient data

        # Handle both 'Close' and 'close' column names
        close_col = 'Close' if 'Close' in spy_features.columns else 'close'

        # Calculate 20-day realized volatility
        prices = spy_features[close_col].tail(21)
        returns = prices.pct_change().dropna()

        if len(returns) < 20:
            return 1.0  # Not enough data

        # Calculate realized volatility (annualized)
        realized_vol = returns.std() * np.sqrt(252)

        # Scale inversely: higher vol → lower scalar
        # If realized_vol = 0.15 (target), scalar = 1.0
        # If realized_vol = 0.30 (2x target), scalar = 0.5
        # Cap at 1.0 to prevent leverage
        if realized_vol > 0:
            vol_scalar = min(1.0, self.target_volatility / realized_vol)
        else:
            vol_scalar = 1.0

        return vol_scalar

    def check_circuit_breaker(self, current_nav: float) -> bool:
        """
        Check if drawdown threshold breached.
        Returns True if should exit to cash.

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
            if self.circuit_breaker_active:
                print(f"  → Circuit breaker RESET (new high: ${current_nav:.2f})")
            self.circuit_breaker_active = False  # Reset if making new highs

        # Calculate current drawdown
        if self.max_nav > 0:
            drawdown = (current_nav - self.max_nav) / self.max_nav
        else:
            drawdown = 0.0

        # Activate breaker if threshold crossed
        if drawdown < self.drawdown_threshold:
            if not self.circuit_breaker_active:
                print(f"  → Circuit breaker TRIGGERED (NAV=${current_nav:.2f}, max=${self.max_nav:.2f}, DD={drawdown*100:.1f}%)")
            self.circuit_breaker_active = True
            return True

        return self.circuit_breaker_active  # Stay in cash once activated until new highs

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights - ONLY in bear markets.
        V3: Includes volatility scaling and drawdown circuit breaker.

        Returns:
            ModelOutput with target weights (empty if not bear regime)
        """
        # REGIME CHECK: Temporarily disabled for Phase 1 testing
        # TODO: Re-enable after validating model logic
        # if context.regime.equity_regime != 'bear':
        #     # Not a bear market - return empty weights (no positions)
        #     return ModelOutput(
        #         model_name=self.model_id,
        #         timestamp=context.timestamp,
        #         weights={}
        #     )

        # V3: Check circuit breaker FIRST (before any other logic)
        # Use model_budget_value if available, otherwise use default
        current_nav = getattr(context, 'model_budget_value', 100000.0)
        if self.check_circuit_breaker(current_nav):
            # Circuit breaker activated - exit to 100% cash
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
                # BUG: This was applying volatility scaling DAILY causing overtrading!
                # FIX: Just hold current positions, no daily adjustments
                print(f"  [V3] Holding (day {days_since_rebalance}/{self.rebalance_days})")
                return ModelOutput(
                    model_name=self.model_id,
                    timestamp=context.timestamp,
                    weights=context.current_exposures,
                    hold_current=True  # Actually hold without modifications
                )

        self.last_rebalance = context.timestamp
        print(f"  [V3] Rebalancing at {context.timestamp.date()}")

        # Calculate momentum for each defensive asset
        asset_momentum = {}

        for asset in self.defensive_assets:
            if asset not in context.asset_features:
                continue

            features = context.asset_features[asset]

            # Handle both 'Close' and 'close' column names
            close_col = 'Close' if 'Close' in features.columns else 'close'

            if len(features) < self.momentum_period + 1:
                continue

            # Get current and historical prices
            current_price = features[close_col].iloc[-1]
            past_price = features[close_col].iloc[-(self.momentum_period + 1)]

            if pd.isna(current_price) or pd.isna(past_price) or past_price == 0:
                continue

            # Calculate momentum
            momentum = (current_price - past_price) / past_price
            asset_momentum[asset] = momentum

        # Initialize weights
        weights = {}

        if len(asset_momentum) == 0:
            # No data available - go to cash (SHY)
            weights[self.cash_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # V2: Check if ALL assets are below cash threshold
        # This is the circuit breaker for extreme conditions like 2022
        max_momentum = max(asset_momentum.values())
        if max_momentum < self.cash_threshold:
            # Everything is crashing badly - go to pure cash
            weights[self.cash_asset] = 1.0
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Sort assets by momentum (descending - best first, even if negative)
        ranked_assets = sorted(asset_momentum.items(), key=lambda x: x[1], reverse=True)

        # Get top N assets
        top_assets = ranked_assets[:self.top_n]

        # Check if top assets meet minimum momentum threshold
        qualified_assets = [(asset, mom) for asset, mom in top_assets if mom >= self.min_momentum]

        if len(qualified_assets) > 0:
            # Equal weight across qualified assets
            # Note: SHY can be selected here if it has good momentum
            weight_per_asset = 1.0 / len(qualified_assets)
            for asset, _ in qualified_assets:
                weights[asset] = weight_per_asset
        else:
            # No assets meet minimum threshold - use cash (SHY)
            weights[self.cash_asset] = 1.0

        # V3: Apply volatility scaling to final weights
        vol_scalar = self.calculate_volatility_scalar(context)
        print(f"       Vol scalar: {vol_scalar:.3f}")
        scaled_weights = {k: v * vol_scalar for k, v in weights.items()}

        # If scaling reduced total exposure, put remainder in SHY
        total_exposure = sum(scaled_weights.values())
        if total_exposure < 1.0:
            scaled_weights[self.cash_asset] = scaled_weights.get(self.cash_asset, 0) + (1.0 - total_exposure)

        # Log final weights
        weights_str = ", ".join([f"{k}={v:.3f}" for k, v in scaled_weights.items() if v > 0.001])
        print(f"       Final weights: {weights_str}")

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=scaled_weights
        )

    def __repr__(self):
        return (
            f"BearDefensiveRotation_v3(model_id='{self.model_id}', "
            f"momentum_period={self.momentum_period}, top_n={self.top_n}, "
            f"min_momentum={self.min_momentum}, cash_threshold={self.cash_threshold}, "
            f"rebalance_days={self.rebalance_days}, "
            f"target_volatility={self.target_volatility}, "
            f"drawdown_threshold={self.drawdown_threshold})"
        )