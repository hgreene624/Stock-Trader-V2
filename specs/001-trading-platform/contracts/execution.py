"""
ExecutionInterface abstract base class.

Unified abstraction for broker interaction across backtest, paper, and live modes.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from decimal import Decimal
from dataclasses import dataclass
import pandas as pd


@dataclass
class Position:
    """Represents a single position in the portfolio."""

    symbol: str
    quantity: Decimal  # Shares/units held (can be negative for shorts)
    entry_price: Decimal  # Average entry price
    market_price: Decimal  # Current market price
    market_value: Decimal  # quantity × market_price
    unrealized_pnl: Decimal  # (market_price - entry_price) × quantity

    def __post_init__(self):
        """Validate position consistency."""
        # Market value should equal quantity × market_price
        expected_value = self.quantity * self.market_price
        assert abs(self.market_value - expected_value) < Decimal("0.01"), \
            f"market_value {self.market_value} != quantity {self.quantity} × price {self.market_price}"

        # Unrealized PnL should equal (market_price - entry_price) × quantity
        expected_pnl = (self.market_price - self.entry_price) * self.quantity
        assert abs(self.unrealized_pnl - expected_pnl) < Decimal("0.01"), \
            f"unrealized_pnl {self.unrealized_pnl} != price delta × quantity"


@dataclass
class OrderResult:
    """Result of order submission."""

    success: bool
    order_id: str  # Internal or broker order ID
    filled_quantity: Decimal
    filled_price: Decimal
    fees: Decimal
    slippage: Decimal
    error_message: str | None = None


class ExecutionInterface(ABC):
    """
    Abstract interface for broker adapters.

    Implementations:
    - BacktestAdapter: Offline bar-based simulation with OHLC
    - AlpacaAdapter: Alpaca API (paper + live for equities)
    - BinanceAdapter: Binance API (spot crypto)
    - KrakenAdapter: Kraken API (spot crypto)

    All adapters must implement this interface to ensure seamless
    progression from backtest → paper → live.
    """

    @abstractmethod
    def submit_target_weights(
        self,
        target_weights: Dict[str, float],
        timestamp: pd.Timestamp
    ) -> List[OrderResult]:
        """
        Submit target portfolio weights and execute necessary trades.

        The adapter:
        1. Computes position deltas (target - current)
        2. Generates orders to achieve target weights
        3. Submits orders to broker (or simulates in backtest)
        4. Returns results with fills, fees, slippage

        Args:
            target_weights: NAV-relative target weights per symbol
                Example: {"SPY": 0.30, "QQQ": 0.15, "BTC-USD": 0.10}
                - Values in range [0.0, 1.0] (long only for v1)
                - Sum of values ≤ max_leverage (e.g., 1.2)
            timestamp: Execution timestamp (UTC)

        Returns:
            List of OrderResult objects (one per trade executed)

        Raises:
            ValueError: If target_weights violate constraints
            ConnectionError: If broker API unavailable (paper/live only)

        Example:
            results = adapter.submit_target_weights(
                {"SPY": 0.30, "QQQ": 0.15},
                pd.Timestamp('2025-01-15 20:00', tz='UTC')
            )
            for result in results:
                if result.success:
                    print(f"Filled {result.filled_quantity} @ ${result.filled_price}")
        """
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, Position]:
        """
        Get current portfolio positions.

        Returns:
            Dictionary mapping symbol to Position object

        Example:
            positions = adapter.get_positions()
            # {"SPY": Position(symbol="SPY", quantity=100, ...), ...}
        """
        pass

    @abstractmethod
    def get_cash(self) -> Decimal:
        """
        Get available cash balance.

        Returns:
            Cash balance as Decimal

        Example:
            cash = adapter.get_cash()  # Decimal("50000.00")
        """
        pass

    @abstractmethod
    def get_nav(self) -> Decimal:
        """
        Get net asset value (cash + positions market value).

        Returns:
            NAV as Decimal

        Example:
            nav = adapter.get_nav()  # Decimal("100000.00")
        """
        pass

    @abstractmethod
    def get_broker_metadata(self) -> Dict[str, any]:
        """
        Get broker-specific metadata (account info, constraints, etc.).

        Returns:
            Dictionary with broker-specific information

        Example (Alpaca):
            {
                "account_id": "abc123",
                "buying_power": Decimal("50000.00"),
                "pattern_day_trader": False,
                "trading_blocked": False
            }

        Example (Backtest):
            {
                "mode": "backtest",
                "current_bar": 1523,
                "total_bars": 8760,
                "slippage_bps": 5,
                "fee_bps": 1
            }
        """
        pass


class BacktestAdapter(ExecutionInterface):
    """
    Backtest execution adapter using bar-based OHLC simulation.

    Execution logic:
    - Market orders: Fill at next bar's open price
    - Slippage: Configurable bps (default 5 bps = 0.05%)
    - Fees: Configurable bps (default 1 bps = 0.01%)
    - Validation: Ensure order within bar's OHLC range

    No external dependencies or API calls.
    """

    def __init__(
        self,
        initial_cash: Decimal,
        slippage_bps: float = 5.0,
        fee_bps: float = 1.0
    ):
        """
        Initialize backtest adapter.

        Args:
            initial_cash: Starting capital
            slippage_bps: Slippage in basis points (default 5 = 0.05%)
            fee_bps: Fees in basis points (default 1 = 0.01%)
        """
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
        self.bar_count = 0

    def submit_target_weights(
        self,
        target_weights: Dict[str, float],
        timestamp: pd.Timestamp
    ) -> List[OrderResult]:
        """
        Simulate order execution at next bar's open.

        Implementation stub - actual logic in engines/execution/backtest.py
        """
        # Stub implementation
        return []

    def get_positions(self) -> Dict[str, Position]:
        """Get current positions."""
        return self.positions

    def get_cash(self) -> Decimal:
        """Get cash balance."""
        return self.cash

    def get_nav(self) -> Decimal:
        """Calculate NAV."""
        positions_value = sum(
            pos.market_value for pos in self.positions.values()
        )
        return self.cash + positions_value

    def get_broker_metadata(self) -> Dict[str, any]:
        """Get backtest metadata."""
        return {
            "mode": "backtest",
            "current_bar": self.bar_count,
            "slippage_bps": self.slippage_bps,
            "fee_bps": self.fee_bps,
            "num_positions": len(self.positions)
        }


# Example usage
if __name__ == "__main__":
    from decimal import Decimal
    import pandas as pd

    # Create backtest adapter
    adapter = BacktestAdapter(
        initial_cash=Decimal("100000.00"),
        slippage_bps=5.0,
        fee_bps=1.0
    )

    print(f"Initial cash: ${adapter.get_cash()}")
    print(f"Initial NAV: ${adapter.get_nav()}")
    print(f"Metadata: {adapter.get_broker_metadata()}")

    # In real implementation, submit_target_weights would execute trades
    # and update positions/cash accordingly
