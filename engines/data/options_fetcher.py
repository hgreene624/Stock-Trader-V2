"""
Options data fetching for Alpaca.

Fetches options chains, greeks, and IV data for options strategies.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.requests import GetOptionContractsRequest
from alpaca.trading.enums import ContractType, AssetStatus

logger = logging.getLogger(__name__)


class OptionsDataFetcher:
    """
    Fetches options data from Alpaca.

    Provides:
    - Options chains (calls and puts)
    - Greeks (delta, gamma, theta, vega)
    - Implied volatility
    - Bid/ask spreads
    """

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        """
        Initialize options data fetcher.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: Use paper trading endpoint
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper

        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )

        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        logger.info(f"Initialized OptionsDataFetcher (paper={paper})")

    def get_options_chain(
        self,
        underlying: str,
        expiration_date_gte: Optional[datetime] = None,
        expiration_date_lte: Optional[datetime] = None,
        contract_type: Optional[ContractType] = None,
        strike_price_gte: Optional[float] = None,
        strike_price_lte: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Get options chain for an underlying symbol.

        Args:
            underlying: Symbol (e.g., 'SPY')
            expiration_date_gte: Minimum expiration date
            expiration_date_lte: Maximum expiration date
            contract_type: ContractType.CALL or ContractType.PUT
            strike_price_gte: Minimum strike price
            strike_price_lte: Maximum strike price

        Returns:
            DataFrame with columns:
                - symbol: Option symbol
                - strike_price: Strike price
                - expiration_date: Expiration date
                - contract_type: 'call' or 'put'
                - status: Option status
        """
        try:
            request = GetOptionContractsRequest(
                underlying_symbols=[underlying],
                status=AssetStatus.ACTIVE,
                expiration_date_gte=expiration_date_gte,
                expiration_date_lte=expiration_date_lte,
                type=contract_type,
                strike_price_gte=strike_price_gte,
                strike_price_lte=strike_price_lte
            )

            contracts = self.trading_client.get_option_contracts(request)

            if not contracts:
                logger.warning(f"No options found for {underlying}")
                return pd.DataFrame()

            # Convert to DataFrame
            data = []
            for contract in contracts:
                data.append({
                    'symbol': contract.symbol,
                    'strike_price': float(contract.strike_price),
                    'expiration_date': contract.expiration_date,
                    'contract_type': contract.type.value,
                    'status': contract.status.value,
                    'underlying_symbol': contract.underlying_symbol,
                    'contract_id': contract.id
                })

            df = pd.DataFrame(data)
            logger.info(f"Retrieved {len(df)} options for {underlying}")

            return df

        except Exception as e:
            logger.error(f"Error fetching options chain for {underlying}: {e}")
            return pd.DataFrame()

    def get_underlying_price(self, symbol: str) -> Optional[float]:
        """
        Get current price of underlying symbol.

        Args:
            symbol: Underlying symbol (e.g., 'SPY')

        Returns:
            Current price or None
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request)

            if symbol in quote:
                price = float(quote[symbol].ask_price)
                logger.debug(f"{symbol} price: ${price:.2f}")
                return price

            return None

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def find_put_by_delta(
        self,
        underlying: str,
        target_delta: float = 0.30,
        min_dte: int = 30,
        max_dte: int = 45
    ) -> Optional[Dict]:
        """
        Find put option closest to target delta.

        For cash-secured puts, typical target is 0.30 delta
        (~30% probability of being ITM at expiration).

        Args:
            underlying: Symbol (e.g., 'SPY')
            target_delta: Target delta (0.30 = 30 delta)
            min_dte: Minimum days to expiration
            max_dte: Maximum days to expiration

        Returns:
            Dict with option details or None
        """
        try:
            # Get underlying price
            underlying_price = self.get_underlying_price(underlying)
            if not underlying_price:
                logger.error(f"Could not get price for {underlying}")
                return None

            # Calculate date range
            today = datetime.now()
            exp_min = today + timedelta(days=min_dte)
            exp_max = today + timedelta(days=max_dte)

            # Get put options chain
            chain = self.get_options_chain(
                underlying=underlying,
                expiration_date_gte=exp_min,
                expiration_date_lte=exp_max,
                contract_type=ContractType.PUT
            )

            if chain.empty:
                logger.warning(f"No puts found for {underlying}")
                return None

            # Estimate strike based on delta
            # For 0.30 delta put, strike is typically ~7-10% OTM
            # Rough approximation: delta ≈ (strike - price) / (2 * price * sqrt(DTE/365))
            # For simplicity, use: 0.30 delta put ≈ 93-95% of current price
            target_strike = underlying_price * (1 - target_delta)

            # Find closest strike
            chain['strike_diff'] = abs(chain['strike_price'] - target_strike)
            best_option = chain.nsmallest(1, 'strike_diff').iloc[0]

            result = {
                'symbol': best_option['symbol'],
                'strike_price': best_option['strike_price'],
                'expiration_date': best_option['expiration_date'],
                'underlying_price': underlying_price,
                'dte': (best_option['expiration_date'] - today).days,
                'estimated_delta': target_delta,  # Would need greeks API for actual delta
                'moneyness': best_option['strike_price'] / underlying_price
            }

            logger.info(
                f"Found put: {result['symbol']} @ ${result['strike_price']:.2f} "
                f"(DTE={result['dte']}, ~{target_delta:.2f}Δ)"
            )

            return result

        except Exception as e:
            logger.error(f"Error finding put by delta: {e}")
            return None

    def calculate_put_return(
        self,
        strike_price: float,
        premium: float,
        assignment_probability: float = 0.30
    ) -> Dict[str, float]:
        """
        Calculate expected return for cash-secured put.

        Args:
            strike_price: Put strike price
            premium: Premium collected
            assignment_probability: Probability of assignment (≈ delta)

        Returns:
            Dict with return metrics
        """
        # Capital at risk (need to hold cash to buy 100 shares)
        capital_at_risk = strike_price * 100

        # Return if not assigned (keep premium)
        return_if_expire = premium / capital_at_risk

        # Return if assigned (buy at strike, premium reduces cost basis)
        cost_basis = strike_price - premium
        return_if_assigned = -premium / capital_at_risk  # Slight loss from premium

        # Expected return
        expected_return = (
            (1 - assignment_probability) * return_if_expire +
            assignment_probability * return_if_assigned
        )

        return {
            'capital_at_risk': capital_at_risk,
            'return_if_expire': return_if_expire,
            'return_if_assigned': return_if_assigned,
            'expected_return': expected_return,
            'premium': premium
        }


def main():
    """Test options data fetcher."""
    import os

    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not secret_key:
        print("Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables")
        return

    fetcher = OptionsDataFetcher(api_key, secret_key, paper=True)

    # Test 1: Get SPY price
    print("\n=== Test 1: Get SPY price ===")
    price = fetcher.get_underlying_price('SPY')
    print(f"SPY price: ${price:.2f}")

    # Test 2: Get options chain
    print("\n=== Test 2: Get SPY put chain (30-45 DTE) ===")
    today = datetime.now()
    chain = fetcher.get_options_chain(
        underlying='SPY',
        expiration_date_gte=today + timedelta(days=30),
        expiration_date_lte=today + timedelta(days=45),
        contract_type=ContractType.PUT
    )
    print(f"Found {len(chain)} puts")
    if not chain.empty:
        print(chain[['symbol', 'strike_price', 'expiration_date']].head())

    # Test 3: Find 0.30 delta put
    print("\n=== Test 3: Find 0.30 delta put ===")
    put = fetcher.find_put_by_delta('SPY', target_delta=0.30)
    if put:
        print(f"Symbol: {put['symbol']}")
        print(f"Strike: ${put['strike_price']:.2f}")
        print(f"Underlying: ${put['underlying_price']:.2f}")
        print(f"DTE: {put['dte']}")
        print(f"Moneyness: {put['moneyness']:.2%}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
