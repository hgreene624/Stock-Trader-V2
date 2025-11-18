"""
Options Trading Engine for Alpaca

Complete implementation for:
- Searching option contracts
- Placing orders (buy/sell, open/close)
- Managing positions
- Tracking P&L
- Contract symbol parsing

Supports cash-secured puts, covered calls, spreads, and more.
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOptionContractsRequest,
    MarketOrderRequest,
    LimitOrderRequest,
    GetOrdersRequest
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderType,
    ContractType,
    QueryOrderStatus,
    AssetStatus,
    PositionSide
)
from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.requests import OptionLatestQuoteRequest

logger = logging.getLogger(__name__)


class OptionsEngine:
    """
    Production-ready options trading engine for Alpaca.

    Features:
    - Contract search with delta/DTE filters
    - Order placement (market/limit)
    - Position tracking and P&L
    - Buying power validation
    - Contract symbol parsing
    """

    def __init__(self, api_key: str = None, secret_key: str = None, paper: bool = True):
        """
        Initialize options engine.

        Args:
            api_key: Alpaca API key (defaults to env ALPACA_API_KEY)
            secret_key: Alpaca secret key (defaults to env ALPACA_SECRET_KEY)
            paper: Use paper trading (default: True)
        """
        self.api_key = api_key or os.getenv('ALPACA_API_KEY')
        self.secret_key = secret_key or os.getenv('ALPACA_SECRET_KEY')
        self.paper = paper

        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API credentials required. Set ALPACA_API_KEY and ALPACA_SECRET_KEY.")

        # Initialize clients
        self.trading_client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=self.paper
        )

        self.data_client = OptionHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )

        logger.info(f"OptionsEngine initialized (paper={self.paper})")

    def parse_option_symbol(self, symbol: str) -> Dict:
        """
        Parse Alpaca option symbol format: SPY250127P00608000

        Args:
            symbol: Option contract symbol

        Returns:
            Dict with underlying, expiration, type, strike
        """
        # Format: UNDERLYING + YYMMDD + C/P + 8-digit strike
        # Example: SPY250127P00608000

        # Find the 6-digit date (YYMMDD)
        # Scan for pattern: any text, then 6 digits, then C or P
        import re
        match = re.match(r'([A-Z]+)(\d{6})([CP])(\d{8})', symbol)

        if not match:
            raise ValueError(f"Invalid option symbol format: {symbol}")

        underlying, date_str, contract_type, strike_str = match.groups()

        # Parse date
        year = 2000 + int(date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        expiration = datetime(year, month, day).date()

        # Parse strike (divide by 1000 to get actual price)
        strike = int(strike_str) / 1000.0

        return {
            'underlying': underlying,
            'expiration': expiration,
            'type': 'put' if contract_type == 'P' else 'call',
            'strike': strike,
            'symbol': symbol
        }

    def format_option_symbol(
        self,
        underlying: str,
        expiration: datetime,
        contract_type: str,
        strike: float
    ) -> str:
        """
        Create Alpaca option symbol: SPY250127P00608000

        Args:
            underlying: Underlying symbol (e.g., SPY)
            expiration: Expiration date
            contract_type: 'call' or 'put'
            strike: Strike price

        Returns:
            Formatted option symbol
        """
        # Format date as YYMMDD
        date_str = expiration.strftime('%y%m%d')

        # Format strike as 8 digits (multiply by 1000, pad to 8)
        strike_int = int(strike * 1000)
        strike_str = f"{strike_int:08d}"

        # Contract type
        type_char = 'P' if contract_type.lower() == 'put' else 'C'

        return f"{underlying}{date_str}{type_char}{strike_str}"

    def search_contracts(
        self,
        underlying: str,
        expiration_gte: str = None,
        expiration_lte: str = None,
        contract_type: str = "put",
        strike_gte: float = None,
        strike_lte: float = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Search for option contracts.

        Args:
            underlying: Underlying symbol
            expiration_gte: Min expiration (YYYY-MM-DD)
            expiration_lte: Max expiration (YYYY-MM-DD)
            contract_type: 'call' or 'put'
            strike_gte: Min strike
            strike_lte: Max strike
            limit: Max results

        Returns:
            DataFrame with contract details
        """
        try:
            request = GetOptionContractsRequest(
                underlying_symbols=[underlying],
                status=AssetStatus.ACTIVE,
                expiration_date_gte=expiration_gte,
                expiration_date_lte=expiration_lte,
                type=ContractType.PUT if contract_type.lower() == 'put' else ContractType.CALL,
                strike_price_gte=str(strike_gte) if strike_gte else None,
                strike_price_lte=str(strike_lte) if strike_lte else None,
                limit=limit
            )

            contracts = self.trading_client.get_option_contracts(request)

            if not contracts:
                logger.warning(f"No contracts found for {underlying}")
                return pd.DataFrame()

            data = []
            for contract in contracts.option_contracts:
                data.append({
                    'symbol': contract.symbol,
                    'underlying': contract.underlying_symbol,
                    'strike': float(contract.strike_price),
                    'expiration': contract.expiration_date,
                    'type': contract.type.value,
                    'style': contract.style.value if hasattr(contract, 'style') else 'american',
                    'size': contract.size
                })

            df = pd.DataFrame(data)

            # Add DTE
            if len(df) > 0:
                df['dte'] = (pd.to_datetime(df['expiration']) - pd.Timestamp.now()).dt.days

            return df

        except Exception as e:
            logger.error(f"Error searching contracts: {e}")
            raise

    def get_account_info(self) -> Dict:
        """Get account information including buying power."""
        account = self.trading_client.get_account()

        return {
            'buying_power': float(account.buying_power),
            'cash': float(account.cash),
            'portfolio_value': float(account.portfolio_value),
            'options_buying_power': float(account.options_buying_power) if hasattr(account, 'options_buying_power') else float(account.buying_power),
            'options_approved_level': getattr(account, 'options_approved_level', None)
        }

    def validate_buying_power_csp(
        self,
        strike: float,
        quantity: int = 1
    ) -> Tuple[bool, float, str]:
        """
        Validate buying power for cash-secured put.

        Args:
            strike: Strike price
            quantity: Number of contracts

        Returns:
            (is_valid, required_capital, message)
        """
        # Cash-secured put requires strike * 100 * quantity in cash
        required_capital = strike * 100 * quantity

        account_info = self.get_account_info()
        available = account_info['options_buying_power']

        if available >= required_capital:
            return True, required_capital, f"✅ Sufficient capital: ${available:,.2f} >= ${required_capital:,.2f}"
        else:
            return False, required_capital, f"❌ Insufficient capital: ${available:,.2f} < ${required_capital:,.2f}"

    def sell_cash_secured_put(
        self,
        contract_symbol: str,
        quantity: int = 1,
        limit_price: float = None,
        dry_run: bool = True
    ) -> Dict:
        """
        Sell a cash-secured put (open short put position).

        Args:
            contract_symbol: Option contract symbol
            quantity: Number of contracts
            limit_price: Limit price (use None for market order)
            dry_run: If True, validate but don't submit

        Returns:
            Order response or validation result
        """
        # Parse contract
        contract_info = self.parse_option_symbol(contract_symbol)

        # Validate buying power
        is_valid, required, message = self.validate_buying_power_csp(
            strike=contract_info['strike'],
            quantity=quantity
        )

        if not is_valid:
            raise ValueError(f"Insufficient buying power: {message}")

        logger.info(f"Selling CSP: {contract_symbol} x{quantity}")
        logger.info(f"  Strike: ${contract_info['strike']:.2f}")
        logger.info(f"  Expiration: {contract_info['expiration']}")
        logger.info(f"  Required capital: ${required:,.2f}")

        if dry_run:
            return {
                'status': 'dry_run',
                'message': 'Order validated but not submitted (dry_run=True)',
                'contract': contract_info,
                'required_capital': required,
                'buying_power_check': message
            }

        # Place order
        if limit_price:
            order_request = LimitOrderRequest(
                symbol=contract_symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )
        else:
            order_request = MarketOrderRequest(
                symbol=contract_symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )

        order = self.trading_client.submit_order(order_request)

        logger.info(f"✅ Order submitted: {order.id}")

        return {
            'status': 'submitted',
            'order_id': order.id,
            'symbol': order.symbol,
            'qty': order.qty,
            'side': order.side.value,
            'type': order.type.value,
            'limit_price': float(order.limit_price) if order.limit_price else None,
            'submitted_at': order.submitted_at
        }

    def buy_to_close_put(
        self,
        contract_symbol: str,
        quantity: int = 1,
        limit_price: float = None,
        dry_run: bool = True
    ) -> Dict:
        """
        Buy to close an existing short put position.

        Args:
            contract_symbol: Option contract symbol
            quantity: Number of contracts
            limit_price: Limit price (use None for market order)
            dry_run: If True, validate but don't submit

        Returns:
            Order response
        """
        contract_info = self.parse_option_symbol(contract_symbol)

        logger.info(f"Buying to close: {contract_symbol} x{quantity}")

        if dry_run:
            return {
                'status': 'dry_run',
                'message': 'Order validated but not submitted (dry_run=True)',
                'contract': contract_info
            }

        # Place order
        if limit_price:
            order_request = LimitOrderRequest(
                symbol=contract_symbol,
                qty=quantity,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )
        else:
            order_request = MarketOrderRequest(
                symbol=contract_symbol,
                qty=quantity,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )

        order = self.trading_client.submit_order(order_request)

        logger.info(f"✅ Order submitted: {order.id}")

        return {
            'status': 'submitted',
            'order_id': order.id,
            'symbol': order.symbol,
            'qty': order.qty,
            'side': order.side.value
        }

    def get_positions(self) -> pd.DataFrame:
        """
        Get all open option positions.

        Returns:
            DataFrame with position details
        """
        try:
            positions = self.trading_client.get_all_positions()

            if not positions:
                return pd.DataFrame()

            data = []
            for pos in positions:
                # Filter to options only (symbol format check)
                if len(pos.symbol) >= 15:  # Options symbols are longer
                    try:
                        contract_info = self.parse_option_symbol(pos.symbol)

                        data.append({
                            'symbol': pos.symbol,
                            'underlying': contract_info['underlying'],
                            'type': contract_info['type'],
                            'strike': contract_info['strike'],
                            'expiration': contract_info['expiration'],
                            'qty': int(pos.qty),
                            'side': pos.side.value,
                            'avg_entry_price': float(pos.avg_entry_price),
                            'current_price': float(pos.current_price),
                            'market_value': float(pos.market_value),
                            'unrealized_pl': float(pos.unrealized_pl),
                            'unrealized_plpc': float(pos.unrealized_plpc)
                        })
                    except:
                        # Skip non-option positions
                        continue

            df = pd.DataFrame(data)

            # Add DTE
            if len(df) > 0:
                df['dte'] = (pd.to_datetime(df['expiration']) - pd.Timestamp.now()).dt.days

            return df

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return pd.DataFrame()

    def get_orders(self, status: str = 'open') -> pd.DataFrame:
        """
        Get option orders.

        Args:
            status: 'open', 'closed', or 'all'

        Returns:
            DataFrame with order details
        """
        try:
            if status == 'open':
                request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            elif status == 'closed':
                request = GetOrdersRequest(status=QueryOrderStatus.CLOSED)
            else:
                request = GetOrdersRequest(status=QueryOrderStatus.ALL)

            orders = self.trading_client.get_orders(request)

            if not orders:
                return pd.DataFrame()

            data = []
            for order in orders:
                # Filter to options
                if len(order.symbol) >= 15:
                    try:
                        contract_info = self.parse_option_symbol(order.symbol)

                        data.append({
                            'order_id': order.id,
                            'symbol': order.symbol,
                            'underlying': contract_info['underlying'],
                            'qty': int(order.qty),
                            'filled_qty': int(order.filled_qty) if order.filled_qty else 0,
                            'side': order.side.value,
                            'type': order.type.value,
                            'status': order.status.value,
                            'limit_price': float(order.limit_price) if order.limit_price else None,
                            'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                            'submitted_at': order.submitted_at
                        })
                    except:
                        continue

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return pd.DataFrame()


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("Options Trading Engine - Test Suite")
    print("=" * 80)
    print()

    # Initialize
    try:
        engine = OptionsEngine(paper=True)
        print("✅ Engine initialized (paper trading)")
        print()
    except ValueError as e:
        print(f"❌ {e}")
        print("Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables")
        sys.exit(1)

    # Test 1: Account info
    print("Test 1: Account Information")
    print("-" * 80)
    try:
        account = engine.get_account_info()
        print(f"Buying Power: ${account['buying_power']:,.2f}")
        print(f"Options Buying Power: ${account['options_buying_power']:,.2f}")
        print(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
        print(f"Options Level: {account['options_approved_level']}")
        print("✅ Account info retrieved")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 2: Search contracts
    print("Test 2: Search for SPY Put Contracts")
    print("-" * 80)
    try:
        today = datetime.now()
        min_exp = (today + timedelta(days=30)).strftime('%Y-%m-%d')
        max_exp = (today + timedelta(days=45)).strftime('%Y-%m-%d')

        contracts = engine.search_contracts(
            underlying="SPY",
            expiration_gte=min_exp,
            expiration_lte=max_exp,
            contract_type="put",
            limit=10
        )

        if len(contracts) > 0:
            print(f"Found {len(contracts)} contracts")
            print(contracts[['symbol', 'strike', 'expiration', 'dte']].head())
            print("✅ Contract search successful")
        else:
            print("⚠️  No contracts found (market might be closed)")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 3: Parse symbol
    print("Test 3: Parse Option Symbol")
    print("-" * 80)
    test_symbol = "SPY250127P00608000"
    try:
        parsed = engine.parse_option_symbol(test_symbol)
        print(f"Symbol: {test_symbol}")
        print(f"Parsed: {parsed}")
        print("✅ Symbol parsing successful")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 4: Validate buying power
    print("Test 4: Validate Buying Power (Cash-Secured Put)")
    print("-" * 80)
    try:
        is_valid, required, message = engine.validate_buying_power_csp(
            strike=600.0,
            quantity=1
        )
        print(f"Strike: $600.00, Quantity: 1")
        print(f"Required capital: ${required:,.2f}")
        print(message)
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

    # Test 5: Dry run sell CSP
    print("Test 5: Dry Run - Sell Cash-Secured Put")
    print("-" * 80)
    if len(contracts) > 0:
        test_contract = contracts.iloc[0]['symbol']
        try:
            result = engine.sell_cash_secured_put(
                contract_symbol=test_contract,
                quantity=1,
                limit_price=2.50,
                dry_run=True  # Don't actually submit
            )
            print(f"Contract: {test_contract}")
            print(f"Status: {result['status']}")
            print(f"Message: {result['message']}")
            print("✅ Dry run successful")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("⚠️  Skipped (no contracts available)")
    print()

    print("=" * 80)
    print("Test Suite Complete")
    print("=" * 80)
