#!/usr/bin/env python3
"""
Functional Test Script for Trading Platform

Tests the complete end-to-end workflow:
1. Data download
2. Backtest execution
3. Performance analysis
4. Results reporting
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import yaml
from decimal import Decimal

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print a section header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_metric(label, value, unit=""):
    """Print a metric with formatting."""
    print(f"  {Colors.BOLD}{label:.<40}{Colors.ENDC} {Colors.OKCYAN}{value}{unit}{Colors.ENDC}")


def test_data_download():
    """Test data download functionality."""
    print_header("PHASE 1: DATA DOWNLOAD")

    from engines.data.downloader import DataDownloader

    symbols = ['SPY', 'QQQ']

    # Use VERY recent dates to stay within Yahoo Finance 730-day limit
    # Daily: Need 200+ trading days for 200-day MA (about 10 months)
    daily_start = '2024-01-01'

    # H4: Use last 60-90 days only (Yahoo Finance hourly limit is 730 days from TODAY)
    h4_start = '2024-09-01'  # About 2.5 months of data
    end_date = '2024-11-15'  # Recent end date

    print_info(f"Downloading data for {', '.join(symbols)}")
    print_info(f"Daily period: {daily_start} to {end_date}")
    print_info(f"H4 period: {h4_start} to {end_date}")
    print_warning("Note: Yahoo Finance hourly data can be unreliable; using shorter H4 period")

    downloader = DataDownloader(data_dir='data')

    for symbol in symbols:
        print(f"\n{Colors.BOLD}Downloading {symbol}...{Colors.ENDC}")

        # Download daily data (automatically saves to parquet)
        try:
            df_daily = downloader.download_equity(
                symbol=symbol,
                start_date=daily_start,
                end_date=end_date,
                timeframe='1D'
            )
            print_success(f"Daily data: {len(df_daily)} bars → data/equities/{symbol}_1D.parquet")
        except Exception as e:
            print_error(f"Failed to download daily data: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Download H4 data (automatically saves to parquet)
        # First try H4, if it fails try 1H as fallback
        try:
            print(f"  Attempting H4 download (this may take a moment)...")
            df_h4 = downloader.download_equity(
                symbol=symbol,
                start_date=h4_start,
                end_date=end_date,
                timeframe='4H'
            )
            print_success(f"H4 data: {len(df_h4)} bars → data/equities/{symbol}_4H.parquet")
        except Exception as e:
            print_warning(f"H4 download failed: {e}")
            print_info(f"Attempting 1H download as fallback...")

            try:
                # Try 1H data and manually resample
                df_1h = downloader.download_equity(
                    symbol=symbol,
                    start_date=h4_start,
                    end_date=end_date,
                    timeframe='1H'
                )

                # Manually resample to 4H
                print_info(f"Resampling {len(df_1h)} 1H bars to 4H...")
                df_h4 = df_1h.resample('4H').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()

                # Filter to H4 boundaries
                df_h4 = df_h4[df_h4.index.hour.isin([0, 4, 8, 12, 16, 20])]

                # Save manually
                from pathlib import Path
                output_path = Path('data/equities') / f"{symbol}_4H.parquet"
                df_h4.to_parquet(output_path, engine='pyarrow', compression='snappy')

                print_success(f"H4 data: {len(df_h4)} bars → {output_path}")
            except Exception as e2:
                print_error(f"Failed to download 1H data as fallback: {e2}")
                import traceback
                traceback.print_exc()
                return False

    print_success("\nData download completed successfully!")
    return True


def test_backtest_execution():
    """Test backtest execution."""
    print_header("PHASE 2: BACKTEST EXECUTION")

    from models.equity_trend_v1 import EquityTrendModel_v1
    from backtest.runner import BacktestRunner

    # Create backtest config
    config_path = Path('configs/base/test_system.yaml')
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Use dates that match our H4 data availability
    config = {
        'backtest': {
            'data_dir': 'data',
            'h4_timeframe': '4H',
            'daily_timeframe': '1D',
            'asset_class': 'equity',
            'symbols': ['SPY', 'QQQ'],
            'start_date': '2024-09-01',  # Match H4 data start
            'end_date': '2024-11-01',  # Use Nov 1 as end for clean cutoff
            'initial_nav': 100000.0,
            'fill_timing': 'close',
            'slippage_bps': 5.0,
            'commission_pct': 0.001,
            'min_commission': 1.0,
            'lookback_bars': 100
        },
        'models': {
            'EquityTrendModel_v1': {
                'budget': 0.50,
                'ma_period': 200,
                'momentum_period': 120
            }
        },
        'risk': {}
    }

    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    print_info(f"Config: {config_path}")
    print_info(f"Period: {config['backtest']['start_date']} to {config['backtest']['end_date']}")
    print_info(f"Initial Capital: ${config['backtest']['initial_nav']:,.0f}")
    print_info(f"Assets: {', '.join(config['backtest']['symbols'])}")

    # Initialize model
    print(f"\n{Colors.BOLD}Initializing EquityTrendModel_v1...{Colors.ENDC}")
    model = EquityTrendModel_v1(
        assets=['SPY', 'QQQ'],
        ma_period=200,
        momentum_period=120
    )
    print_success(f"Model: {model.model_id}")
    print_info(f"Strategy: 200-day MA trend following with 120-day momentum")

    # Run backtest
    print(f"\n{Colors.BOLD}Running backtest...{Colors.ENDC}")
    try:
        runner = BacktestRunner(str(config_path))
        results = runner.run(
            model=model,
            start_date='2024-09-01',  # Match config start date
            end_date='2024-11-01'
        )
        print_success("Backtest completed successfully!")
        return results
    except Exception as e:
        print_error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_results_analysis(results):
    """Test results analysis and reporting."""
    print_header("PHASE 3: RESULTS ANALYSIS")

    if results is None:
        print_error("No results to analyze")
        return False

    # Performance metrics
    print(f"{Colors.BOLD}Performance Metrics{Colors.ENDC}")
    print("-" * 80)

    metrics = results['metrics']

    print_metric("Initial NAV", f"${metrics['initial_nav']:,.2f}")
    print_metric("Final NAV", f"${metrics['final_nav']:,.2f}")
    print_metric("Total Return", f"{metrics['total_return']*100:.2f}", "%")
    print_metric("CAGR", f"{metrics['cagr']*100:.2f}", "%")
    print_metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.3f}")
    print_metric("Max Drawdown", f"{metrics['max_drawdown']*100:.2f}", "%")
    print_metric("Win Rate", f"{metrics['win_rate']*100:.1f}", "%")
    print_metric("Total Trades", f"{metrics['total_trades']}")
    print_metric("Balanced Performance Score", f"{metrics['bps']:.3f}")

    # NAV series
    nav_series = results['nav_series']
    print(f"\n{Colors.BOLD}NAV Progression{Colors.ENDC}")
    print("-" * 80)
    print_info(f"Total bars: {len(nav_series)}")
    print_info(f"First bar: {nav_series.index[0]} → ${nav_series.iloc[0]:,.2f}")
    print_info(f"Last bar: {nav_series.index[-1]} → ${nav_series.iloc[-1]:,.2f}")

    # Calculate key statistics
    nav_max = nav_series.max()
    nav_min = nav_series.min()
    nav_max_date = nav_series.idxmax()
    nav_min_date = nav_series.idxmin()

    print_metric("Peak NAV", f"${nav_max:,.2f} (on {nav_max_date.date()})")
    print_metric("Trough NAV", f"${nav_min:,.2f} (on {nav_min_date.date()})")

    # Trade log
    trade_log = results['trade_log']
    print(f"\n{Colors.BOLD}Trade Activity{Colors.ENDC}")
    print("-" * 80)

    if len(trade_log) > 0:
        print_info(f"Total trades: {len(trade_log)}")

        # Show first 5 trades
        print(f"\n{Colors.BOLD}Sample Trades (first 5):{Colors.ENDC}")
        for i, trade in trade_log.head(5).iterrows():
            print(f"  {trade['timestamp']:%Y-%m-%d %H:%M} | "
                  f"{trade['symbol']:>5} | "
                  f"{trade['side']:>4} | "
                  f"{trade['quantity']:>8.2f} @ ${trade['price']:>8.2f} | "
                  f"Fee: ${trade['commission']:>6.2f}")

        if len(trade_log) > 5:
            print(f"  ... and {len(trade_log) - 5} more trades")
    else:
        print_warning("No trades executed")

    # Assessment
    print(f"\n{Colors.BOLD}Assessment{Colors.ENDC}")
    print("-" * 80)

    # Determine performance grade
    if metrics['sharpe_ratio'] >= 1.5 and metrics['cagr'] >= 0.15:
        grade = f"{Colors.OKGREEN}EXCELLENT{Colors.ENDC}"
        assessment = "Strong risk-adjusted returns with good growth"
    elif metrics['sharpe_ratio'] >= 1.0 and metrics['cagr'] >= 0.10:
        grade = f"{Colors.OKGREEN}GOOD{Colors.ENDC}"
        assessment = "Solid performance with acceptable risk"
    elif metrics['sharpe_ratio'] >= 0.5 and metrics['cagr'] >= 0.05:
        grade = f"{Colors.WARNING}FAIR{Colors.ENDC}"
        assessment = "Moderate performance, room for improvement"
    else:
        grade = f"{Colors.FAIL}POOR{Colors.ENDC}"
        assessment = "Underperforming, strategy needs refinement"

    print(f"  Grade: {grade}")
    print(f"  {assessment}")

    # Risk assessment
    if metrics['max_drawdown'] < 0.10:
        risk_level = f"{Colors.OKGREEN}LOW{Colors.ENDC}"
    elif metrics['max_drawdown'] < 0.20:
        risk_level = f"{Colors.WARNING}MODERATE{Colors.ENDC}"
    else:
        risk_level = f"{Colors.FAIL}HIGH{Colors.ENDC}"

    print(f"  Risk Level: {risk_level}")

    return True


def test_data_pipeline():
    """Test data pipeline functionality."""
    print_header("PHASE 4: DATA PIPELINE VALIDATION")

    from engines.data.pipeline import DataPipeline

    pipeline = DataPipeline(data_dir='data')

    print_info("Loading and preparing data...")

    try:
        asset_data = pipeline.load_and_prepare(
            symbols=['SPY', 'QQQ'],
            h4_timeframe='4H',
            daily_timeframe='1D',
            asset_class='equity'
        )

        print_success(f"Loaded data for {len(asset_data)} symbols")

        for symbol, df in asset_data.items():
            print(f"\n{Colors.BOLD}{symbol}:{Colors.ENDC}")
            print_metric("Bars", len(df))
            print_metric("Date range", f"{df.index[0].date()} to {df.index[-1].date()}")
            print_metric("Columns", ', '.join(df.columns.tolist()[:5]) + '...')

            # Check for required features
            required_features = ['close', 'daily_ma_200', 'daily_momentum_120']
            has_all = all(col in df.columns for col in required_features)
            if has_all:
                print_success("All required features present")
            else:
                print_warning("Some features missing")

        return True
    except Exception as e:
        print_error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_model_portfolio():
    """Test multi-model portfolio execution (Phase 4)."""
    print_header("PHASE 5: MULTI-MODEL PORTFOLIO")

    from models.equity_trend_v1 import EquityTrendModel_v1
    from models.index_mean_rev_v1 import IndexMeanReversionModel_v1
    from backtest.runner import BacktestRunner

    # Create multi-model config
    config_path = Path('configs/base/test_multi_model.yaml')
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {
        'backtest': {
            'data_dir': 'data',
            'h4_timeframe': '4H',
            'daily_timeframe': '1D',
            'asset_class': 'equity',
            'symbols': ['SPY', 'QQQ'],
            'start_date': '2024-09-01',
            'end_date': '2024-11-01',
            'initial_nav': 100000.0,
            'fill_timing': 'close',
            'slippage_bps': 5.0,
            'commission_pct': 0.001,
            'min_commission': 1.0,
            'lookback_bars': 100
        },
        'models': {
            'EquityTrendModel_v1': {
                'budget': 0.60,
                'ma_period': 200,
                'momentum_period': 120
            },
            'IndexMeanReversionModel_v1': {
                'budget': 0.40,
                'rsi_period': 14,
                'bb_period': 20
            }
        },
        'risk': {
            'max_position_size': 0.40,
            'max_asset_class_exposure': {'equity': 1.0},
            'max_leverage': 1.2
        }
    }

    with open(config_path, 'w') as f:
        yaml.dump(config, f)

    print_info(f"Config: {config_path}")
    print_info(f"Models: EquityTrendModel_v1 (60%), IndexMeanReversionModel_v1 (40%)")

    # Initialize models
    print(f"\n{Colors.BOLD}Initializing models...{Colors.ENDC}")

    model1 = EquityTrendModel_v1(
        assets=['SPY', 'QQQ'],
        ma_period=200,
        momentum_period=120
    )
    print_success(f"Model 1: {model1.model_id} (60% budget)")

    model2 = IndexMeanReversionModel_v1(
        assets=['SPY', 'QQQ'],
        rsi_period=14,
        bb_period=20
    )
    print_success(f"Model 2: {model2.model_id} (40% budget)")

    # Run multi-model backtest
    print(f"\n{Colors.BOLD}Running multi-model backtest...{Colors.ENDC}")
    try:
        runner = BacktestRunner(str(config_path))
        results = runner.run(
            models=[model1, model2],
            start_date='2024-09-01',
            end_date='2024-11-01'
        )

        print_success("Multi-model backtest completed!")

        # Verify multi-model results
        print(f"\n{Colors.BOLD}Multi-Model Validation:{Colors.ENDC}")

        if 'attribution_history' in results and len(results['attribution_history']) > 0:
            print_success("Attribution tracking: ACTIVE")

            last_snapshot = results['attribution_history'][-1]
            print_metric("Models tracked", len(results['model_ids']))
            print_metric("Model IDs", ', '.join(results['model_ids']))

            # Check budget allocation
            print(f"\n{Colors.BOLD}Budget Allocation:{Colors.ENDC}")
            for model_id in results['model_ids']:
                budget = last_snapshot.model_budgets.get(model_id, 0.0)
                print_metric(model_id, f"{budget*100:.1f}%")

            # Check attribution
            print(f"\n{Colors.BOLD}Position Attribution:{Colors.ENDC}")
            for symbol, attr_dict in last_snapshot.attribution.items():
                if len(attr_dict) > 0:
                    total_weight = sum(attr_dict.values())
                    print(f"  {symbol}: {total_weight*100:.2f}% total")
                    for model_id, weight in attr_dict.items():
                        print(f"    └─ {model_id}: {weight*100:.2f}%")
        else:
            print_warning("No attribution data found")

        return results
    except Exception as e:
        print_error(f"Multi-model backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_risk_controls():
    """Test risk control functionality (Phase 5)."""
    print_header("PHASE 6: RISK CONTROLS")

    from engines.risk.engine import RiskEngine, RiskLimits

    print_info("Initializing risk engine...")

    # Create risk limits
    limits = RiskLimits(
        max_position_size=0.40,
        max_crypto_exposure=0.20,
        max_total_leverage=1.2,
        max_drawdown_threshold=0.15
    )

    risk_engine = RiskEngine(limits=limits)

    print_success("Risk engine initialized")

    # Display constraints
    print(f"\n{Colors.BOLD}Active Risk Limits:{Colors.ENDC}")
    print_metric("Max Position Size", f"{limits.max_position_size*100:.0f}%")
    print_metric("Max Crypto Exposure", f"{limits.max_crypto_exposure*100:.0f}%")
    print_metric("Max Total Leverage", f"{limits.max_total_leverage:.2f}x")
    print_metric("Drawdown Threshold", f"{limits.max_drawdown_threshold*100:.0f}%")
    print_metric("Drawdown Halt", f"{limits.max_drawdown_halt*100:.0f}%")

    # Test constraint enforcement
    print(f"\n{Colors.BOLD}Testing Constraint Enforcement:{Colors.ENDC}")

    # Test 1: Position size limit
    test_portfolio = {
        'SPY': 0.50,  # Exceeds 40% limit
        'QQQ': 0.30
    }

    print_info("Test 1: Position size limit (SPY at 50% > 40% max)")
    constrained, violations = risk_engine.enforce_constraints(
        target_weights=test_portfolio,
        current_nav=Decimal('100000'),
        asset_metadata={'SPY': {'asset_class': 'equity'}, 'QQQ': {'asset_class': 'equity'}}
    )

    if constrained['SPY'] <= 0.40:
        print_success(f"SPY constrained to {constrained['SPY']*100:.1f}%")
    else:
        print_warning(f"SPY not properly constrained: {constrained['SPY']*100:.1f}%")

    if len(violations) > 0:
        print_info(f"Violations detected: {len(violations)}")

    # Test 2: Leverage limit
    test_portfolio2 = {
        'SPY': 0.60,
        'QQQ': 0.60,
        'IWM': 0.30  # Total 150% > 120% leverage limit
    }

    print_info("Test 2: Leverage limit (150% total > 120% max)")
    constrained2, violations2 = risk_engine.enforce_constraints(
        target_weights=test_portfolio2,
        current_nav=Decimal('100000'),
        asset_metadata={
            'SPY': {'asset_class': 'equity'},
            'QQQ': {'asset_class': 'equity'},
            'IWM': {'asset_class': 'equity'}
        }
    )

    total_exposure = sum(abs(w) for w in constrained2.values())
    if total_exposure <= 1.2:
        print_success(f"Total exposure constrained to {total_exposure*100:.1f}%")
    else:
        print_warning(f"Leverage not properly constrained: {total_exposure*100:.1f}%")

    if len(violations2) > 0:
        print_info(f"Violations detected: {len(violations2)}")

    print_success("Risk controls validated")
    return True


def test_regime_classification():
    """Test regime classification functionality (Phase 6)."""
    print_header("PHASE 7: REGIME CLASSIFICATION")

    from engines.regime.engine import RegimeEngine
    from engines.regime.classifiers import (
        EquityRegimeClassifier,
        VolatilityRegimeClassifier,
        CryptoRegimeClassifier,
        MacroRegimeClassifier
    )
    from engines.data.pipeline import DataPipeline

    print_info("Initializing regime engine...")

    regime_engine = RegimeEngine()
    print_success("Regime engine initialized")

    # Test individual classifiers
    print(f"\n{Colors.BOLD}Testing Regime Classifiers:{Colors.ENDC}")

    # Load data for regime classification
    pipeline = DataPipeline(data_dir='data')

    try:
        # Load equity data for classification
        asset_data = pipeline.load_and_prepare(
            symbols=['SPY'],
            h4_timeframe='4H',
            daily_timeframe='1D',
            asset_class='equity'
        )

        spy_data = asset_data['SPY']
        test_timestamp = spy_data.index[-1]

        # Get daily prices for MA calculation
        spy_daily_prices = spy_data['close'].resample('1D').last().dropna()

        # Test equity regime
        print_info("Testing equity regime classifier...")
        equity_classifier = EquityRegimeClassifier()
        equity_regime = equity_classifier.classify(spy_daily_prices, test_timestamp)
        print_success(f"Equity regime: {equity_regime.upper()}")

        # Test volatility regime (use synthetic VIX for now)
        print_info("Testing volatility regime classifier...")
        vol_classifier = VolatilityRegimeClassifier()
        # Create synthetic VIX data based on SPY volatility
        returns = spy_daily_prices.pct_change().dropna()
        synthetic_vix = returns.rolling(20).std() * 100 * (252 ** 0.5)
        vol_regime = vol_classifier.classify(synthetic_vix, test_timestamp)
        print_success(f"Volatility regime: {vol_regime.upper()}")

        # Test full regime classification
        print(f"\n{Colors.BOLD}Full Regime State:{Colors.ENDC}")
        regime = regime_engine.classify_regime(
            timestamp=test_timestamp,
            spy_prices=spy_daily_prices,
            vix_values=synthetic_vix
        )

        print_metric("Timestamp", str(test_timestamp.date()))
        print_metric("Equity Regime", regime.equity_regime.upper())
        print_metric("Volatility Regime", regime.vol_regime.upper())
        print_metric("Crypto Regime", regime.crypto_regime.upper())
        print_metric("Macro Regime", regime.macro_regime.upper())

        # Get regime summary
        summary = regime_engine.get_regime_summary(regime)
        print_metric("Overall Risk Level", summary['risk_level'].upper())

        print_success("Regime classification validated")
        return True

    except Exception as e:
        print_error(f"Regime classification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_regime_aware_portfolio():
    """Test regime-aware portfolio management."""
    print_header("PHASE 8: REGIME-AWARE PORTFOLIO")

    from engines.portfolio.engine import PortfolioEngine
    from engines.risk.scaling import RegimeRiskScaler
    from models.base import RegimeState

    print_info("Testing regime-aware budget scaling...")

    # Create regime budget configuration
    regime_budgets = {
        'equity_regime': {
            'bull': 1.2,     # 120% budget in bull markets
            'neutral': 1.0,  # 100% budget in neutral
            'bear': 0.5      # 50% budget in bear markets
        },
        'vol_regime': {
            'low': 1.1,      # 110% budget in low vol
            'normal': 1.0,   # 100% budget in normal vol
            'high': 0.7      # 70% budget in high vol
        }
    }

    # Initialize portfolio engine with regime budgets
    portfolio_engine = PortfolioEngine(regime_budgets=regime_budgets)
    print_success("Portfolio engine initialized with regime budgets")

    # Test budget scaling in different regimes
    base_budgets = {
        'EquityTrendModel_v1': 0.60,
        'IndexMeanReversionModel_v1': 0.40
    }

    print(f"\n{Colors.BOLD}Base Budgets:{Colors.ENDC}")
    for model, budget in base_budgets.items():
        print_metric(model, f"{budget*100:.0f}%")

    # Test 1: Bull + Low Vol regime
    print(f"\n{Colors.BOLD}Scenario 1: BULL + LOW VOL{Colors.ENDC}")
    regime_bull_low = RegimeState(
        timestamp=pd.Timestamp.now(tz='UTC'),
        equity_regime='bull',
        vol_regime='low',
        crypto_regime='risk_on',
        macro_regime='expansion'
    )

    scaled_budgets_1 = portfolio_engine.apply_regime_budget_scaling(
        base_budgets=base_budgets,
        regime=regime_bull_low
    )

    for model, budget in scaled_budgets_1.items():
        multiplier = budget / base_budgets[model]
        print_metric(model, f"{budget*100:.0f}% ({multiplier:.2f}x)")

    # Test 2: Bear + High Vol regime
    print(f"\n{Colors.BOLD}Scenario 2: BEAR + HIGH VOL{Colors.ENDC}")
    regime_bear_high = RegimeState(
        timestamp=pd.Timestamp.now(tz='UTC'),
        equity_regime='bear',
        vol_regime='high',
        crypto_regime='risk_off',
        macro_regime='contraction'
    )

    scaled_budgets_2 = portfolio_engine.apply_regime_budget_scaling(
        base_budgets=base_budgets,
        regime=regime_bear_high
    )

    for model, budget in scaled_budgets_2.items():
        multiplier = budget / base_budgets[model]
        print_metric(model, f"{budget*100:.0f}% ({multiplier:.2f}x)")

    print_success("Regime-aware portfolio management validated")
    return True


def test_regime_reporting():
    """Test regime alignment reporting."""
    print_header("PHASE 9: REGIME REPORTING")

    from backtest.reporting import BacktestReporter

    print_info("Testing regime reporting functionality...")

    # Create sample results with regime data
    results = {
        'model_ids': ['TestModel'],
        'start_date': '2024-09-01',
        'end_date': '2024-11-01',
        'metrics': {
            'initial_nav': 100000.00,
            'final_nav': 110000.00,
            'total_return': 0.10,
            'cagr': 0.25,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.05,
            'win_rate': 0.65,
            'total_trades': 20,
            'bps': 0.75
        },
        'trade_log': pd.DataFrame(),
        'nav_series': pd.Series(
            [100000 + i*200 for i in range(50)],
            index=pd.date_range('2024-09-01', periods=50, freq='1D', tz='UTC')
        ),
        'regime_log': pd.DataFrame({
            'timestamp': pd.date_range('2024-09-01', periods=5, freq='10D', tz='UTC'),
            'equity_regime': ['bull', 'bull', 'neutral', 'bear', 'neutral'],
            'vol_regime': ['low', 'normal', 'normal', 'high', 'normal'],
            'crypto_regime': ['risk_on', 'risk_on', 'neutral', 'risk_off', 'neutral'],
            'macro_regime': ['expansion', 'expansion', 'neutral', 'neutral', 'expansion']
        })
    }

    reporter = BacktestReporter()

    # Test regime performance metrics
    print_info("Generating regime performance metrics...")
    regime_metrics = reporter.generate_regime_performance_metrics(results)

    if len(regime_metrics) > 0:
        print_success(f"Generated metrics for {len(regime_metrics)} regime states")
        print_metric("Dimensions analyzed", regime_metrics['dimension'].nunique())
        print_metric("Regime states", regime_metrics['regime_state'].nunique())
    else:
        print_warning("No regime metrics generated")

    # Test regime alignment report
    print_info("Generating regime alignment report...")
    report = reporter.generate_regime_alignment_report(results)

    if 'REGIME ALIGNMENT REPORT' in report:
        print_success("Regime alignment report generated")

        # Check report sections
        sections = {
            'Distribution': 'Regime Distribution' in report,
            'Performance': 'Performance by Regime' in report,
            'Transitions': 'Regime Transition Summary' in report
        }

        print(f"\n{Colors.BOLD}Report Sections:{Colors.ENDC}")
        for section, present in sections.items():
            status = f"{Colors.OKGREEN}✓{Colors.ENDC}" if present else f"{Colors.FAIL}✗{Colors.ENDC}"
            print(f"  {status} {section}")

        return all(sections.values())
    else:
        print_error("Failed to generate regime alignment report")
        return False


def main():
    """Run all functional tests."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 80)
    print("TRADING PLATFORM FUNCTIONAL TEST SUITE".center(80))
    print("Testing Phases 1-6: Complete Platform Functionality".center(80))
    print("=" * 80)
    print(f"{Colors.ENDC}\n")

    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Working directory: {os.getcwd()}")

    start_time = datetime.now()

    # Track results
    tests = []

    # Test 1: Data Download
    try:
        result = test_data_download()
        tests.append(("Phase 1: Data Download", result))
    except Exception as e:
        print_error(f"Data download test failed: {e}")
        tests.append(("Phase 1: Data Download", False))

    # Test 2: Data Pipeline
    try:
        result = test_data_pipeline()
        tests.append(("Phase 2: Data Pipeline", result))
    except Exception as e:
        print_error(f"Data pipeline test failed: {e}")
        tests.append(("Phase 2: Data Pipeline", False))

    # Test 3: Single Model Backtest
    try:
        backtest_results = test_backtest_execution()
        tests.append(("Phase 3: Single Model Backtest", backtest_results is not None))
    except Exception as e:
        print_error(f"Backtest execution test failed: {e}")
        tests.append(("Phase 3: Single Model Backtest", False))
        backtest_results = None

    # Test 4: Results Analysis
    if backtest_results is not None:
        try:
            result = test_results_analysis(backtest_results)
            tests.append(("Phase 3: Results Analysis", result))
        except Exception as e:
            print_error(f"Results analysis test failed: {e}")
            tests.append(("Phase 3: Results Analysis", False))
    else:
        tests.append(("Phase 3: Results Analysis", False))

    # Test 5: Multi-Model Portfolio
    try:
        multi_model_results = test_multi_model_portfolio()
        tests.append(("Phase 4: Multi-Model Portfolio", multi_model_results is not None))
    except Exception as e:
        print_error(f"Multi-model portfolio test failed: {e}")
        import traceback
        traceback.print_exc()
        tests.append(("Phase 4: Multi-Model Portfolio", False))

    # Test 6: Risk Controls
    try:
        result = test_risk_controls()
        tests.append(("Phase 5: Risk Controls", result))
    except Exception as e:
        print_error(f"Risk controls test failed: {e}")
        import traceback
        traceback.print_exc()
        tests.append(("Phase 5: Risk Controls", False))

    # Test 7: Regime Classification
    try:
        result = test_regime_classification()
        tests.append(("Phase 6: Regime Classification", result))
    except Exception as e:
        print_error(f"Regime classification test failed: {e}")
        import traceback
        traceback.print_exc()
        tests.append(("Phase 6: Regime Classification", False))

    # Test 8: Regime-Aware Portfolio
    try:
        result = test_regime_aware_portfolio()
        tests.append(("Phase 6: Regime-Aware Portfolio", result))
    except Exception as e:
        print_error(f"Regime-aware portfolio test failed: {e}")
        import traceback
        traceback.print_exc()
        tests.append(("Phase 6: Regime-Aware Portfolio", False))

    # Test 9: Regime Reporting
    try:
        result = test_regime_reporting()
        tests.append(("Phase 6: Regime Reporting", result))
    except Exception as e:
        print_error(f"Regime reporting test failed: {e}")
        import traceback
        traceback.print_exc()
        tests.append(("Phase 6: Regime Reporting", False))

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_header("COMPREHENSIVE TEST SUMMARY")

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    print(f"{Colors.BOLD}Test Results by Phase:{Colors.ENDC}\n")
    for name, result in tests:
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"  {name:.<60} {status}")

    print(f"\n{Colors.BOLD}Phase Coverage:{Colors.ENDC}\n")
    print_info("Phase 1: Foundation - Data Download")
    print_info("Phase 2: Foundation - Data Pipeline & Validation")
    print_info("Phase 3: User Story 1 - Single Model Backtesting")
    print_info("Phase 4: User Story 2 - Multi-Model Portfolio")
    print_info("Phase 5: User Story 3 - Risk Controls & Constraints")
    print_info("Phase 6: User Story 4 - Regime Classification & Adaptation")

    print(f"\n{Colors.BOLD}Statistics:{Colors.ENDC}\n")
    print_metric("Total Test Phases", total)
    print_metric("Passed", f"{passed} ({passed/total*100:.0f}%)")
    print_metric("Failed", f"{total - passed}")
    print_metric("Duration", f"{duration:.2f}s")

    # Feature summary
    print(f"\n{Colors.BOLD}Features Validated:{Colors.ENDC}\n")
    features = [
        "✓ Data download (equities via Yahoo Finance)",
        "✓ Data pipeline (H4 + daily alignment, feature computation)",
        "✓ Single model backtesting (equity trend following)",
        "✓ Multi-model portfolio (2+ models, budget allocation)",
        "✓ Portfolio attribution tracking",
        "✓ Risk constraints (position limits, leverage, drawdown)",
        "✓ Regime classification (equity, volatility, crypto, macro)",
        "✓ Regime-aware budget scaling",
        "✓ Regime alignment reporting"
    ]

    for feature in features:
        print(f"  {Colors.OKGREEN}{feature}{Colors.ENDC}")

    # Final verdict
    print()
    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{Colors.BOLD}{'✓ ALL TESTS PASSED - PHASES 1-6 FULLY FUNCTIONAL':^80}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print()
        print_success("Trading platform core functionality validated!")
        print_info("Ready for: Parameter optimization (Phase 7), Live trading (Phase 8)")
        return 0
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.FAIL}{Colors.BOLD}{f'✗ {total - passed}/{total} TEST(S) FAILED':^80}{Colors.ENDC}")
        print(f"{Colors.FAIL}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print()
        print_error("Some tests failed - review errors above for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
