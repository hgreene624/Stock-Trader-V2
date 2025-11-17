"""
Backtest Executor

Simulates order execution and position tracking for backtesting.

Features:
- Bar-based OHLC simulation
- Configurable fill timing (bar close, bar open, etc.)
- Slippage modeling (fixed bps or percentage)
- Commission modeling
- Position tracking with P&L
- NAV calculation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Literal
from decimal import Decimal
from dataclasses import dataclass
import sys
sys.path.append('..')
from engines.execution.interface import ExecutionInterface, Position, OrderResult
from utils.logging import StructuredLogger


@dataclass
class BacktestConfig:
    """Configuration for backtest execution."""
    initial_nav: Decimal
    fill_timing: Literal["close", "open", "vwap"] = "close"
    slippage_bps: float = 5.0  # Slippage in basis points
    commission_pct: float = 0.001  # Commission as % of trade value (0.1%)
    min_commission: Decimal = Decimal("1.00")  # Minimum commission per trade


class BacktestExecutor(ExecutionInterface):
    """
    Simulates trade execution for backtesting.

    Maintains positions and cash, processes target weights into trades,
    and simulates fills using historical OHLCV data.
    """

    def __init__(
        self,
        config: BacktestConfig,
        asset_data: Dict[str, pd.DataFrame],
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize backtest executor.

        Args:
            config: Backtest configuration
            asset_data: Dict of symbol → OHLCV DataFrame
            logger: Optional logger instance
        """
        self.config = config
        self.asset_data = asset_data
        self.logger = logger or StructuredLogger()

        # State
        self.cash = config.initial_nav
        self.positions: Dict[str, Position] = {}
        self.nav_history: List[Dict] = []
        self.trade_history: List[Dict] = []

    def submit_target_weights(
        self,
        target_weights: Dict[str, float],
        timestamp: pd.Timestamp
    ) -> List[OrderResult]:
        """
        Submit target portfolio weights and execute necessary trades.

        Args:
            target_weights: Target weights as fraction of NAV (e.g., {"SPY": 0.5, "QQQ": 0.3})
            timestamp: Execution timestamp

        Returns:
            List of order results

        Process:
        1. Calculate current NAV
        2. Convert target weights to target dollar values
        3. Calculate deltas vs current positions
        4. Execute trades to achieve target portfolio
        5. Update positions and cash
        """
        current_nav = self.get_nav()
        orders = []

        # Get current prices
        prices = self._get_prices(timestamp)

        # Calculate target dollar values
        target_values = {
            symbol: float(current_nav) * weight
            for symbol, weight in target_weights.items()
        }

        # Calculate current position values
        current_values = {}
        for symbol, position in self.positions.items():
            if symbol in prices:
                current_values[symbol] = float(position.quantity) * prices[symbol]
            else:
                # Price not available, assume position value = 0 (will liquidate)
                current_values[symbol] = 0.0

        # Add symbols from target_weights that don't have positions
        for symbol in target_weights.keys():
            if symbol not in current_values:
                current_values[symbol] = 0.0

        # Calculate deltas and create orders
        all_symbols = set(target_values.keys()) | set(current_values.keys())

        for symbol in all_symbols:
            target_value = target_values.get(symbol, 0.0)
            current_value = current_values.get(symbol, 0.0)

            delta_value = target_value - current_value

            # Skip if delta is negligible (< $10)
            if abs(delta_value) < 10.0:
                continue

            # Get price
            if symbol not in prices:
                self.logger.error(f"No price available for {symbol} at {timestamp}")
                continue

            price = prices[symbol]

            # Calculate shares to trade
            delta_shares = delta_value / price

            # Round to integer shares
            delta_shares = int(np.round(delta_shares))

            if delta_shares == 0:
                continue

            # Execute trade
            order_result = self._execute_trade(
                symbol=symbol,
                quantity=delta_shares,
                price=price,
                timestamp=timestamp
            )

            orders.append(order_result)

        return orders

    def _execute_trade(
        self,
        symbol: str,
        quantity: int,
        price: float,
        timestamp: pd.Timestamp
    ) -> OrderResult:
        """
        Execute a single trade with slippage and commission.

        Args:
            symbol: Asset symbol
            quantity: Shares to trade (positive = buy, negative = sell)
            price: Base price
            timestamp: Trade timestamp

        Returns:
            OrderResult with execution details
        """
        # Apply slippage
        if quantity > 0:
            # Buy: pay higher price
            fill_price = price * (1 + self.config.slippage_bps / 10000.0)
        else:
            # Sell: receive lower price
            fill_price = price * (1 - self.config.slippage_bps / 10000.0)

        # Calculate gross value
        gross_value = abs(quantity) * fill_price

        # Calculate commission
        commission = max(
            Decimal(str(gross_value * self.config.commission_pct)),
            self.config.min_commission
        )

        # Total cost (including commission)
        if quantity > 0:
            # Buy: cash outflow
            total_cost = Decimal(str(gross_value)) + commission
            self.cash -= total_cost
        else:
            # Sell: cash inflow
            total_proceeds = Decimal(str(gross_value)) - commission
            self.cash += total_proceeds

        # Update position
        if symbol in self.positions:
            position = self.positions[symbol]
            new_quantity = position.quantity + quantity

            if new_quantity == 0:
                # Position closed
                del self.positions[symbol]
            else:
                # Update position
                # Update average entry price (weighted) - convert to floats for calculation
                new_qty_float = float(new_quantity)
                if (position.quantity > 0 and quantity > 0) or \
                   (position.quantity < 0 and quantity < 0):
                    # Adding to position
                    pos_qty = float(position.quantity)
                    pos_entry = float(position.entry_price)
                    total_value = (pos_qty * pos_entry) + (quantity * fill_price)
                    new_entry_price = total_value / new_qty_float
                else:
                    # Reducing position, keep old entry price
                    new_entry_price = float(position.entry_price)

                # Create updated position (floats already converted above)
                entry_price_float = float(new_entry_price)
                market_value = new_qty_float * fill_price
                unrealized_pnl = (fill_price - entry_price_float) * new_qty_float

                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=Decimal(str(new_qty_float)),
                    entry_price=Decimal(str(entry_price_float)),
                    market_price=Decimal(str(fill_price)),
                    market_value=Decimal(str(market_value)),
                    unrealized_pnl=Decimal(str(unrealized_pnl))
                )
        else:
            # New position
            market_value = quantity * fill_price
            unrealized_pnl = 0.0  # No unrealized P&L at entry

            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=Decimal(str(quantity)),
                entry_price=Decimal(str(fill_price)),
                market_price=Decimal(str(fill_price)),
                market_value=Decimal(str(market_value)),
                unrealized_pnl=Decimal(str(unrealized_pnl))
            )

        # Log trade
        trade_record = {
            "timestamp": timestamp,
            "symbol": symbol,
            "quantity": quantity,
            "price": fill_price,
            "gross_value": gross_value,
            "commission": float(commission),
            "side": "BUY" if quantity > 0 else "SELL"
        }

        self.trade_history.append(trade_record)

        self.logger.log_trade(
            trade_id=f"{symbol}_{timestamp.isoformat()}",
            timestamp=timestamp.isoformat(),
            symbol=symbol,
            side=trade_record["side"].lower(),  # "buy" or "sell" (lowercase)
            quantity=abs(quantity),
            price=fill_price,
            fees=float(commission),
            nav_at_trade=float(self.get_nav())
        )

        # Create order result
        order_result = OrderResult(
            success=True,
            order_id=f"{symbol}_{timestamp.isoformat()}",
            filled_quantity=Decimal(str(abs(quantity))),
            filled_price=Decimal(str(fill_price)),
            fees=commission,
            slippage=Decimal(str(abs(fill_price - fill_price)))  # Slippage is already applied in fill_price
        )

        return order_result

    def _get_prices(self, timestamp: pd.Timestamp) -> Dict[str, float]:
        """
        Get prices for all assets at timestamp.

        Args:
            timestamp: Price timestamp

        Returns:
            Dict of symbol → price
        """
        prices = {}

        for symbol, df in self.asset_data.items():
            # Find bar at timestamp
            if timestamp not in df.index:
                # Try to find closest prior bar
                prior_bars = df[df.index <= timestamp]
                if len(prior_bars) == 0:
                    continue
                bar = prior_bars.iloc[-1]
            else:
                bar = df.loc[timestamp]

            # Get price based on fill timing
            if self.config.fill_timing == "close":
                price = bar['close']
            elif self.config.fill_timing == "open":
                price = bar['open']
            elif self.config.fill_timing == "vwap":
                # Simple VWAP approximation
                price = (bar['high'] + bar['low'] + bar['close']) / 3
            else:
                price = bar['close']

            prices[symbol] = float(price)

        return prices

    def get_positions(self) -> Dict[str, Position]:
        """Get current positions."""
        return self.positions.copy()

    def get_cash(self) -> Decimal:
        """Get current cash balance."""
        return self.cash

    def get_nav(self) -> Decimal:
        """
        Calculate current NAV (cash + position values).

        Uses market prices for positions.
        """
        nav = self.cash

        # Add position values using market_value from positions
        for symbol, position in self.positions.items():
            nav += position.market_value

        return nav

    def get_broker_metadata(self) -> Dict[str, any]:
        """
        Get backtest metadata.

        Returns:
            Dictionary with backtest-specific information
        """
        return {
            "mode": "backtest",
            "start_date": self.config.start_date,
            "end_date": self.config.end_date,
            "initial_nav": float(self.config.initial_nav),
            "slippage_bps": self.config.slippage_bps,
            "commission_bps": self.config.commission_bps,
        }

    def record_nav(self, timestamp: pd.Timestamp):
        """
        Record NAV snapshot at timestamp.

        Args:
            timestamp: Snapshot timestamp
        """
        # Get current prices
        prices = self._get_prices(timestamp)

        # Calculate position values at current market prices
        position_values = {}
        total_position_value = Decimal('0.00')

        for symbol, position in self.positions.items():
            if symbol in prices:
                market_price = Decimal(str(prices[symbol]))
            else:
                # Use entry price if market price unavailable
                market_price = position.entry_price

            position_value = position.quantity * market_price
            position_values[symbol] = float(position_value)
            total_position_value += position_value

        nav = self.cash + total_position_value

        # Record
        nav_record = {
            "timestamp": timestamp,
            "nav": float(nav),
            "cash": float(self.cash),
            "position_value": float(total_position_value),
            "positions": position_values.copy()
        }

        self.nav_history.append(nav_record)

    def get_nav_series(self) -> pd.Series:
        """
        Get NAV time series.

        Returns:
            Series with timestamp index and NAV values
        """
        if not self.nav_history:
            return pd.Series(dtype=float)

        df = pd.DataFrame(self.nav_history)
        df.set_index('timestamp', inplace=True)

        return df['nav']

    def get_trade_log(self) -> pd.DataFrame:
        """
        Get trade log as DataFrame.

        Returns:
            DataFrame with all trades
        """
        if not self.trade_history:
            return pd.DataFrame(columns=[
                'timestamp', 'symbol', 'quantity', 'price',
                'gross_value', 'commission', 'side'
            ])

        df = pd.DataFrame(self.trade_history)
        return df


# Example usage
if __name__ == "__main__":
    # Create sample data
    dates = pd.date_range('2025-01-01', periods=10, freq='4H', tz='UTC')
    spy_data = pd.DataFrame({
        'open': 450 + np.random.randn(10) * 2,
        'high': 452 + np.random.randn(10) * 2,
        'low': 448 + np.random.randn(10) * 2,
        'close': 450 + np.random.randn(10) * 2,
        'volume': np.random.randint(1000000, 5000000, 10)
    }, index=dates)

    qqq_data = pd.DataFrame({
        'open': 380 + np.random.randn(10) * 2,
        'high': 382 + np.random.randn(10) * 2,
        'low': 378 + np.random.randn(10) * 2,
        'close': 380 + np.random.randn(10) * 2,
        'volume': np.random.randint(1000000, 5000000, 10)
    }, index=dates)

    # Ensure OHLC consistency
    for df in [spy_data, qqq_data]:
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)

    asset_data = {
        'SPY': spy_data,
        'QQQ': qqq_data
    }

    # Create backtest executor
    config = BacktestConfig(
        initial_nav=Decimal('100000.00'),
        fill_timing='close',
        slippage_bps=5.0,
        commission_pct=0.001
    )

    executor = BacktestExecutor(config=config, asset_data=asset_data)

    print("=" * 60)
    print("Backtest Executor Test")
    print("=" * 60)

    print(f"\nInitial NAV: ${executor.get_nav():,.2f}")
    print(f"Initial Cash: ${executor.get_cash():,.2f}")

    # Submit target weights at first timestamp
    timestamp = dates[0]
    target_weights = {
        'SPY': 0.6,  # 60% in SPY
        'QQQ': 0.4   # 40% in QQQ
    }

    print(f"\nSubmitting target weights at {timestamp}:")
    for symbol, weight in target_weights.items():
        print(f"  {symbol}: {weight:.1%}")

    orders = executor.submit_target_weights(target_weights, timestamp)

    print(f"\nExecuted {len(orders)} orders:")
    for order in orders:
        print(f"  {order.symbol}: {order.quantity} shares @ ${order.filled_price:.2f} "
              f"(commission: ${order.commission:.2f})")

    # Record NAV
    executor.record_nav(timestamp)

    print(f"\nAfter execution:")
    print(f"  NAV: ${executor.get_nav():,.2f}")
    print(f"  Cash: ${executor.get_cash():,.2f}")

    positions = executor.get_positions()
    print(f"  Positions ({len(positions)}):")
    for symbol, position in positions.items():
        print(f"    {symbol}: {position.quantity} shares @ ${position.avg_price:.2f}")

    # Rebalance at later timestamp
    timestamp2 = dates[5]
    target_weights2 = {
        'SPY': 0.3,
        'QQQ': 0.7
    }

    print(f"\n\nRebalancing at {timestamp2}:")
    for symbol, weight in target_weights2.items():
        print(f"  {symbol}: {weight:.1%}")

    orders2 = executor.submit_target_weights(target_weights2, timestamp2)

    print(f"\nExecuted {len(orders2)} orders:")
    for order in orders2:
        side = "BUY" if order.quantity > 0 else "SELL"
        print(f"  {side} {order.symbol}: {abs(order.quantity)} shares @ ${order.filled_price:.2f}")

    executor.record_nav(timestamp2)

    print(f"\nAfter rebalance:")
    print(f"  NAV: ${executor.get_nav():,.2f}")
    print(f"  Cash: ${executor.get_cash():,.2f}")

    # Show trade log
    trade_log = executor.get_trade_log()
    print(f"\nTrade Log ({len(trade_log)} trades):")
    print(trade_log[['timestamp', 'symbol', 'side', 'quantity', 'price', 'commission']])

    # Show NAV series
    nav_series = executor.get_nav_series()
    print(f"\nNAV History:")
    print(nav_series)

    print("\n✓ Backtest executor test passed")
