"""
CashSecuredPutModel_v1

Income generation strategy selling cash-secured puts on SPY.

Strategy:
- Only trade in bull/neutral equity regimes
- Sell puts with target delta ~0.30 (30% ITM probability)
- Target 30-45 DTE (days to expiration)
- Exit at 50% profit or 21 DTE (time decay accelerates)
- Max 2 contracts per model budget
- Hold cash collateral (100% cash-secured)

Why this generates alpha:
1. Collect premium from option sellers' demand
2. Time decay (theta) works in our favor
3. Regime filter avoids selling puts before crashes
4. Mean-reversion tendency of SPY provides safety

Expected returns:
- Premium: ~2-3% per contract (~1-1.5% on capital)
- Frequency: ~8 cycles per year
- Target: 10-15% annual income
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from decimal import Decimal
import sys
import os
sys.path.append('..')
from models.base import BaseModel, Context, ModelOutput


class CashSecuredPutModel_v1(BaseModel):
    """
    Cash-secured put selling strategy on SPY for income generation.
    """

    def __init__(
        self,
        model_id: str = "CashSecuredPutModel_v1",
        underlying: str = "SPY",
        target_delta: float = 0.30,
        min_dte: int = 30,
        max_dte: int = 45,
        profit_target_pct: float = 0.50,
        time_exit_dte: int = 21,
        max_contracts: int = 2,
        allowed_regimes: list = None
    ):
        """
        Initialize CashSecuredPutModel_v1.

        Args:
            model_id: Unique model identifier
            underlying: Underlying symbol to sell puts on (default: SPY)
            target_delta: Target delta for sold puts (default: 0.30)
            min_dte: Minimum days to expiration (default: 30)
            max_dte: Maximum days to expiration (default: 45)
            profit_target_pct: Exit at this % of max profit (default: 0.50 = 50%)
            time_exit_dte: Exit when DTE falls below this (default: 21)
            max_contracts: Maximum contracts to sell (default: 2)
            allowed_regimes: Equity regimes to trade in (default: bull, neutral)
        """
        self.underlying = underlying
        self.target_delta = target_delta
        self.min_dte = min_dte
        self.max_dte = max_dte
        self.profit_target_pct = profit_target_pct
        self.time_exit_dte = time_exit_dte
        self.max_contracts = max_contracts
        self.allowed_regimes = allowed_regimes or ['bull', 'neutral']
        self.model_id = model_id

        # For backtesting, we'll track simulated positions
        self.open_positions = []  # List of {symbol, entry_price, entry_date, strike, expiration}

        super().__init__(
            name=model_id,
            version="1.0.0",
            universe=[underlying]  # We trade the underlying and options on it
        )

    def generate_target_weights(self, context: Context) -> ModelOutput:
        """
        Generate target weights for cash-secured put strategy.

        Strategy:
        1. Check regime - only trade in allowed regimes
        2. Check existing positions - manage exits first
        3. If no position and regime OK, find new put to sell
        4. Return weights: underlying exposure + cash reserve

        Returns:
            ModelOutput with target weights
        """
        weights = {self.underlying: 0.0}

        # Get regime
        equity_regime = context.regime.equity_regime

        # Check if regime allows trading
        if equity_regime not in self.allowed_regimes:
            # Bear market - don't sell puts, hold cash
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights  # All cash (0.0 weight in underlying)
            )

        # Get underlying data
        if self.underlying not in context.asset_features:
            # No data available
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        features = context.asset_features[self.underlying]
        if len(features) == 0:
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # Get current price
        close_col = 'Close' if 'Close' in features.columns else 'close'
        current_price = features[close_col].iloc[-1]

        if pd.isna(current_price):
            return ModelOutput(
                model_name=self.model_id,
                timestamp=context.timestamp,
                weights=weights
            )

        # SIMPLIFIED BACKTEST SIMULATION:
        # In a real backtest, we'd track options positions with Greeks, DTE, etc.
        # For now, we'll use a proxy strategy:
        # - Calculate how much capital we'd allocate to cash-secured puts
        # - Estimate expected return
        # - Model as if we're holding some SPY exposure

        # Check if we should be "in position" (simplified monthly rebalancing)
        should_enter = self._should_enter_position(context, features, equity_regime)

        if should_enter:
            # Simulate being in a CSP position
            # A cash-secured put is like being 0% invested but earning premium
            # We'll model this as holding small SPY position to represent the strategy
            # The actual options strategy would be implemented in live trading

            # For backtesting, represent CSP exposure as minimal SPY weight
            # This is a placeholder - proper options backtesting would track P&L from premium
            weights[self.underlying] = 0.0  # Cash-secured = holding cash

            # In a real implementation, we'd track:
            # - Premium collected
            # - Strike price
            # - DTE
            # - Current option value
            # - Unrealized P&L
        else:
            # No position
            weights[self.underlying] = 0.0

        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=weights,
            confidence={self.underlying: 0.7} if should_enter else None
        )

    def _should_enter_position(
        self,
        context: Context,
        features: pd.DataFrame,
        equity_regime: str
    ) -> bool:
        """
        Determine if we should enter a new CSP position.

        Simplified logic for backtesting:
        - Only in bull/neutral regimes
        - SPY above 200-day MA (uptrend)
        - Not oversold (RSI > 30)

        Args:
            context: Market context
            features: Underlying asset features
            equity_regime: Current equity regime

        Returns:
            True if should enter position
        """
        # Check regime
        if equity_regime not in self.allowed_regimes:
            return False

        # Check if we have enough history
        if len(features) < 200:
            return False

        # Get indicators
        close_col = 'Close' if 'Close' in features.columns else 'close'
        current_price = features[close_col].iloc[-1]

        # Calculate 200-day MA
        ma_200 = features[close_col].tail(200).mean()

        # Simple trend filter: only sell puts if SPY is in uptrend
        if current_price < ma_200:
            return False

        # Calculate RSI if available
        if 'rsi' in features.columns or 'RSI' in features.columns:
            rsi_col = 'RSI' if 'RSI' in features.columns else 'rsi'
            rsi = features[rsi_col].iloc[-1]

            # Don't sell puts if oversold (potential further drop)
            if not pd.isna(rsi) and rsi < 30:
                return False

        # All checks passed - we can sell puts
        return True

    def __repr__(self):
        return (
            f"CashSecuredPutModel_v1(model_id='{self.model_id}', "
            f"underlying={self.underlying}, delta={self.target_delta}, "
            f"dte={self.min_dte}-{self.max_dte})"
        )


# Example standalone test
if __name__ == "__main__":
    # NOTE: This is a simplified demonstration
    # Real options backtesting requires options chain data and proper P&L tracking

    print("CashSecuredPutModel_v1 - Income Generation Strategy")
    print("=" * 60)

    model = CashSecuredPutModel_v1(
        underlying="SPY",
        target_delta=0.30,
        min_dte=30,
        max_dte=45
    )

    print(f"\nModel: {model}")
    print(f"Strategy: Sell cash-secured puts on {model.underlying}")
    print(f"Target delta: {model.target_delta}")
    print(f"DTE range: {model.min_dte}-{model.max_dte} days")
    print(f"Allowed regimes: {model.allowed_regimes}")
    print(f"Max contracts: {model.max_contracts}")

    print("\n" + "=" * 60)
    print("NOTE: Full options backtesting requires:")
    print("  1. Historical options chain data")
    print("  2. Greeks calculation (delta, theta, vega, gamma)")
    print("  3. IV surface modeling")
    print("  4. Assignment simulation")
    print("  5. Margin requirements tracking")
    print("\nCurrent implementation provides simplified proxy for research.")
    print("=" * 60)
