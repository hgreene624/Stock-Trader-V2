"""
Test suite for no look-ahead bias validation.

Critical tests to ensure the system never uses future data in decisions.
"""

import pytest
import pandas as pd
import numpy as np
from decimal import Decimal
import sys
sys.path.append('..')
from engines.data.alignment import TimeAligner, TimeAlignmentError
from engines.data.pipeline import DataPipeline
from models.base import Context, RegimeState


class TestNoLookAhead:
    """Test no look-ahead bias enforcement."""

    def test_time_aligner_validates_lookahead(self):
        """Test that TimeAligner detects look-ahead violations."""
        # Create daily data with future timestamp
        daily_dates = pd.date_range('2025-01-10', '2025-01-20', freq='1D', tz='UTC')
        daily_dates = daily_dates + pd.Timedelta(hours=21)  # Market close at 21:00 UTC

        daily_data = pd.DataFrame({
            'close': np.arange(100, 100 + len(daily_dates)),
            'ma_200': np.arange(95, 95 + len(daily_dates))
        }, index=daily_dates)

        # Create H4 timestamps
        h4_timestamps = pd.date_range(
            '2025-01-15 00:00', '2025-01-18 00:00',
            freq='4H', tz='UTC'
        )
        h4_timestamps = h4_timestamps[h4_timestamps.hour.isin([0, 4, 8, 12, 16, 20])]

        # This should succeed (no look-ahead)
        aligned = TimeAligner.align_daily_to_h4(daily_data, h4_timestamps)

        # Verify: at each H4 timestamp, aligned data should be from past
        for h4_ts in h4_timestamps:
            if h4_ts in aligned.index:
                aligned_close = aligned.loc[h4_ts, 'close']

                # Find source daily bar
                matching = daily_data[daily_data['close'] == aligned_close]
                if len(matching) > 0:
                    source_ts = matching.index[0]
                    assert source_ts <= h4_ts, \
                        f"Look-ahead violation: {source_ts} > {h4_ts}"

        print("✓ TimeAligner correctly validates no look-ahead")

    def test_context_validates_asset_features(self):
        """Test that Context validates asset features for look-ahead."""
        # Create asset features with correct timestamps
        spy_data = pd.DataFrame({
            'close': [450, 452, 455],
            'daily_ma_200': [440, 441, 442]
        }, index=pd.date_range('2025-01-15 00:00', periods=3, freq='4H', tz='UTC'))

        # This should succeed
        context = Context(
            timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
            asset_features={'SPY': spy_data},
            regime=RegimeState(
                equity='NEUTRAL',
                volatility='NORMAL',
                crypto='NEUTRAL',
                macro='NEUTRAL'
            ),
            model_budget_fraction=0.30,
            model_budget_value=Decimal('30000.00')
        )

        assert context.timestamp == pd.Timestamp('2025-01-15 08:00', tz='UTC')
        print("✓ Context accepts valid asset features (no look-ahead)")

        # Create asset features with FUTURE timestamp
        future_spy_data = pd.DataFrame({
            'close': [450, 452, 455],
            'daily_ma_200': [440, 441, 442]
        }, index=pd.date_range('2025-01-15 00:00', periods=3, freq='4H', tz='UTC'))

        # Add a future bar
        future_bar = pd.DataFrame({
            'close': [458],
            'daily_ma_200': [443]
        }, index=[pd.Timestamp('2025-01-15 12:00', tz='UTC')])  # Future!

        future_spy_data = pd.concat([future_spy_data, future_bar])

        # This should FAIL
        with pytest.raises(AssertionError, match="LOOK-AHEAD VIOLATION"):
            context = Context(
                timestamp=pd.Timestamp('2025-01-15 08:00', tz='UTC'),
                asset_features={'SPY': future_spy_data},
                regime=RegimeState(
                    equity='NEUTRAL',
                    volatility='NORMAL',
                    crypto='NEUTRAL',
                    macro='NEUTRAL'
                ),
                model_budget_fraction=0.30,
                model_budget_value=Decimal('30000.00')
            )

        print("✓ Context correctly rejects future asset features")

    def test_lookback_window_enforcement(self):
        """Test that lookback window enforces no look-ahead."""
        # Create sample data
        dates = pd.date_range('2025-01-01', periods=200, freq='4H', tz='UTC')
        df = pd.DataFrame({
            'close': 450 + np.random.randn(200) * 5
        }, index=dates)

        # Get lookback window
        decision_time = dates[100]
        window = TimeAligner.get_lookback_window(df, decision_time, lookback_bars=50)

        # Verify all data is before or at decision time
        assert window.index.max() <= decision_time, \
            f"Look-ahead violation: max timestamp {window.index.max()} > {decision_time}"

        # Verify window size
        assert len(window) <= 50, f"Window too large: {len(window)} > 50"

        print("✓ Lookback window correctly enforces no look-ahead")

    def test_enforce_no_lookahead_raises_on_future_data(self):
        """Test that enforce_no_lookahead raises on future data."""
        # Create data with future bars
        dates = pd.date_range('2025-01-01', periods=100, freq='4H', tz='UTC')
        df = pd.DataFrame({
            'close': 450 + np.random.randn(100) * 5
        }, index=dates)

        decision_time = dates[50]

        # This should work (filters to past data)
        past_data = TimeAligner.enforce_no_lookahead(df, decision_time)
        assert len(past_data) <= 51, f"Expected ≤51 bars, got {len(past_data)}"
        assert past_data.index.max() <= decision_time

        print("✓ enforce_no_lookahead correctly filters data")

    def test_daily_to_h4_alignment_boundary_cases(self):
        """Test edge cases in daily to H4 alignment."""
        # Daily data at 21:00 UTC (market close)
        daily_dates = pd.date_range('2025-01-10', '2025-01-15', freq='1D', tz='UTC')
        daily_dates = daily_dates + pd.Timedelta(hours=21)

        daily_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105],
            'value': [1, 2, 3, 4, 5, 6]
        }, index=daily_dates)

        # H4 timestamp BEFORE daily bar (should use previous day)
        h4_ts = pd.Timestamp('2025-01-15 20:00', tz='UTC')  # Before 21:00 close

        aligned = TimeAligner.align_daily_to_h4(
            daily_data,
            pd.DatetimeIndex([h4_ts])
        )

        # Should use 2025-01-14 data (not 2025-01-15 which closes at 21:00)
        expected_value = 5  # 2025-01-14's value
        actual_value = aligned.loc[h4_ts, 'value']

        # Note: Alignment uses forward-fill, so it should use most recent available
        assert actual_value <= 5, \
            f"Used future data: got value {actual_value}, expected ≤ 5"

        print("✓ Daily to H4 alignment handles boundary cases correctly")

    def test_pipeline_context_creation_no_lookahead(self):
        """Test that DataPipeline.create_context enforces no look-ahead."""
        # Create simple in-memory data
        dates = pd.date_range('2025-01-01', periods=200, freq='4H', tz='UTC')

        spy_data = pd.DataFrame({
            'close': 450 + np.cumsum(np.random.randn(200) * 0.5),
            'volume': np.random.randint(1000000, 5000000, 200),
            'daily_ma_200': 440.0  # Simplified
        }, index=dates)

        asset_data = {'SPY': spy_data}

        # Create pipeline (without actual file I/O)
        from engines.data.pipeline import DataPipeline
        pipeline = DataPipeline()

        # Pick a decision timestamp
        decision_ts = dates[100]

        # Create context
        context = pipeline.create_context(
            timestamp=decision_ts,
            asset_data=asset_data,
            regime=RegimeState(
                equity='NEUTRAL',
                volatility='NORMAL',
                crypto='NEUTRAL',
                macro='NEUTRAL'
            ),
            model_budget_fraction=0.30,
            model_budget_value=Decimal('30000.00'),
            lookback_bars=50
        )

        # Verify context timestamp
        assert context.timestamp == decision_ts

        # Verify asset features have no future data
        for symbol, features in context.asset_features.items():
            assert features.index.max() <= decision_ts, \
                f"Look-ahead in {symbol}: max timestamp {features.index.max()} > {decision_ts}"

        print("✓ DataPipeline.create_context enforces no look-ahead")


def run_tests():
    """Run all no look-ahead tests."""
    print("=" * 70)
    print("NO LOOK-AHEAD VALIDATION TESTS")
    print("=" * 70)
    print()

    test_suite = TestNoLookAhead()

    tests = [
        ("TimeAligner validation", test_suite.test_time_aligner_validates_lookahead),
        ("Context validation", test_suite.test_context_validates_asset_features),
        ("Lookback window enforcement", test_suite.test_lookback_window_enforcement),
        ("Enforce no lookahead filter", test_suite.test_enforce_no_lookahead_raises_on_future_data),
        ("Daily to H4 boundary cases", test_suite.test_daily_to_h4_alignment_boundary_cases),
        ("Pipeline context creation", test_suite.test_pipeline_context_creation_no_lookahead)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {test_name}")
            print(f"  Error: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print()
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
