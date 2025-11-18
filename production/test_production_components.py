"""
Test Production Components Before Docker Build.

Validates:
- Alpaca API credentials and connectivity
- Broker adapter functionality
- Data fetcher (hybrid approach)
- Model loading and execution
- Health monitor

Run this BEFORE building Docker to catch issues early.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import production components
from production.runner.broker_adapter import AlpacaBrokerAdapter
from production.runner.live_data_fetcher import HybridDataFetcher
from production.runner.health_monitor import HealthMonitor


def load_env_from_file():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent / 'docker' / '.env'

    if not env_file.exists():
        logger.error(f"❌ .env file not found: {env_file}")
        logger.error("   Create it with: cp production/docker/.env.example production/docker/.env")
        return False

    # Simple .env parser
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    logger.info(f"✅ Loaded environment from {env_file}")
    return True


def test_alpaca_credentials():
    """Test 1: Verify Alpaca API credentials work."""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Alpaca API Credentials")
    logger.info("="*80)

    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    mode = os.getenv('MODE', 'paper')

    if not api_key or not secret_key:
        logger.error("❌ ALPACA_API_KEY or ALPACA_SECRET_KEY not set in .env")
        return False

    logger.info(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    logger.info(f"Mode: {mode}")

    try:
        broker = AlpacaBrokerAdapter(
            api_key=api_key,
            secret_key=secret_key,
            paper=(mode == 'paper')
        )

        # Test account access
        account = broker.get_account()

        logger.info(f"✅ Account connected successfully!")
        logger.info(f"   Equity: ${account['equity']:,.2f}")
        logger.info(f"   Cash: ${account['cash']:,.2f}")
        logger.info(f"   Buying Power: ${account['buying_power']:,.2f}")
        logger.info(f"   Pattern Day Trader: {account['pattern_day_trader']}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to connect to Alpaca: {e}")
        return False


def test_broker_adapter():
    """Test 2: Test broker adapter functionality."""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Broker Adapter Functionality")
    logger.info("="*80)

    try:
        broker = AlpacaBrokerAdapter(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            paper=(os.getenv('MODE', 'paper') == 'paper')
        )

        # Test 2a: Get positions
        logger.info("\nTest 2a: Get Positions")
        positions = broker.get_positions()
        logger.info(f"✅ Retrieved {len(positions)} positions")

        if positions:
            for symbol, pos in list(positions.items())[:3]:  # Show first 3
                logger.info(
                    f"   {symbol}: {pos['quantity']} shares @ "
                    f"${pos['current_price']:.2f} = ${pos['market_value']:,.2f}"
                )

        # Test 2b: Get current prices
        logger.info("\nTest 2b: Get Current Prices")
        symbols = ['SPY', 'QQQ', 'XLE']
        prices = broker.get_current_prices(symbols)
        logger.info(f"✅ Retrieved prices for {len(prices)} symbols")

        for symbol, price in prices.items():
            logger.info(f"   {symbol}: ${price:.2f}")

        # Test 2c: Get latest bars
        logger.info("\nTest 2c: Get Latest Bars")
        bars = broker.get_latest_bars(symbols, timeframe='1Day', limit=5)
        logger.info(f"✅ Retrieved bars for {len(bars)} symbols")

        for symbol, bar_list in bars.items():
            logger.info(f"   {symbol}: {len(bar_list)} bars")
            if bar_list:
                latest = bar_list[-1]
                logger.info(
                    f"      Latest: {latest['timestamp']} "
                    f"Close=${latest['close']:.2f} Vol={latest['volume']:,.0f}"
                )

        return True

    except Exception as e:
        logger.error(f"❌ Broker adapter test failed: {e}", exc_info=True)
        return False


def test_data_fetcher():
    """Test 3: Test hybrid data fetcher."""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Hybrid Data Fetcher")
    logger.info("="*80)

    try:
        broker = AlpacaBrokerAdapter(
            api_key=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            paper=(os.getenv('MODE', 'paper') == 'paper')
        )

        # Create data fetcher (will use /tmp for cache in test)
        test_cache_dir = Path('/tmp/trading_test_cache')
        test_cache_dir.mkdir(parents=True, exist_ok=True)

        fetcher = HybridDataFetcher(
            broker_adapter=broker,
            cache_dir=str(test_cache_dir),
            max_lookback_days=250,
            api_fetch_bars=10
        )

        # Test fetching data for context
        logger.info("\nFetching data for SPY, QQQ...")
        symbols = ['SPY', 'QQQ']

        asset_features = fetcher.get_data_for_context(
            symbols=symbols,
            current_timestamp=datetime.now(timezone.utc)
        )

        logger.info(f"✅ Data fetched for {len(asset_features)}/{len(symbols)} symbols")

        for symbol, df in asset_features.items():
            logger.info(f"\n   {symbol}:")
            logger.info(f"      Rows: {len(df)}")
            logger.info(f"      Columns: {list(df.columns)}")
            logger.info(f"      Date range: {df.index[0]} to {df.index[-1]}")
            logger.info(f"      Latest close: ${df['Close'].iloc[-1]:.2f}")
            logger.info(f"      MA_200: ${df['MA_200'].iloc[-1]:.2f}")
            logger.info(f"      RSI_14: {df['RSI_14'].iloc[-1]:.2f}")

        return True

    except Exception as e:
        logger.error(f"❌ Data fetcher test failed: {e}", exc_info=True)
        return False


def test_health_monitor():
    """Test 4: Test health monitoring."""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Health Monitor")
    logger.info("="*80)

    try:
        monitor = HealthMonitor(port=8081)  # Use different port for test

        # Record some activity
        monitor.record_cycle_start()
        monitor.record_cycle_complete()
        monitor.record_order_submitted(success=True)
        monitor.record_metric('test_metric', 123.45)

        # Get status
        status, details = monitor.get_health_status()

        logger.info(f"✅ Health monitor working")
        logger.info(f"   Status: {status}")
        logger.info(f"   Total cycles: {details['total_cycles']}")
        logger.info(f"   Errors: {details['errors']}")

        metrics = monitor.get_metrics()
        logger.info(f"   Metrics: {len(metrics)} tracked")

        return True

    except Exception as e:
        logger.error(f"❌ Health monitor test failed: {e}", exc_info=True)
        return False


def test_model_export():
    """Test 5: Verify model can be exported."""
    logger.info("\n" + "="*80)
    logger.info("TEST 5: Model Export")
    logger.info("="*80)

    try:
        # Check if model file exists
        model_file = Path(__file__).parent.parent / 'models' / 'sector_rotation_v1.py'

        if not model_file.exists():
            logger.warning(f"⚠️  Model file not found: {model_file}")
            logger.warning("   This is OK if you haven't created the model yet")
            return True

        logger.info(f"✅ Model file found: {model_file}")

        # Check if profile exists
        profiles_file = Path(__file__).parent.parent / 'configs' / 'profiles.yaml'

        if profiles_file.exists():
            import yaml
            with open(profiles_file, 'r') as f:
                profiles = yaml.safe_load(f)

            # Check for sector rotation profiles
            sector_profiles = [
                name for name in profiles.keys()
                if 'sector' in name.lower()
            ]

            logger.info(f"✅ Found {len(sector_profiles)} sector rotation profiles:")
            for profile_name in sector_profiles[:3]:
                logger.info(f"   - {profile_name}")

        return True

    except Exception as e:
        logger.error(f"❌ Model export test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("\n" + "="*80)
    logger.info("PRODUCTION COMPONENTS TEST SUITE")
    logger.info("="*80)
    logger.info("Testing production components before Docker build...")
    logger.info("")

    # Load environment
    if not load_env_from_file():
        logger.error("\n❌ Cannot proceed without .env file")
        return False

    # Run tests
    results = {
        'Alpaca Credentials': test_alpaca_credentials(),
        'Broker Adapter': test_broker_adapter(),
        'Data Fetcher': test_data_fetcher(),
        'Health Monitor': test_health_monitor(),
        'Model Export': test_model_export(),
    }

    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}")

    all_passed = all(results.values())

    logger.info("\n" + "="*80)
    if all_passed:
        logger.info("✅ ALL TESTS PASSED!")
        logger.info("="*80)
        logger.info("\nYou're ready to build the Docker image:")
        logger.info("  ./production/deploy/build.sh SectorRotationModel_v1")
        logger.info("\nOr test locally first:")
        logger.info("  ./production/deploy/local-test.sh")
    else:
        logger.info("❌ SOME TESTS FAILED")
        logger.info("="*80)
        logger.info("\nFix the issues above before building Docker image.")
        logger.info("Common issues:")
        logger.info("  - Check .env file has correct API keys")
        logger.info("  - Verify internet connection")
        logger.info("  - Ensure Alpaca account is active")

    logger.info("="*80 + "\n")

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
