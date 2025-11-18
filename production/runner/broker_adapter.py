"""
Alpaca Broker Adapter for Production Trading.

Handles all interactions with Alpaca REST API:
- Account management
- Position reconciliation
- Order submission and tracking
- Error handling and retries
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timezone

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestBarRequest
from alpaca.data.timeframe import TimeFrame


logger = logging.getLogger(__name__)


class AlpacaBrokerAdapter:
    """
    Production broker adapter for Alpaca.

    Features:
    - Paper and live trading support
    - Position reconciliation
    - Order submission with retry logic
    - Rate limit handling
    - Error recovery
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = True,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Initialize Alpaca broker adapter.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: Use paper trading if True, live if False
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Delay between retries (seconds)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize Alpaca clients
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )

        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        # Cache
        self._account_cache = None
        self._account_cache_time = None
        self._account_cache_ttl = 60.0  # 1 minute

        logger.info(f"Initialized Alpaca adapter (paper={paper})")

    def _retry_request(self, func, *args, **kwargs):
        """Execute request with retry logic."""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                time.sleep(self.retry_delay * (attempt + 1))

    def get_account(self, use_cache: bool = True) -> Dict:
        """
        Get account information.

        Args:
            use_cache: Use cached account info if available

        Returns:
            Dict with account info (equity, cash, buying_power, etc.)
        """
        now = time.time()

        # Check cache
        if use_cache and self._account_cache:
            if now - self._account_cache_time < self._account_cache_ttl:
                return self._account_cache

        # Fetch account
        account = self._retry_request(self.trading_client.get_account)

        result = {
            'equity': float(account.equity),
            'cash': float(account.cash),
            'buying_power': float(account.buying_power),
            'portfolio_value': float(account.portfolio_value),
            'pattern_day_trader': account.pattern_day_trader,
            'trading_blocked': account.trading_blocked,
            'account_blocked': account.account_blocked,
        }

        # Update cache
        self._account_cache = result
        self._account_cache_time = now

        return result

    def get_positions(self) -> Dict[str, Dict]:
        """
        Get current positions from broker.

        Returns:
            Dict[symbol, position_info] where position_info contains:
            - quantity: Number of shares
            - market_value: Current market value
            - cost_basis: Total cost basis
            - unrealized_pl: Unrealized P&L
            - unrealized_plpc: Unrealized P&L percent
        """
        positions = self._retry_request(self.trading_client.get_all_positions)

        result = {}
        for pos in positions:
            result[pos.symbol] = {
                'quantity': float(pos.qty),
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'current_price': float(pos.current_price),
                'avg_entry_price': float(pos.avg_entry_price),
            }

        logger.info(f"Retrieved {len(result)} positions from broker")
        return result

    def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current market prices for symbols.

        Args:
            symbols: List of symbols to fetch

        Returns:
            Dict[symbol, price]
        """
        request = StockLatestBarRequest(symbol_or_symbols=symbols)
        bars = self._retry_request(self.data_client.get_stock_latest_bar, request)

        prices = {}
        for symbol in symbols:
            if symbol in bars:
                prices[symbol] = float(bars[symbol].close)
            else:
                logger.warning(f"No price data for {symbol}")

        return prices

    def get_latest_bars(
        self,
        symbols: List[str],
        timeframe: str = '4Hour',
        limit: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Get latest bars for symbols.

        Args:
            symbols: List of symbols
            timeframe: Bar timeframe ('4Hour', '1Day', etc.)
            limit: Number of bars to fetch

        Returns:
            Dict[symbol, List[bar_dict]] where bar_dict has OHLCV data
        """
        # Map timeframe string to Alpaca TimeFrame
        tf_map = {
            '4Hour': TimeFrame.Hour,  # Will request 4x 1H bars
            '1Day': TimeFrame.Day,
            '1Hour': TimeFrame.Hour,
        }

        tf = tf_map.get(timeframe, TimeFrame.Hour)

        # Fetch bars
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=tf,
            limit=limit * 4 if timeframe == '4Hour' else limit
        )

        bars_response = self._retry_request(self.data_client.get_stock_bars, request)

        result = {}
        for symbol in symbols:
            # Use .data dict instead of 'in' check (BarSet.__contains__ doesn't work reliably)
            if symbol in bars_response.data and len(bars_response.data[symbol]) > 0:
                bars = bars_response.data[symbol]
                result[symbol] = [
                    {
                        'timestamp': bar.timestamp,
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': float(bar.volume),
                    }
                    for bar in bars
                ]
            else:
                result[symbol] = []
                logger.warning(f"No bar data for {symbol}")

        return result

    def submit_order(
        self,
        symbol: str,
        quantity: float,
        side: str,
        order_type: str = 'market',
        limit_price: Optional[float] = None,
        time_in_force: str = 'day'
    ) -> Dict:
        """
        Submit order to broker.

        Args:
            symbol: Symbol to trade
            quantity: Number of shares (absolute value)
            side: 'buy' or 'sell'
            order_type: 'market' or 'limit'
            limit_price: Limit price for limit orders
            time_in_force: 'day', 'gtc', 'ioc', 'fok'

        Returns:
            Order info dict with order_id, status, filled_qty, etc.
        """
        # Validate
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive: {quantity}")

        side_enum = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
        tif_map = {
            'day': TimeInForce.DAY,
            'gtc': TimeInForce.GTC,
            'ioc': TimeInForce.IOC,
            'fok': TimeInForce.FOK,
        }
        tif_enum = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

        # Create order request
        if order_type.lower() == 'market':
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side_enum,
                time_in_force=tif_enum
            )
        elif order_type.lower() == 'limit':
            if limit_price is None:
                raise ValueError("limit_price required for limit orders")
            order_request = LimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side_enum,
                time_in_force=tif_enum,
                limit_price=limit_price
            )
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        # Submit order
        logger.info(
            f"Submitting {side} order: {symbol} {quantity} @ {order_type}"
        )

        order = self._retry_request(
            self.trading_client.submit_order,
            order_request
        )

        result = {
            'order_id': str(order.id),
            'symbol': order.symbol,
            'quantity': float(order.qty),
            'side': side,
            'type': order_type,
            'status': order.status.value,
            'filled_qty': float(order.filled_qty) if order.filled_qty else 0.0,
            'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else 0.0,
            'submitted_at': order.submitted_at,
        }

        logger.info(f"Order submitted: {result['order_id']} ({result['status']})")
        return result

    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders.

        Returns:
            Number of orders cancelled
        """
        logger.info("Cancelling all open orders...")
        cancelled = self._retry_request(self.trading_client.cancel_orders)
        count = len(cancelled) if cancelled else 0
        logger.info(f"Cancelled {count} orders")
        return count

    def close_all_positions(self) -> int:
        """
        Close all positions at market.

        Returns:
            Number of positions closed
        """
        logger.info("Closing all positions...")
        positions = self.get_positions()

        closed_count = 0
        for symbol, pos_info in positions.items():
            qty = abs(pos_info['quantity'])
            if qty > 0:
                side = 'sell' if pos_info['quantity'] > 0 else 'buy'
                try:
                    self.submit_order(symbol, qty, side, order_type='market')
                    closed_count += 1
                except Exception as e:
                    logger.error(f"Failed to close position {symbol}: {e}")

        logger.info(f"Closed {closed_count} positions")
        return closed_count

    def reconcile_positions(
        self,
        expected_positions: Dict[str, float]
    ) -> Tuple[Dict[str, float], List[str]]:
        """
        Reconcile expected positions with broker positions.

        Args:
            expected_positions: Dict[symbol, quantity] from internal tracking

        Returns:
            Tuple of (position_diffs, warnings)
            - position_diffs: Dict[symbol, diff] where diff = broker - expected
            - warnings: List of warning messages
        """
        broker_positions = self.get_positions()

        diffs = {}
        warnings = []

        # Check all expected positions
        all_symbols = set(expected_positions.keys()) | set(broker_positions.keys())

        for symbol in all_symbols:
            expected = expected_positions.get(symbol, 0.0)
            actual = broker_positions.get(symbol, {}).get('quantity', 0.0)

            diff = actual - expected

            if abs(diff) > 0.01:  # Tolerance for rounding
                diffs[symbol] = diff
                warnings.append(
                    f"Position mismatch {symbol}: expected {expected}, "
                    f"actual {actual}, diff {diff}"
                )

        if warnings:
            logger.warning(f"Reconciliation found {len(warnings)} mismatches")
            for warning in warnings:
                logger.warning(warning)
        else:
            logger.info("Position reconciliation: all positions match")

        return diffs, warnings

    def get_buying_power_for_symbol(self, symbol: str) -> float:
        """
        Calculate available buying power for a symbol.

        Args:
            symbol: Symbol to check

        Returns:
            Available buying power in dollars
        """
        account = self.get_account()
        return account['buying_power']
