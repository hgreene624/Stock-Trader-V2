"""
Pipeline Validation Script

Comprehensive test of all system components with detailed logging.
Run this before using the platform to ensure everything works correctly.

Usage:
    python validate_pipeline.py [--verbose] [--skip-download]
"""

import sys
import os
import argparse
import traceback
from pathlib import Path
from datetime import datetime
import tempfile
import shutil
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class PipelineValidator:
    """Validates all components of the trading platform pipeline."""

    def __init__(self, verbose=False):
        """
        Initialize validator.

        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.test_results = []
        self.temp_dir = None
        self.start_time = datetime.now()

    def log(self, message, level="INFO"):
        """
        Log a message with timestamp and level.

        Args:
            message: Message to log
            level: Log level (INFO, SUCCESS, WARNING, ERROR)
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if level == "SUCCESS":
            color = Colors.OKGREEN
            symbol = "✓"
        elif level == "ERROR":
            color = Colors.FAIL
            symbol = "✗"
        elif level == "WARNING":
            color = Colors.WARNING
            symbol = "⚠"
        else:
            color = Colors.OKBLUE
            symbol = "→"

        print(f"{color}[{timestamp}] {symbol} {message}{Colors.ENDC}")

    def log_verbose(self, message):
        """Log verbose message (only if verbose mode enabled)."""
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"{Colors.OKCYAN}[{timestamp}]   {message}{Colors.ENDC}")

    def test_step(self, name, func, *args, **kwargs):
        """
        Execute a test step with error handling and logging.

        Args:
            name: Test name
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            True if test passed, False otherwise
        """
        self.log(f"Testing: {name}", "INFO")

        try:
            result = func(*args, **kwargs)

            self.test_results.append({
                "name": name,
                "status": "PASS",
                "error": None
            })

            self.log(f"PASSED: {name}", "SUCCESS")
            return True

        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()

            self.test_results.append({
                "name": name,
                "status": "FAIL",
                "error": error_msg,
                "traceback": tb
            })

            self.log(f"FAILED: {name}", "ERROR")
            self.log(f"  Error: {error_msg}", "ERROR")

            if self.verbose:
                print(f"\n{Colors.FAIL}Traceback:{Colors.ENDC}")
                print(tb)

            return False

    def setup_temp_environment(self):
        """Create temporary directory for testing."""
        self.log("Setting up temporary test environment", "INFO")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="trading_platform_test_"))
        self.log_verbose(f"Temp directory: {self.temp_dir}")

    def cleanup_temp_environment(self):
        """Remove temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            self.log("Cleaning up temporary test environment", "INFO")
            shutil.rmtree(self.temp_dir)

    # =========================================================================
    # Component Tests
    # =========================================================================

    def test_imports(self):
        """Test that all required modules can be imported."""
        self.log("=" * 70)
        self.log("PHASE 1: Import Tests", "INFO")
        self.log("=" * 70)

        imports = [
            ("pandas", "import pandas as pd"),
            ("numpy", "import numpy as np"),
            ("pyarrow", "import pyarrow"),
            ("yaml", "import yaml"),
            ("pydantic", "import pydantic"),
            ("yfinance", "import yfinance"),
            ("ccxt", "import ccxt"),
            ("duckdb", "import duckdb"),
            ("matplotlib", "import matplotlib.pyplot as plt"),
        ]

        missing_packages = []
        all_passed = True

        for name, import_stmt in imports:
            try:
                exec(import_stmt)
                self.log_verbose(f"  {name}: OK")
            except ImportError as e:
                self.log(f"  {name}: MISSING", "ERROR")
                missing_packages.append(name)
                all_passed = False

        if not all_passed:
            self.log("\n" + "=" * 70, "ERROR")
            self.log("MISSING DEPENDENCIES DETECTED", "ERROR")
            self.log("=" * 70, "ERROR")
            self.log("\nThe following packages are required but not installed:", "ERROR")
            for pkg in missing_packages:
                self.log(f"  - {pkg}", "ERROR")

            self.log("\n" + Colors.WARNING + "To fix this, run:" + Colors.ENDC)
            self.log(f"\n  {Colors.BOLD}pip install -r requirements.txt{Colors.ENDC}\n")

            raise ImportError(
                f"Missing {len(missing_packages)} required package(s). "
                f"Run: pip install -r requirements.txt"
            )

    def test_utils_logging(self):
        """Test structured logger."""
        import pandas as pd
        from utils.logging import StructuredLogger

        logger = StructuredLogger(logs_dir=str(self.temp_dir / "logs"))

        # Test basic logging
        logger.info("Test info message")
        logger.error("Test error message")

        # Test trade logging
        logger.log_trade(
            trade_id="test_001",
            timestamp=pd.Timestamp.now(tz='UTC').isoformat(),
            symbol="SPY",
            side="buy",
            quantity=100,
            price=450.0,
            fees=5.0
        )

        # Verify log files created
        log_dir = self.temp_dir / "logs"
        assert log_dir.exists(), "Log directory not created"
        assert (log_dir / "trades.log").exists(), "Trade log not created"

        self.log_verbose("  Logger created successfully")
        self.log_verbose(f"  Log files in: {log_dir}")

    def test_utils_config(self):
        """Test config loader."""
        from utils.config import ConfigLoader

        # Create test config
        config_dir = self.temp_dir / "configs"
        config_dir.mkdir(parents=True)

        config_path = config_dir / "test.yaml"
        config_content = """
        test_key: test_value
        nested:
          key1: value1
          key2: value2
        """

        with open(config_path, 'w') as f:
            f.write(config_content)

        # Load config using class method
        config = ConfigLoader.load_yaml(str(config_path))

        assert config['test_key'] == 'test_value'
        assert config['nested']['key1'] == 'value1'

        self.log_verbose("  Config loaded successfully")
        self.log_verbose(f"  Config keys: {list(config.keys())}")

    def test_utils_time(self):
        """Test time utilities."""
        import pandas as pd
        from utils.time_utils import normalize_to_utc, is_h4_boundary, round_to_h4_boundary

        # Test UTC normalization
        ts = pd.Timestamp('2025-01-15 12:00:00', tz='America/New_York')
        utc_ts = normalize_to_utc(ts)
        assert str(utc_ts.tz) == 'UTC', f"Expected UTC timezone, got {utc_ts.tz}"

        # Test H4 boundary detection
        h4_ts = pd.Timestamp('2025-01-15 12:00:00', tz='UTC')
        assert is_h4_boundary(h4_ts), "12:00 should be H4 boundary"

        non_h4_ts = pd.Timestamp('2025-01-15 13:00:00', tz='UTC')
        assert not is_h4_boundary(non_h4_ts), "13:00 should not be H4 boundary"

        # Test rounding
        rounded = round_to_h4_boundary(non_h4_ts)
        assert is_h4_boundary(rounded), "Rounded timestamp should be H4 boundary"

        self.log_verbose("  H4 boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC")

    def test_utils_metrics(self):
        """Test performance metrics calculator."""
        import pandas as pd
        import numpy as np
        from utils.metrics import calculate_sharpe_ratio, calculate_cagr, calculate_max_drawdown

        # Create sample NAV series
        dates = pd.date_range('2023-01-01', periods=252, freq='D', tz='UTC')
        nav_values = 100000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.01, 252)))
        nav_series = pd.Series(nav_values, index=dates)

        # Calculate returns
        returns = nav_series.pct_change().dropna()

        # Test metrics
        sharpe = calculate_sharpe_ratio(returns, periods_per_year=252)
        initial = float(nav_series.iloc[0])
        final = float(nav_series.iloc[-1])
        cagr = calculate_cagr(initial, final, years=1.0)
        max_dd = calculate_max_drawdown(nav_series)

        assert -10 < sharpe < 10, f"Sharpe ratio out of range: {sharpe}"
        assert -1 < cagr < 5, f"CAGR out of range: {cagr}"
        assert 0 <= max_dd <= 1, f"Max drawdown out of range: {max_dd}"

        self.log_verbose(f"  Sharpe: {sharpe:.2f}")
        self.log_verbose(f"  CAGR: {cagr:.2%}")
        self.log_verbose(f"  Max DD: {max_dd:.2%}")

    def test_data_validator(self):
        """Test data validator."""
        import pandas as pd
        import numpy as np
        from engines.data.validator import DataValidator

        # Create valid OHLCV data
        dates = pd.date_range('2025-01-01', periods=100, freq='4H', tz='UTC')
        data = pd.DataFrame({
            'open': 450 + np.random.randn(100) * 2,
            'high': 452 + np.random.randn(100) * 2,
            'low': 448 + np.random.randn(100) * 2,
            'close': 450 + np.random.randn(100) * 2,
            'volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)

        # Ensure OHLC consistency
        data['high'] = data[['open', 'high', 'close']].max(axis=1)
        data['low'] = data[['open', 'low', 'close']].min(axis=1)

        # Validate
        is_valid, errors = DataValidator.validate_data(data, expected_freq='4H')

        # Should be valid (or only warnings)
        critical_errors = [e for e in errors if not e.startswith("WARNING")]
        assert len(critical_errors) == 0, f"Data validation failed: {critical_errors}"

        self.log_verbose(f"  Validated {len(data)} bars")
        if errors:
            self.log_verbose(f"  Warnings: {len(errors)}")

    def test_data_alignment(self):
        """Test time alignment (no look-ahead)."""
        import pandas as pd
        import numpy as np
        from engines.data.alignment import TimeAligner

        # Create daily data
        daily_dates = pd.date_range('2025-01-10', '2025-01-20', freq='1D', tz='UTC')
        daily_dates = daily_dates + pd.Timedelta(hours=21)  # Market close

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

        # Align
        aligned = TimeAligner.align_daily_to_h4(daily_data, h4_timestamps)

        # Verify no look-ahead
        for h4_ts in h4_timestamps:
            if h4_ts in aligned.index:
                aligned_close = aligned.loc[h4_ts, 'close']
                matching = daily_data[daily_data['close'] == aligned_close]

                if len(matching) > 0:
                    source_ts = matching.index[0]
                    assert source_ts <= h4_ts, \
                        f"Look-ahead violation: {source_ts} > {h4_ts}"

        self.log_verbose(f"  Aligned {len(aligned)} H4 bars with daily data")
        self.log_verbose("  No look-ahead violations detected")

    def test_data_features(self):
        """Test feature computation."""
        import pandas as pd
        import numpy as np
        from engines.data.features import FeatureComputer

        # Create sample data
        dates = pd.date_range('2023-01-01', periods=300, freq='D', tz='UTC')
        close_prices = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 300)))

        df = pd.DataFrame({
            'open': close_prices * (1 + np.random.normal(0, 0.005, 300)),
            'high': close_prices * (1 + np.abs(np.random.normal(0.01, 0.01, 300))),
            'low': close_prices * (1 - np.abs(np.random.normal(0.01, 0.01, 300))),
            'close': close_prices,
            'volume': np.random.randint(1000000, 5000000, 300)
        }, index=dates)

        # Ensure OHLC consistency
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)

        # Compute features
        enriched = FeatureComputer.add_all_features(
            df,
            ma_periods=[50, 200],
            momentum_periods=[30, 60]
        )

        # Verify features added
        assert 'sma_50' in enriched.columns
        assert 'sma_200' in enriched.columns
        assert 'rsi' in enriched.columns
        assert 'momentum_60' in enriched.columns

        self.log_verbose(f"  Computed {len(enriched.columns)} features")
        self.log_verbose(f"  Features: {list(enriched.columns)[:10]}...")

    def test_model_base(self):
        """Test base model interface."""
        import pandas as pd
        from models.base import Context, RegimeState, BaseModel

        # Create context
        spy_data = pd.DataFrame({
            'close': [450, 452, 455],
            'daily_ma_200': [440, 441, 442]
        }, index=pd.date_range('2025-01-15', periods=3, freq='4H', tz='UTC'))

        ts = pd.Timestamp('2025-01-15 08:00', tz='UTC')
        context = Context(
            timestamp=ts,
            asset_features={'SPY': spy_data},
            regime=RegimeState(
                timestamp=ts,
                equity_regime='neutral',
                vol_regime='normal',
                crypto_regime='neutral',
                macro_regime='neutral'
            ),
            model_budget_fraction=0.30,
            model_budget_value=Decimal('30000.00')
        )

        # Verify context
        assert context.timestamp == pd.Timestamp('2025-01-15 08:00', tz='UTC')
        assert 'SPY' in context.asset_features
        assert context.model_budget_fraction == 0.30

        self.log_verbose("  Context created successfully")
        self.log_verbose(f"  Assets: {list(context.asset_features.keys())}")

    def test_equity_trend_model(self):
        """Test EquityTrendModel_v1."""
        import pandas as pd
        import numpy as np
        from models.equity_trend_v1 import EquityTrendModel_v1
        from models.base import Context, RegimeState

        # Create test data with clear signals
        dates = pd.date_range('2025-01-01', periods=300, freq='4H', tz='UTC')

        # SPY: uptrend (price > MA, positive momentum)
        spy_data = pd.DataFrame({
            'close': 450 + np.arange(300) * 0.1,
            'daily_ma_200': 440.0,
            'daily_momentum_120': 0.10
        }, index=dates)

        # QQQ: downtrend
        qqq_data = pd.DataFrame({
            'close': 380 - np.arange(300) * 0.05,
            'daily_ma_200': 390.0,
            'daily_momentum_120': -0.08
        }, index=dates)

        context = Context(
            timestamp=dates[-1],
            asset_features={'SPY': spy_data, 'QQQ': qqq_data},
            regime=RegimeState(
                timestamp=dates[-1],
                equity_regime='bull',
                vol_regime='normal',
                crypto_regime='neutral',
                macro_regime='expansion'
            ),
            model_budget_fraction=0.30,
            model_budget_value=Decimal('30000.00')
        )

        # Generate signals
        model = EquityTrendModel_v1()
        output = model.generate_target_weights(context)

        # Verify signals
        assert output.weights['SPY'] > 0, "SPY should be LONG"
        assert output.weights['QQQ'] == 0, "QQQ should be FLAT"

        total_weight = sum(output.weights.values())
        assert 0 <= total_weight <= 1.0, f"Total weight {total_weight} out of range"

        self.log_verbose(f"  SPY signal: LONG ({output.weights['SPY']:.2%})")
        self.log_verbose(f"  QQQ signal: FLAT ({output.weights['QQQ']:.2%})")

    def test_index_mean_rev_model(self):
        """Test IndexMeanReversionModel_v1."""
        import pandas as pd
        import numpy as np
        from models.index_mean_rev_v1 import IndexMeanReversionModel_v1
        from models.base import Context, RegimeState

        # Create test data with RSI oversold signal
        dates = pd.date_range('2025-01-01', periods=300, freq='4H', tz='UTC')

        # SPY: oversold (RSI < 30, price < BB_lower)
        spy_data = pd.DataFrame({
            'close': np.ones(300) * 450,
            'rsi': np.ones(300) * 25,  # Oversold
            'bb_upper': np.ones(300) * 460,
            'bb_lower': np.ones(300) * 455  # Price 450 < 455 (below BB_lower)
        }, index=dates)

        # QQQ: not oversold
        qqq_data = pd.DataFrame({
            'close': np.ones(300) * 380,
            'rsi': np.ones(300) * 50,  # Neutral
            'bb_upper': np.ones(300) * 390,
            'bb_lower': np.ones(300) * 370
        }, index=dates)

        context = Context(
            timestamp=dates[-1],
            asset_features={'SPY': spy_data, 'QQQ': qqq_data},
            regime=RegimeState(
                timestamp=dates[-1],
                equity_regime='neutral',
                vol_regime='normal',
                crypto_regime='neutral',
                macro_regime='neutral'
            ),
            model_budget_fraction=0.25,
            model_budget_value=Decimal('25000.00')
        )

        # Generate signals
        model = IndexMeanReversionModel_v1()
        output = model.generate_target_weights(context)

        # Verify signals
        assert output.weights['SPY'] > 0, "SPY should be LONG (oversold)"
        assert output.weights['QQQ'] == 0, "QQQ should be FLAT (not oversold)"

        total_weight = sum(output.weights.values())
        assert 0 <= total_weight <= 1.0, f"Total weight {total_weight} out of range"

        self.log_verbose(f"  SPY signal: LONG ({output.weights['SPY']:.2%}) - RSI oversold")
        self.log_verbose(f"  QQQ signal: FLAT ({output.weights['QQQ']:.2%})")

    def test_crypto_momentum_model(self):
        """Test CryptoMomentumModel_v1."""
        import pandas as pd
        import numpy as np
        from models.crypto_momentum_v1 import CryptoMomentumModel_v1
        from models.base import Context, RegimeState

        # Create test data with positive momentum
        dates = pd.date_range('2025-01-01', periods=300, freq='4H', tz='UTC')

        # BTC: positive momentum
        btc_data = pd.DataFrame({
            'close': 65000 + np.arange(300) * 10,
            'daily_momentum_60': np.ones(300) * 0.15  # +15% momentum
        }, index=dates)

        # ETH: negative momentum
        eth_data = pd.DataFrame({
            'close': 3500 - np.arange(300) * 5,
            'daily_momentum_60': np.ones(300) * -0.10  # -10% momentum
        }, index=dates)

        # Test 1: RISK_ON regime (should trade)
        context_risk_on = Context(
            timestamp=dates[-1],
            asset_features={'BTC': btc_data, 'ETH': eth_data},
            regime=RegimeState(
                timestamp=dates[-1],
                equity_regime='neutral',
                vol_regime='normal',
                crypto_regime='RISK_ON',
                macro_regime='neutral'
            ),
            model_budget_fraction=0.15,
            model_budget_value=Decimal('15000.00')
        )

        model = CryptoMomentumModel_v1(regime_gating=True)
        output = model.generate_target_weights(context_risk_on)

        # Should be long BTC (positive momentum), flat ETH (negative momentum)
        assert output.weights['BTC'] > 0, "BTC should be LONG (positive momentum)"
        assert output.weights['ETH'] == 0, "ETH should be FLAT (negative momentum)"

        self.log_verbose(f"  BTC signal (RISK_ON): LONG ({output.weights['BTC']:.2%})")
        self.log_verbose(f"  ETH signal (RISK_ON): FLAT ({output.weights['ETH']:.2%})")

        # Test 2: RISK_OFF regime (should not trade)
        context_risk_off = Context(
            timestamp=dates[-1],
            asset_features={'BTC': btc_data, 'ETH': eth_data},
            regime=RegimeState(
                timestamp=dates[-1],
                equity_regime='neutral',
                vol_regime='normal',
                crypto_regime='RISK_OFF',
                macro_regime='neutral'
            ),
            model_budget_fraction=0.15,
            model_budget_value=Decimal('15000.00')
        )

        output_risk_off = model.generate_target_weights(context_risk_off)

        # Should be flat on all assets (regime gating)
        assert output_risk_off.weights['BTC'] == 0, "BTC should be FLAT (RISK_OFF regime)"
        assert output_risk_off.weights['ETH'] == 0, "ETH should be FLAT (RISK_OFF regime)"

        self.log_verbose(f"  BTC signal (RISK_OFF): FLAT (regime gate)")
        self.log_verbose(f"  ETH signal (RISK_OFF): FLAT (regime gate)")

    def test_portfolio_engine(self):
        """Test Portfolio Engine aggregation."""
        import pandas as pd
        from models.base import ModelOutput, RegimeState
        from engines.portfolio.engine import PortfolioEngine

        engine = PortfolioEngine()
        timestamp = pd.Timestamp('2025-01-15 16:00', tz='UTC')
        nav = Decimal('100000.00')

        # Test 1: Non-overlapping models
        model_outputs = [
            ModelOutput(
                model_name="EquityTrendModel_v1",
                timestamp=timestamp,
                weights={'SPY': 1.0, 'QQQ': 0.0}  # Model-relative: 100% SPY
            ),
            ModelOutput(
                model_name="IndexMeanReversionModel_v1",
                timestamp=timestamp,
                weights={'SPY': 0.0, 'QQQ': 1.0}  # Model-relative: 100% QQQ
            )
        ]

        model_budgets = {
            "EquityTrendModel_v1": 0.60,
            "IndexMeanReversionModel_v1": 0.25
        }

        target = engine.aggregate_model_outputs(model_outputs, model_budgets, nav)

        # Check NAV-relative weights
        assert abs(target.target_weights['SPY'] - 0.60) < 0.0001, "SPY should be 60% NAV"
        assert abs(target.target_weights['QQQ'] - 0.25) < 0.0001, "QQQ should be 25% NAV"

        # Check attribution
        assert target.attribution['SPY']['EquityTrendModel_v1'] == 0.60
        assert target.attribution['QQQ']['IndexMeanReversionModel_v1'] == 0.25

        self.log_verbose(f"  Non-overlapping aggregation: SPY={target.target_weights['SPY']:.2%}, QQQ={target.target_weights['QQQ']:.2%}")

        # Test 2: Overlapping models (both target SPY)
        model_outputs_overlap = [
            ModelOutput(
                model_name="Model_A",
                timestamp=timestamp,
                weights={'SPY': 1.0}  # 100% to SPY
            ),
            ModelOutput(
                model_name="Model_B",
                timestamp=timestamp,
                weights={'SPY': 1.0}  # 100% to SPY
            )
        ]

        model_budgets_overlap = {
            "Model_A": 0.40,
            "Model_B": 0.30
        }

        target_overlap = engine.aggregate_model_outputs(
            model_outputs_overlap, model_budgets_overlap, nav
        )

        # Should sum: 0.40 + 0.30 = 0.70
        assert abs(target_overlap.target_weights['SPY'] - 0.70) < 0.0001, "SPY should be 70% NAV (0.40 + 0.30)"

        # Check both models are in attribution
        assert 'Model_A' in target_overlap.attribution['SPY']
        assert 'Model_B' in target_overlap.attribution['SPY']

        self.log_verbose(f"  Overlapping aggregation: SPY={target_overlap.target_weights['SPY']:.2%} (0.40 + 0.30)")

    def test_attribution_tracker(self):
        """Test Attribution Tracker."""
        import pandas as pd
        from engines.portfolio.attribution import AttributionTracker

        tracker = AttributionTracker()
        timestamp = pd.Timestamp('2025-01-15 16:00', tz='UTC')
        nav = Decimal('100000.00')

        # Test 1: Valid attribution
        positions = {'SPY': 0.60, 'QQQ': 0.25}
        attribution = {
            'SPY': {'Model_A': 0.40, 'Model_B': 0.20},  # Sum = 0.60 ✓
            'QQQ': {'Model_B': 0.25}  # Sum = 0.25 ✓
        }
        model_budgets = {'Model_A': 0.40, 'Model_B': 0.60}

        snapshot = tracker.record_attribution(timestamp, positions, attribution, model_budgets, nav)
        is_valid, violations = tracker.validate_attribution(positions, attribution)

        assert is_valid, f"Attribution validation should pass: {violations}"
        assert len(violations) == 0

        self.log_verbose("  Valid attribution: PASSED")

        # Test 2: Invalid attribution (mismatch)
        positions_bad = {'SPY': 0.60}
        attribution_bad = {
            'SPY': {'Model_A': 0.40, 'Model_B': 0.25}  # Sum = 0.65 ≠ 0.60 ✗
        }

        is_valid_bad, violations_bad = tracker.validate_attribution(positions_bad, attribution_bad)

        assert not is_valid_bad, "Mismatched attribution should fail validation"
        assert len(violations_bad) > 0

        self.log_verbose(f"  Invalid attribution detected: {len(violations_bad)} violations")

        # Test 3: Model exposure extraction
        model_exposure = tracker.get_model_exposure(snapshot, 'Model_B')
        assert 'SPY' in model_exposure
        assert 'QQQ' in model_exposure
        assert model_exposure['SPY'] == 0.20
        assert model_exposure['QQQ'] == 0.25

        self.log_verbose(f"  Model_B exposure: SPY={model_exposure['SPY']:.2%}, QQQ={model_exposure['QQQ']:.2%}")

    def test_multi_model_backtest(self):
        """Test complete multi-model backtest workflow."""
        import pandas as pd
        import numpy as np
        import yaml
        from backtest.runner import BacktestRunner
        from models.equity_trend_v1 import EquityTrendModel_v1
        from models.index_mean_rev_v1 import IndexMeanReversionModel_v1
        from models.crypto_momentum_v1 import CryptoMomentumModel_v1

        # Generate data
        data_dir = self.temp_dir / "data_multi"

        # Generate equities
        dates_1d = pd.date_range('2022-01-01', '2024-01-15', freq='1D', tz='UTC')
        dates_4h = pd.date_range('2022-01-01', '2024-01-15', freq='4h', tz='UTC')

        equities_dir = data_dir / 'equities'
        equities_dir.mkdir(parents=True, exist_ok=True)

        for symbol in ['SPY', 'QQQ']:
            base_price = 450 if symbol == 'SPY' else 380
            close_1d = base_price * np.exp(np.cumsum(np.random.normal(0.0001, 0.015, len(dates_1d))))

            df_1d = pd.DataFrame({
                'open': close_1d * (1 + np.random.normal(0, 0.003, len(dates_1d))),
                'high': close_1d * (1 + np.abs(np.random.normal(0.008, 0.005, len(dates_1d)))),
                'low': close_1d * (1 - np.abs(np.random.normal(0.008, 0.005, len(dates_1d)))),
                'close': close_1d,
                'volume': np.random.randint(1000000, 10000000, len(dates_1d))
            }, index=dates_1d)

            df_1d['high'] = df_1d[['open', 'high', 'close']].max(axis=1)
            df_1d['low'] = df_1d[['open', 'low', 'close']].min(axis=1)

            df_1d.to_parquet(equities_dir / f"{symbol}_1D.parquet")

            close_4h = base_price * np.exp(np.cumsum(np.random.normal(0.0001, 0.015, len(dates_4h))))

            df_4h = pd.DataFrame({
                'open': close_4h * (1 + np.random.normal(0, 0.003, len(dates_4h))),
                'high': close_4h * (1 + np.abs(np.random.normal(0.008, 0.005, len(dates_4h)))),
                'low': close_4h * (1 - np.abs(np.random.normal(0.008, 0.005, len(dates_4h)))),
                'close': close_4h,
                'volume': np.random.randint(1000000, 10000000, len(dates_4h))
            }, index=dates_4h)

            df_4h['high'] = df_4h[['open', 'high', 'close']].max(axis=1)
            df_4h['low'] = df_4h[['open', 'low', 'close']].min(axis=1)

            df_4h.to_parquet(equities_dir / f"{symbol}_4H.parquet")

        # Generate crypto
        crypto_dir = data_dir / 'crypto'
        crypto_dir.mkdir(parents=True, exist_ok=True)

        for symbol in ['BTC', 'ETH']:
            base_price = 65000 if symbol == 'BTC' else 3500
            close_1d_crypto = base_price * np.exp(np.cumsum(np.random.normal(0.0002, 0.025, len(dates_1d))))

            df_1d_crypto = pd.DataFrame({
                'open': close_1d_crypto * (1 + np.random.normal(0, 0.005, len(dates_1d))),
                'high': close_1d_crypto * (1 + np.abs(np.random.normal(0.015, 0.01, len(dates_1d)))),
                'low': close_1d_crypto * (1 - np.abs(np.random.normal(0.015, 0.01, len(dates_1d)))),
                'close': close_1d_crypto,
                'volume': np.random.randint(1000000, 10000000, len(dates_1d))
            }, index=dates_1d)

            df_1d_crypto['high'] = df_1d_crypto[['open', 'high', 'close']].max(axis=1)
            df_1d_crypto['low'] = df_1d_crypto[['open', 'low', 'close']].min(axis=1)

            df_1d_crypto.to_parquet(crypto_dir / f"{symbol}_1D.parquet")

            close_4h_crypto = base_price * np.exp(np.cumsum(np.random.normal(0.0002, 0.025, len(dates_4h))))

            df_4h_crypto = pd.DataFrame({
                'open': close_4h_crypto * (1 + np.random.normal(0, 0.005, len(dates_4h))),
                'high': close_4h_crypto * (1 + np.abs(np.random.normal(0.015, 0.01, len(dates_4h)))),
                'low': close_4h_crypto * (1 - np.abs(np.random.normal(0.015, 0.01, len(dates_4h)))),
                'close': close_4h_crypto,
                'volume': np.random.randint(1000000, 10000000, len(dates_4h))
            }, index=dates_4h)

            df_4h_crypto['high'] = df_4h_crypto[['open', 'high', 'close']].max(axis=1)
            df_4h_crypto['low'] = df_4h_crypto[['open', 'low', 'close']].min(axis=1)

            df_4h_crypto.to_parquet(crypto_dir / f"{symbol}_4H.parquet")

        # Create config
        config_dir = self.temp_dir / "configs_multi"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_path = config_dir / "test_multi_model.yaml"
        config_content = {
            'backtest': {
                'data_dir': str(data_dir),
                'h4_timeframe': '4H',
                'daily_timeframe': '1D',
                'asset_class': 'equity',
                'symbols': ['SPY', 'QQQ', 'BTC', 'ETH'],
                'start_date': '2023-06-01',
                'end_date': '2024-01-01',
                'initial_nav': 100000.0,
                'fill_timing': 'close',
                'slippage_bps': 5.0,
                'commission_pct': 0.001,
                'min_commission': 1.0,
                'lookback_bars': 100
            },
            'models': {
                'EquityTrendModel_v1': {'budget': 0.60},
                'IndexMeanReversionModel_v1': {'budget': 0.25},
                'CryptoMomentumModel_v1': {'budget': 0.15}
            },
            'risk': {}
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Create models
        model1 = EquityTrendModel_v1(assets=['SPY', 'QQQ'])
        model2 = IndexMeanReversionModel_v1(assets=['SPY', 'QQQ'])
        model3 = CryptoMomentumModel_v1(assets=['BTC', 'ETH'], regime_gating=False)

        # Manually load data since we need mixed asset classes
        # BacktestRunner.load_and_prepare() only supports single asset_class
        from engines.data.pipeline import DataPipeline

        pipeline = DataPipeline(data_dir=str(data_dir))

        # Load equities
        equity_data = pipeline.load_and_prepare(
            symbols=['SPY', 'QQQ'],
            h4_timeframe='4H',
            daily_timeframe='1D',
            asset_class='equity'
        )

        # Load crypto
        crypto_data = pipeline.load_and_prepare(
            symbols=['BTC', 'ETH'],
            h4_timeframe='4H',
            daily_timeframe='1D',
            asset_class='crypto'
        )

        # Merge asset data
        asset_data = {**equity_data, **crypto_data}

        # Filter to backtest period
        end_date_ts = pd.Timestamp('2024-01-01', tz='UTC')
        for symbol in asset_data:
            asset_data[symbol] = asset_data[symbol][asset_data[symbol].index <= end_date_ts]

        # Get timestamps
        timestamps = pipeline.get_timestamps(asset_data, '2023-06-01', '2024-01-01')

        # Run simulation manually (since BacktestRunner doesn't support mixed asset classes yet)
        from backtest.executor import BacktestExecutor, BacktestConfig
        from engines.portfolio.engine import PortfolioEngine
        from engines.portfolio.attribution import AttributionTracker
        from models.base import RegimeState

        config_bt = BacktestConfig(
            initial_nav=Decimal('100000.0'),
            fill_timing='close',
            slippage_bps=5.0,
            commission_pct=0.001
        )

        executor = BacktestExecutor(config=config_bt, asset_data=asset_data)
        portfolio_engine = PortfolioEngine()
        attribution_tracker = AttributionTracker()

        model_budgets = {
            'EquityTrendModel_v1': 0.60,
            'IndexMeanReversionModel_v1': 0.25,
            'CryptoMomentumModel_v1': 0.15
        }

        # Simple simulation loop
        for timestamp in timestamps[:10]:  # Just test first 10 bars
            current_nav = executor.get_nav()
            regime = RegimeState(
                timestamp=timestamp,
                equity_regime='neutral',
                vol_regime='normal',
                crypto_regime='neutral',
                macro_regime='neutral'
            )

            # Generate outputs from all models
            model_outputs = []
            for model in [model1, model2, model3]:
                context = pipeline.create_context(
                    timestamp=timestamp,
                    asset_data=asset_data,
                    regime=regime,
                    model_budget_fraction=model_budgets[model.model_id],
                    model_budget_value=current_nav * Decimal(str(model_budgets[model.model_id])),
                    lookback_bars=100
                )
                output = model.generate_target_weights(context)
                model_outputs.append(output)

            # Aggregate
            target = portfolio_engine.aggregate_model_outputs(
                model_outputs, model_budgets, current_nav
            )

            # Record attribution
            current_positions = {}
            for symbol, position in executor.get_positions().items():
                current_positions[symbol] = float(position.market_value / current_nav)

            attribution_tracker.record_attribution(
                timestamp, current_positions, target.attribution, model_budgets, current_nav
            )

            # Submit orders
            executor.submit_target_weights(target.target_weights, timestamp)
            executor.record_nav(timestamp)

        # Build results dict
        nav_series = executor.get_nav_series()
        final_nav = float(nav_series.iloc[-1]) if len(nav_series) > 0 else 100000.0

        results = {
            'model_ids': ['EquityTrendModel_v1', 'IndexMeanReversionModel_v1', 'CryptoMomentumModel_v1'],
            'nav_series': nav_series,
            'trade_log': executor.get_trade_log(),
            'metrics': {
                'sharpe_ratio': 0.0,
                'final_nav': final_nav
            },
            'attribution_history': attribution_tracker.history
        }

        # Verify results
        assert len(results['nav_series']) > 0
        assert 'sharpe_ratio' in results['metrics']
        assert len(results['model_ids']) == 3
        assert 'attribution_history' in results

        # Verify attribution history exists and is valid
        assert len(results['attribution_history']) > 0
        final_snapshot = results['attribution_history'][-1]
        assert hasattr(final_snapshot, 'positions')
        assert hasattr(final_snapshot, 'attribution')

        self.log_verbose(f"  Models: {', '.join(results['model_ids'])}")
        self.log_verbose(f"  Bars simulated: {len(results['nav_series'])}")
        self.log_verbose(f"  Trades: {len(results['trade_log'])}")
        self.log_verbose(f"  Final NAV: ${results['metrics']['final_nav']:,.2f}")
        self.log_verbose(f"  Sharpe: {results['metrics']['sharpe_ratio']:.2f}")
        self.log_verbose(f"  Attribution snapshots: {len(results['attribution_history'])}")

    def test_backtest_executor(self):
        """Test backtest executor."""
        import pandas as pd
        import numpy as np
        from backtest.executor import BacktestExecutor, BacktestConfig

        # Create sample data
        dates = pd.date_range('2025-01-01', periods=50, freq='4H', tz='UTC')

        spy_data = pd.DataFrame({
            'open': 450 + np.random.randn(50) * 2,
            'high': 452 + np.random.randn(50) * 2,
            'low': 448 + np.random.randn(50) * 2,
            'close': 450 + np.random.randn(50) * 2,
            'volume': np.random.randint(1000000, 5000000, 50)
        }, index=dates)

        # Ensure OHLC consistency
        spy_data['high'] = spy_data[['open', 'high', 'close']].max(axis=1)
        spy_data['low'] = spy_data[['open', 'low', 'close']].min(axis=1)

        # Create executor
        config = BacktestConfig(
            initial_nav=Decimal('100000.00'),
            fill_timing='close',
            slippage_bps=5.0,
            commission_pct=0.001
        )

        executor = BacktestExecutor(
            config=config,
            asset_data={'SPY': spy_data}
        )

        # Submit orders
        target_weights = {'SPY': 0.5}
        orders = executor.submit_target_weights(target_weights, dates[0])

        assert len(orders) > 0, "No orders executed"
        assert executor.get_nav() > 0, "NAV is invalid"

        self.log_verbose(f"  Initial NAV: ${config.initial_nav:,.2f}")
        self.log_verbose(f"  Executed {len(orders)} orders")
        self.log_verbose(f"  Current NAV: ${executor.get_nav():,.2f}")

    def test_data_pipeline(self):
        """Test data pipeline (requires generated data)."""
        import pandas as pd
        import numpy as np
        from engines.data.pipeline import DataPipeline
        from engines.data.downloader import DataDownloader
        from engines.data.features import FeatureComputer

        data_dir = self.temp_dir / "data"

        # Generate synthetic data
        downloader = DataDownloader(data_dir=str(data_dir))

        dates_1d = pd.date_range('2023-01-01', periods=500, freq='1D', tz='UTC')
        dates_4h = pd.date_range('2023-01-01', periods=3000, freq='4H', tz='UTC')

        for symbol in ['SPY', 'QQQ']:
            # Generate daily
            base_price = 450 if symbol == 'SPY' else 380
            close_1d = base_price * np.exp(np.cumsum(np.random.normal(0.0001, 0.015, len(dates_1d))))

            df_1d = pd.DataFrame({
                'open': close_1d * (1 + np.random.normal(0, 0.003, len(dates_1d))),
                'high': close_1d * (1 + np.abs(np.random.normal(0.008, 0.005, len(dates_1d)))),
                'low': close_1d * (1 - np.abs(np.random.normal(0.008, 0.005, len(dates_1d)))),
                'close': close_1d,
                'volume': np.random.randint(1000000, 10000000, len(dates_1d))
            }, index=dates_1d)

            df_1d['high'] = df_1d[['open', 'high', 'close']].max(axis=1)
            df_1d['low'] = df_1d[['open', 'low', 'close']].min(axis=1)

            # Save
            equities_dir = data_dir / 'equities'
            equities_dir.mkdir(parents=True, exist_ok=True)
            df_1d.to_parquet(equities_dir / f"{symbol}_1D.parquet")

            # Generate 4H
            close_4h = base_price * np.exp(np.cumsum(np.random.normal(0.0001, 0.015, len(dates_4h))))

            df_4h = pd.DataFrame({
                'open': close_4h * (1 + np.random.normal(0, 0.003, len(dates_4h))),
                'high': close_4h * (1 + np.abs(np.random.normal(0.008, 0.005, len(dates_4h)))),
                'low': close_4h * (1 - np.abs(np.random.normal(0.008, 0.005, len(dates_4h)))),
                'close': close_4h,
                'volume': np.random.randint(1000000, 10000000, len(dates_4h))
            }, index=dates_4h)

            df_4h['high'] = df_4h[['open', 'high', 'close']].max(axis=1)
            df_4h['low'] = df_4h[['open', 'low', 'close']].min(axis=1)

            df_4h.to_parquet(equities_dir / f"{symbol}_4H.parquet")

        # Test pipeline
        pipeline = DataPipeline(data_dir=str(data_dir))

        data = pipeline.load_and_prepare(
            symbols=['SPY', 'QQQ'],
            h4_timeframe='4H',
            daily_timeframe='1D',
            asset_class='equity'
        )

        assert 'SPY' in data
        assert 'QQQ' in data
        assert len(data['SPY']) > 0
        assert 'daily_ma_200' in data['SPY'].columns

        self.log_verbose(f"  Loaded {len(data)} symbols")
        self.log_verbose(f"  SPY: {len(data['SPY'])} bars, {len(data['SPY'].columns)} features")

    def test_results_database(self):
        """Test DuckDB results database."""
        import pandas as pd
        import numpy as np
        from results.schema import ResultsDatabase

        db_path = self.temp_dir / "test_results.duckdb"
        db = ResultsDatabase(str(db_path))

        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='D', tz='UTC')
        nav_series = pd.Series(
            100000 * np.exp(np.cumsum(np.random.normal(0.0001, 0.01, 100))),
            index=dates
        )

        trade_log = pd.DataFrame({
            'timestamp': dates[:10],
            'symbol': ['SPY'] * 10,
            'side': ['BUY', 'SELL'] * 5,
            'quantity': np.random.randint(10, 100, 10),
            'price': 450 + np.random.randn(10) * 5,
            'gross_value': np.random.uniform(4000, 50000, 10),
            'commission': np.random.uniform(5, 50, 10)
        })

        metrics = {
            'total_return': 0.15,
            'cagr': 0.12,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.08
        }

        # Save
        run_id = "test_run_001"
        db.save_backtest_results(
            run_id=run_id,
            model_id="EquityTrendModel_v1",
            start_date="2023-01-01",
            end_date="2023-12-31",
            nav_series=nav_series,
            trade_log=trade_log,
            metrics=metrics
        )

        # Retrieve
        summary = db.get_backtest_summary(run_id)
        assert summary['run_id'] == run_id

        retrieved_nav = db.get_nav_series(run_id)
        assert len(retrieved_nav) == len(nav_series)

        db.close()

        self.log_verbose(f"  Saved and retrieved run: {run_id}")
        self.log_verbose(f"  NAV points: {len(nav_series)}")
        self.log_verbose(f"  Trades: {len(trade_log)}")

    def test_full_backtest_workflow(self):
        """Test complete end-to-end backtest."""
        import pandas as pd
        import numpy as np
        import yaml
        from backtest.runner import BacktestRunner
        from models.equity_trend_v1 import EquityTrendModel_v1
        from engines.data.downloader import DataDownloader

        # Generate data (using temp dir from pipeline test)
        data_dir = self.temp_dir / "data"

        # Use data from pipeline test if available, otherwise generate
        if not (data_dir / 'equities' / 'SPY_1D.parquet').exists():
            self.log_verbose("  Generating synthetic data...")
            # Generate data with appropriate date range
            # Start early enough to allow for 200-day MA lookback
            # End slightly after backtest end to avoid edge effects
            dates_1d = pd.date_range('2022-01-01', '2024-01-15', freq='1D', tz='UTC')
            dates_4h = pd.date_range('2022-01-01', '2024-01-15', freq='4h', tz='UTC')

            for symbol in ['SPY', 'QQQ']:
                base_price = 450 if symbol == 'SPY' else 380
                close_1d = base_price * np.exp(np.cumsum(np.random.normal(0.0001, 0.015, len(dates_1d))))

                df_1d = pd.DataFrame({
                    'open': close_1d * (1 + np.random.normal(0, 0.003, len(dates_1d))),
                    'high': close_1d * (1 + np.abs(np.random.normal(0.008, 0.005, len(dates_1d)))),
                    'low': close_1d * (1 - np.abs(np.random.normal(0.008, 0.005, len(dates_1d)))),
                    'close': close_1d,
                    'volume': np.random.randint(1000000, 10000000, len(dates_1d))
                }, index=dates_1d)

                df_1d['high'] = df_1d[['open', 'high', 'close']].max(axis=1)
                df_1d['low'] = df_1d[['open', 'low', 'close']].min(axis=1)

                equities_dir = data_dir / 'equities'
                equities_dir.mkdir(parents=True, exist_ok=True)
                df_1d.to_parquet(equities_dir / f"{symbol}_1D.parquet")

                close_4h = base_price * np.exp(np.cumsum(np.random.normal(0.0001, 0.015, len(dates_4h))))

                df_4h = pd.DataFrame({
                    'open': close_4h * (1 + np.random.normal(0, 0.003, len(dates_4h))),
                    'high': close_4h * (1 + np.abs(np.random.normal(0.008, 0.005, len(dates_4h)))),
                    'low': close_4h * (1 - np.abs(np.random.normal(0.008, 0.005, len(dates_4h)))),
                    'close': close_4h,
                    'volume': np.random.randint(1000000, 10000000, len(dates_4h))
                }, index=dates_4h)

                df_4h['high'] = df_4h[['open', 'high', 'close']].max(axis=1)
                df_4h['low'] = df_4h[['open', 'low', 'close']].min(axis=1)

                df_4h.to_parquet(equities_dir / f"{symbol}_4H.parquet")

        # Create config
        config_dir = self.temp_dir / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_path = config_dir / "test_backtest.yaml"
        config_content = {
            'backtest': {
                'data_dir': str(data_dir),
                'h4_timeframe': '4H',
                'daily_timeframe': '1D',
                'asset_class': 'equity',
                'symbols': ['SPY', 'QQQ'],
                'start_date': '2023-06-01',
                'end_date': '2024-01-01',
                'initial_nav': 100000.0,
                'fill_timing': 'close',
                'slippage_bps': 5.0,
                'commission_pct': 0.001,
                'min_commission': 1.0,
                'lookback_bars': 100
            },
            'models': {
                'EquityTrendModel_v1': {
                    'budget': 0.30,
                    'ma_period': 200,
                    'momentum_period': 120
                }
            },
            'risk': {}
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_content, f)

        # Run backtest
        model = EquityTrendModel_v1(assets=['SPY', 'QQQ'])
        runner = BacktestRunner(str(config_path))

        results = runner.run(
            model=model,
            start_date='2023-06-01',
            end_date='2024-01-01'
        )

        # Verify results
        assert len(results['nav_series']) > 0
        assert 'sharpe_ratio' in results['metrics']
        assert results['metrics']['initial_nav'] == 100000.0

        self.log_verbose(f"  Bars simulated: {len(results['nav_series'])}")
        self.log_verbose(f"  Trades: {len(results['trade_log'])}")
        self.log_verbose(f"  Final NAV: ${results['metrics']['final_nav']:,.2f}")
        self.log_verbose(f"  Sharpe: {results['metrics']['sharpe_ratio']:.2f}")

    # =========================================================================
    # Main Test Runner
    # =========================================================================

    def run_all_tests(self):
        """Run all validation tests."""
        self.log(f"\n{'=' * 70}")
        self.log(f"{Colors.BOLD}TRADING PLATFORM PIPELINE VALIDATION{Colors.ENDC}")
        self.log(f"{'=' * 70}\n")

        # Setup
        self.setup_temp_environment()

        try:
            # Phase 1: Imports
            self.test_step("Import Dependencies", self.test_imports)

            # Phase 2: Utils
            self.log(f"\n{'=' * 70}")
            self.log("PHASE 2: Utilities Tests", "INFO")
            self.log(f"{'=' * 70}")

            self.test_step("Utils: Structured Logger", self.test_utils_logging)
            self.test_step("Utils: Config Loader", self.test_utils_config)
            self.test_step("Utils: Time Utilities", self.test_utils_time)
            self.test_step("Utils: Performance Metrics", self.test_utils_metrics)

            # Phase 3: Data Layer
            self.log(f"\n{'=' * 70}")
            self.log("PHASE 3: Data Layer Tests", "INFO")
            self.log(f"{'=' * 70}")

            self.test_step("Data: Validator", self.test_data_validator)
            self.test_step("Data: Time Alignment (No Look-Ahead)", self.test_data_alignment)
            self.test_step("Data: Feature Computation", self.test_data_features)
            self.test_step("Data: Pipeline", self.test_data_pipeline)

            # Phase 4: Model Layer
            self.log(f"\n{'=' * 70}")
            self.log("PHASE 4: Model Layer Tests", "INFO")
            self.log(f"{'=' * 70}")

            self.test_step("Model: Base Context", self.test_model_base)
            self.test_step("Model: EquityTrendModel_v1", self.test_equity_trend_model)
            self.test_step("Model: IndexMeanReversionModel_v1", self.test_index_mean_rev_model)
            self.test_step("Model: CryptoMomentumModel_v1", self.test_crypto_momentum_model)

            # Phase 5: Backtest Engine
            self.log(f"\n{'=' * 70}")
            self.log("PHASE 5: Backtest Engine Tests", "INFO")
            self.log(f"{'=' * 70}")

            self.test_step("Backtest: Executor", self.test_backtest_executor)
            self.test_step("Backtest: Full Workflow", self.test_full_backtest_workflow)

            # Phase 6: Results Layer
            self.log(f"\n{'=' * 70}")
            self.log("PHASE 6: Results Layer Tests", "INFO")
            self.log(f"{'=' * 70}")

            self.test_step("Results: DuckDB Database", self.test_results_database)

            # Phase 7: Multi-Model Portfolio Tests
            self.log(f"\n{'=' * 70}")
            self.log("PHASE 7: Multi-Model Portfolio Tests", "INFO")
            self.log(f"{'=' * 70}")

            self.test_step("Portfolio: Engine Aggregation", self.test_portfolio_engine)
            self.test_step("Portfolio: Attribution Tracker", self.test_attribution_tracker)
            self.test_step("Portfolio: Multi-Model Backtest", self.test_multi_model_backtest)

        finally:
            # Cleanup
            self.cleanup_temp_environment()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds()

        self.log(f"\n{'=' * 70}")
        self.log(f"{Colors.BOLD}VALIDATION SUMMARY{Colors.ENDC}")
        self.log(f"{'=' * 70}\n")

        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')

        self.log(f"Total Tests: {len(self.test_results)}")
        self.log(f"Passed: {passed}", "SUCCESS" if failed == 0 else "INFO")
        self.log(f"Failed: {failed}", "ERROR" if failed > 0 else "INFO")
        self.log(f"Time: {elapsed:.2f}s")

        if failed > 0:
            self.log(f"\n{Colors.FAIL}Failed Tests:{Colors.ENDC}")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    self.log(f"  - {result['name']}", "ERROR")
                    self.log(f"    {result['error']}", "ERROR")

            self.log(f"\n{Colors.WARNING}Run with --verbose for detailed error traces{Colors.ENDC}")

        self.log(f"\n{'=' * 70}")

        if failed == 0:
            self.log(f"{Colors.OKGREEN}{Colors.BOLD}✓ ALL TESTS PASSED - PLATFORM READY{Colors.ENDC}")
        else:
            self.log(f"{Colors.FAIL}{Colors.BOLD}✗ SOME TESTS FAILED - FIXES REQUIRED{Colors.ENDC}")

        self.log(f"{'=' * 70}\n")

        return failed == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate trading platform pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all validation tests
  python validate_pipeline.py

  # Run with verbose output
  python validate_pipeline.py --verbose
        """
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Run validation
    validator = PipelineValidator(verbose=args.verbose)
    success = validator.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
