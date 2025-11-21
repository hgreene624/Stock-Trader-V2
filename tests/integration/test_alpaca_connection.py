#!/usr/bin/env python3
"""
Alpaca Connection Test Script
Tests API authentication and live data access
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import Alpaca SDK components
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    StockBarsRequest,
    StockQuotesRequest
)
from alpaca.data.timeframe import TimeFrame


def test_trading_client():
    """Test trading client connection and account access"""
    print("=" * 60)
    print("TEST 1: Trading Client - Account Information")
    print("=" * 60)

    try:
        # Get credentials from environment
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_API_SECRET')

        if not api_key or not api_secret:
            print("❌ FAILED: API credentials not found in .env file")
            return False

        print(f"✓ API Key loaded: {api_key[:8]}...")
        print(f"✓ API Secret loaded: {api_secret[:8]}...")

        # Initialize trading client (paper trading by default)
        trading_client = TradingClient(
            api_key=api_key,
            secret_key=api_secret,
            paper=True  # Set to False for live trading
        )

        # Get account information
        account = trading_client.get_account()

        print("\n📊 Account Details:")
        print(f"   Account Number: {account.account_number}")
        print(f"   Status: {account.status}")
        print(f"   Cash: ${float(account.cash):,.2f}")
        print(f"   Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"   Buying Power: ${float(account.buying_power):,.2f}")
        print(f"   Pattern Day Trader: {account.pattern_day_trader}")
        print(f"   Trading Blocked: {account.trading_blocked}")
        print(f"   Account Blocked: {account.account_blocked}")

        print("\n✅ SUCCESS: Trading client connected successfully!")
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_market_data_client():
    """Test market data client and live data access"""
    print("\n" + "=" * 60)
    print("TEST 2: Market Data Client - Live Stock Quotes")
    print("=" * 60)

    try:
        # Get credentials from environment
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_API_SECRET')

        # Initialize market data client
        # Note: For free tier, you may need to use paper=True
        data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=api_secret
        )

        # Test 1: Get latest quote for SPY and QQQ
        print("\n📈 Latest Quotes:")
        symbols = ['SPY', 'QQQ', 'AAPL']

        request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
        latest_quotes = data_client.get_stock_latest_quote(request)

        for symbol in symbols:
            quote = latest_quotes[symbol]
            print(f"\n   {symbol}:")
            print(f"      Bid: ${quote.bid_price:.2f} x {quote.bid_size}")
            print(f"      Ask: ${quote.ask_price:.2f} x {quote.ask_size}")
            print(f"      Timestamp: {quote.timestamp}")

        # Test 2: Get recent daily bars
        print("\n\n📊 Recent Daily Bars (Last 5 Days):")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)  # Get extra days to account for weekends

        bars_request = StockBarsRequest(
            symbol_or_symbols=['SPY'],
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )

        bars = data_client.get_stock_bars(bars_request)
        df = bars.df

        # Display last 5 bars
        print(f"\n   SPY - Last {min(5, len(df))} days:")
        for idx, row in df.tail(5).iterrows():
            timestamp = idx[1] if isinstance(idx, tuple) else idx
            print(f"      {timestamp.strftime('%Y-%m-%d')}: "
                  f"O=${row['open']:.2f} H=${row['high']:.2f} "
                  f"L=${row['low']:.2f} C=${row['close']:.2f} "
                  f"V={int(row['volume']):,}")

        print("\n✅ SUCCESS: Market data client connected successfully!")
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_positions_and_orders():
    """Test getting current positions and recent orders"""
    print("\n" + "=" * 60)
    print("TEST 3: Positions and Orders")
    print("=" * 60)

    try:
        api_key = os.getenv('ALPACA_API_KEY')
        api_secret = os.getenv('ALPACA_API_SECRET')

        trading_client = TradingClient(
            api_key=api_key,
            secret_key=api_secret,
            paper=True
        )

        # Get current positions
        positions = trading_client.get_all_positions()
        print(f"\n📍 Current Positions: {len(positions)}")

        if positions:
            for position in positions:
                print(f"\n   {position.symbol}:")
                print(f"      Qty: {position.qty}")
                print(f"      Market Value: ${float(position.market_value):,.2f}")
                print(f"      Avg Entry: ${float(position.avg_entry_price):,.2f}")
                print(f"      Current Price: ${float(position.current_price):,.2f}")
                print(f"      Unrealized P&L: ${float(position.unrealized_pl):,.2f} "
                      f"({float(position.unrealized_plpc) * 100:.2f}%)")
        else:
            print("   No open positions")

        # Get recent orders
        orders = trading_client.get_orders()
        print(f"\n📋 Recent Orders: {len(orders)}")

        if orders:
            for order in orders[:5]:  # Show last 5 orders
                print(f"\n   {order.symbol} - {order.side} {order.qty} @ {order.type}:")
                print(f"      Status: {order.status}")
                print(f"      Created: {order.created_at}")
        else:
            print("   No recent orders")

        print("\n✅ SUCCESS: Retrieved positions and orders!")
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all connection tests"""
    print("\n" + "🚀 " * 20)
    print("ALPACA CONNECTION TEST SUITE")
    print("🚀 " * 20)

    results = []

    # Run all tests
    results.append(("Trading Client", test_trading_client()))
    results.append(("Market Data Client", test_market_data_client()))
    results.append(("Positions & Orders", test_positions_and_orders()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed! Your Alpaca connection is working perfectly!")
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
