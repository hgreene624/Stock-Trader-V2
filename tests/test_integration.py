"""
Integration test for complete backtest workflow.

Tests the full end-to-end flow:
1. Generate synthetic data
2. Run backtest with EquityTrendModel_v1
3. Verify results
4. Test data persistence
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
from pathlib import Path
import tempfile
import shutil
import sys
sys.path.append('..')
from engines.data.downloader import DataDownloader
from engines.data.features import FeatureComputer
from models.equity_trend_v1 import EquityTrendModel_v1
from backtest.runner import BacktestRunner
from results.schema import ResultsDatabase
from utils.config import ConfigLoader


class TestIntegration:
    """Integration tests for complete backtest workflow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    def generate_synthetic_data(
        self,
        symbol: str,
        start_date: str,
        periods: int,
        freq: str,
        data_dir: Path
    ):
        """
        Generate synthetic OHLCV data for testing.

        Args:
            symbol: Ticker symbol
            start_date: Start date
            periods: Number of bars
            freq: Frequency (4H or 1D)
            data_dir: Data directory
        """
        # Generate price series with trend
        np.random.seed(42)
        base_price = 450 if symbol == 'SPY' else 380

        # Random walk with slight upward drift
        returns = np.random.normal(0.0001, 0.015, periods)
        close_prices = base_price * np.exp(np.cumsum(returns))

        # Generate OHLCV
        dates = pd.date_range(start_date, periods=periods, freq=freq, tz='UTC')

        df = pd.DataFrame({
            'open': close_prices * (1 + np.random.normal(0, 0.003, periods)),
            'high': close_prices * (1 + np.abs(np.random.normal(0.008, 0.005, periods))),
            'low': close_prices * (1 - np.abs(np.random.normal(0.008, 0.005, periods))),
            'close': close_prices,
            'volume': np.random.randint(1000000, 10000000, periods)
        }, index=dates)

        # Ensure OHLC consistency
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)

        # Save to parquet
        output_dir = data_dir / 'equities'
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{symbol}_{freq}.parquet"
        df.to_parquet(output_path, engine='pyarrow', compression='snappy')

        return df

    def test_complete_backtest_workflow(self, temp_dir):
        """Test complete backtest workflow from data to results."""
        print("\n" + "=" * 70)
        print("INTEGRATION TEST: Complete Backtest Workflow")
        print("=" * 70)

        data_dir = Path(temp_dir) / 'data'
        config_dir = Path(temp_dir) / 'configs'
        results_dir = Path(temp_dir) / 'results'

        # Step 1: Generate synthetic data
        print("\nStep 1: Generating synthetic data...")

        # Generate daily data (500 days)
        spy_daily = self.generate_synthetic_data(
            'SPY', '2023-01-01', 500, '1D', data_dir
        )
        qqq_daily = self.generate_synthetic_data(
            'QQQ', '2023-01-01', 500, '1D', data_dir
        )

        # Generate H4 data (500 days * 6 bars/day = 3000 bars)
        spy_h4 = self.generate_synthetic_data(
            'SPY', '2023-01-01', 3000, '4H', data_dir
        )
        qqq_h4 = self.generate_synthetic_data(
            'QQQ', '2023-01-01', 3000, '4H', data_dir
        )

        print(f"  Generated SPY: {len(spy_daily)} daily bars, {len(spy_h4)} H4 bars")
        print(f"  Generated QQQ: {len(qqq_daily)} daily bars, {len(qqq_h4)} H4 bars")

        # Step 2: Create config file
        print("\nStep 2: Creating config file...")

        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / 'test_config.yaml'

        config_content = f"""
backtest:
  data_dir: {data_dir}
  h4_timeframe: "4H"
  daily_timeframe: "1D"
  asset_class: "equity"
  symbols: ["SPY", "QQQ"]
  start_date: "2023-06-01"
  end_date: "2024-01-01"
  initial_nav: 100000.0
  fill_timing: "close"
  slippage_bps: 5.0
  commission_pct: 0.001
  min_commission: 1.0
  lookback_bars: 100

models:
  EquityTrendModel_v1:
    budget: 0.30
    ma_period: 200
    momentum_period: 120

risk:
  per_asset_limit: 0.40
  asset_class_limits:
    equity: 1.0
    crypto: 0.20
  leverage_limit: 1.2
  drawdown_threshold: 0.15
"""

        with open(config_path, 'w') as f:
            f.write(config_content)

        print(f"  Created config at {config_path}")

        # Step 3: Initialize model
        print("\nStep 3: Initializing model...")

        model = EquityTrendModel_v1(
            assets=['SPY', 'QQQ'],
            ma_period=200,
            momentum_period=120
        )

        print(f"  Model: {model}")

        # Step 4: Run backtest
        print("\nStep 4: Running backtest...")

        runner = BacktestRunner(str(config_path))

        results = runner.run(
            model=model,
            start_date="2023-06-01",
            end_date="2024-01-01"
        )

        print(f"  Backtest complete")
        print(f"  Bars simulated: {len(results['nav_series'])}")
        print(f"  Trades executed: {len(results['trade_log'])}")

        # Step 5: Verify results
        print("\nStep 5: Verifying results...")

        nav_series = results['nav_series']
        trade_log = results['trade_log']
        metrics = results['metrics']

        # Check NAV series
        assert len(nav_series) > 0, "NAV series is empty"
        assert nav_series.iloc[0] > 0, "Initial NAV is invalid"
        assert nav_series.iloc[-1] > 0, "Final NAV is invalid"

        # Check trades
        if len(trade_log) > 0:
            assert 'symbol' in trade_log.columns
            assert 'side' in trade_log.columns
            assert 'quantity' in trade_log.columns
            assert 'price' in trade_log.columns

            # Verify all symbols are from universe
            unique_symbols = trade_log['symbol'].unique()
            assert all(s in ['SPY', 'QQQ'] for s in unique_symbols), \
                f"Invalid symbols in trade log: {unique_symbols}"

        # Check metrics
        assert 'total_return' in metrics
        assert 'cagr' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'bps' in metrics

        # Verify metric ranges
        assert -1.0 <= metrics['total_return'] <= 10.0, \
            f"Total return out of range: {metrics['total_return']}"
        assert -10.0 <= metrics['sharpe_ratio'] <= 10.0, \
            f"Sharpe ratio out of range: {metrics['sharpe_ratio']}"

        print(f"  ✓ NAV series valid ({len(nav_series)} points)")
        print(f"  ✓ Trade log valid ({len(trade_log)} trades)")
        print(f"  ✓ Metrics valid")

        # Step 6: Test database persistence
        print("\nStep 6: Testing database persistence...")

        db_path = results_dir / 'test_results.duckdb'
        db = ResultsDatabase(str(db_path))

        run_id = "test_run_001"
        db.save_backtest_results(
            run_id=run_id,
            model_id=model.model_id,
            start_date="2023-06-01",
            end_date="2024-01-01",
            nav_series=nav_series,
            trade_log=trade_log,
            metrics=metrics,
            config=results['config']
        )

        # Retrieve and verify
        summary = db.get_backtest_summary(run_id)
        assert summary['run_id'] == run_id
        assert summary['model_id'] == model.model_id

        retrieved_nav = db.get_nav_series(run_id)
        assert len(retrieved_nav) == len(nav_series)

        retrieved_trades = db.get_trade_log(run_id)
        assert len(retrieved_trades) == len(trade_log)

        db.close()

        print(f"  ✓ Database persistence verified")

        # Print summary
        print("\n" + "=" * 70)
        print("BACKTEST SUMMARY")
        print("=" * 70)
        print(f"\nModel: {results['model_id']}")
        print(f"Period: {results['start_date']} to {results['end_date']}")
        print(f"\nPerformance:")
        print(f"  Initial NAV: ${metrics['initial_nav']:,.2f}")
        print(f"  Final NAV:   ${metrics['final_nav']:,.2f}")
        print(f"  Total Return: {metrics['total_return']:.2%}")
        print(f"  CAGR:        {metrics['cagr']:.2%}")
        print(f"  Sharpe:      {metrics['sharpe_ratio']:.2f}")
        print(f"  Max DD:      {metrics['max_drawdown']:.2%}")
        print(f"  BPS:         {metrics['bps']:.4f}")
        print(f"\nTrading:")
        print(f"  Total Trades: {metrics['total_trades']}")

        print("\n" + "=" * 70)
        print("✓ INTEGRATION TEST PASSED")
        print("=" * 70)

    def test_model_generates_valid_signals(self):
        """Test that model generates valid signals."""
        print("\n" + "=" * 70)
        print("INTEGRATION TEST: Model Signal Generation")
        print("=" * 70)

        from models.base import Context, RegimeState

        # Create sample data with clear trend
        dates = pd.date_range('2025-01-01', periods=300, freq='4H', tz='UTC')

        # SPY: Strong uptrend (price > MA, positive momentum)
        spy_data = pd.DataFrame({
            'close': 450 + np.arange(300) * 0.1,  # Uptrend
            'daily_ma_200': 440.0,
            'daily_momentum_120': 0.10  # +10% momentum
        }, index=dates)

        # QQQ: Downtrend (price < MA, negative momentum)
        qqq_data = pd.DataFrame({
            'close': 380 - np.arange(300) * 0.05,  # Downtrend
            'daily_ma_200': 390.0,
            'daily_momentum_120': -0.08  # -8% momentum
        }, index=dates)

        # Create context
        context = Context(
            timestamp=dates[-1],
            asset_features={
                'SPY': spy_data,
                'QQQ': qqq_data
            },
            regime=RegimeState(
                equity='BULL',
                volatility='NORMAL',
                crypto='NEUTRAL',
                macro='EXPANSION'
            ),
            model_budget_fraction=0.30,
            model_budget_value=Decimal('30000.00')
        )

        # Generate signals
        model = EquityTrendModel_v1()
        output = model.generate_target_weights(context)

        print(f"\nModel: {model.model_id}")
        print(f"Timestamp: {output.timestamp}")

        print("\nSignals:")
        for symbol, signal in output.metadata['signals'].items():
            weight = output.target_weights[symbol]
            print(f"  {symbol}: {'LONG' if signal else 'FLAT'} (weight: {weight:.2%})")

        # Verify signals
        assert output.target_weights['SPY'] > 0, "SPY should be LONG (uptrend)"
        assert output.target_weights['QQQ'] == 0, "QQQ should be FLAT (downtrend)"

        # Verify weights sum to <= 1.0 (relative to model budget)
        total_weight = sum(output.target_weights.values())
        assert 0 <= total_weight <= 1.0, \
            f"Total weight {total_weight} out of valid range [0, 1]"

        print("\n✓ Model generates valid signals")
        print("=" * 70)


def run_tests():
    """Run all integration tests."""
    print("=" * 70)
    print("INTEGRATION TESTS")
    print("=" * 70)

    test_suite = TestIntegration()

    # Create temp directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Test 1: Complete workflow
        print("\n" + "-" * 70)
        test_suite.test_complete_backtest_workflow(temp_dir)

        # Test 2: Model signals
        print("\n" + "-" * 70)
        test_suite.test_model_generates_valid_signals()

        print("\n" + "=" * 70)
        print("ALL INTEGRATION TESTS PASSED ✓")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
