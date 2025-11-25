"""
Backtest Analysis CLI

Run a backtest and generate comprehensive performance analysis with visualizations.

Usage:
    # Analyze using a profile
    python -m backtest.analyze_cli --profile sector_rotation_leverage

    # Analyze with custom parameters
    python -m backtest.analyze_cli \
        --model SectorRotationModel_v1 \
        --params '{"momentum_period": 126, "top_n": 3, "target_leverage": 1.25}' \
        --start 2020-01-01 \
        --end 2024-12-31

Features:
- Runs fresh backtest with specified parameters
- Generates equity curves, drawdown charts, heatmaps
- Creates detailed performance reports
- Saves all outputs to timestamped directory
"""

import argparse
import json
import yaml
import pandas as pd
import subprocess
import inspect
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from backtest.runner import BacktestRunner
from backtest.reporting import BacktestReporter
from backtest.visualization import BacktestVisualizer
from utils.logging import StructuredLogger
from utils.model_id import generate_param_id, generate_model_id, generate_model_hash, get_param_summary
from models.sector_rotation_v1 import SectorRotationModel_v1
from models.sector_rotation_bull_v1 import SectorRotationBull_v1
from models.sector_rotation_bear_v1 import SectorRotationBear_v1
from models.sector_rotation_vix_v1 import SectorRotationVIX_v1
from models.sector_rotation_spy_filter_v1 import SectorRotationSPYFilter_v1
from models.sector_rotation_regime_v1 import SectorRotationRegime_v1
from models.sector_rotation_adaptive_v3 import SectorRotationAdaptive_v3
from models.sector_rotation_adaptive_v4 import SectorRotationAdaptive_v4
from models.adaptive_regime_switcher_v1 import AdaptiveRegimeSwitcher_v1
from models.adaptive_regime_switcher_v2 import AdaptiveRegimeSwitcher_v2
from models.sector_rotation_consistent_v1 import SectorRotationConsistent_v1
from models.sector_rotation_consistent_v2 import SectorRotationConsistent_v2
from models.sector_rotation_consistent_v3 import SectorRotationConsistent_v3
from models.sector_rotation_consistent_v4 import SectorRotationConsistent_v4
from models.bear_defensive_rotation_v1 import BearDefensiveRotation_v1
from models.bear_defensive_rotation_v2 import BearDefensiveRotation_v2
from models.bear_defensive_rotation_v3 import BearDefensiveRotation_v3
from models.bear_defensive_rotation_v4 import BearDefensiveRotation_v4
from models.bear_defensive_rotation_v5 import BearDefensiveRotation_v5
from models.bear_correlation_gated_v1 import BearCorrelationGated_v1
from models.bear_multi_asset_v1 import BearMultiAsset_v1
from models.bear_multi_asset_v2 import BearMultiAsset_v2
from models.beardipbuyer_v1 import BearDipBuyer_v1
from models.sector_rotation_consistent_v5 import SectorRotationConsistent_v5
from models.equity_trend_v1 import EquityTrendModel_v1
from models.equity_trend_v1_daily import EquityTrendModel_v1_Daily
from models.cash_secured_put_v1 import CashSecuredPutModel_v1
from models.equity_trend_v2_daily import EquityTrendModel_v2_Daily


class BacktestAnalyzer:
    """
    Run backtest and generate comprehensive analysis.

    Coordinates:
    - Backtest execution
    - Report generation
    - Visualization creation
    - Benchmark comparison
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize analyzer.

        Args:
            output_dir: Output directory (default: results/analysis/{timestamp})
        """
        if output_dir is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = f"results/analysis/{timestamp}"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = StructuredLogger()
        self.reporter = BacktestReporter(logger=self.logger)
        self.visualizer = BacktestVisualizer(output_dir=str(self.output_dir))

        print(f"\n📁 Analysis output directory: {self.output_dir}")

    def get_git_info(self) -> Dict[str, Any]:
        """Get git commit hash and dirty status for reproducibility."""
        try:
            # Get current commit hash
            commit = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, check=True
            ).stdout.strip()

            # Check if working directory is dirty
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, check=True
            ).stdout.strip()

            is_dirty = len(status) > 0

            return {
                'commit': commit,
                'is_dirty': is_dirty,
                'warning': 'UNCOMMITTED CHANGES - Results may not be reproducible!' if is_dirty else None
            }
        except Exception as e:
            return {
                'commit': 'unknown',
                'is_dirty': True,
                'warning': f'Could not get git info: {e}'
            }

    def get_model_source(self, model_instance) -> str:
        """Get the source code of the model for reproducibility."""
        try:
            return inspect.getsource(model_instance.__class__)
        except Exception as e:
            return f"Could not retrieve source: {e}"

    def instantiate_model(self, model_name: str, parameters: Dict[str, Any]):
        """
        Instantiate a model by name with parameters.

        Args:
            model_name: Model class name
            parameters: Model parameters

        Returns:
            Model instance
        """
        if model_name == "SectorRotationModel_v1":
            return SectorRotationModel_v1(**parameters)
        elif model_name == "SectorRotationBull_v1":
            return SectorRotationBull_v1(**parameters)
        elif model_name == "SectorRotationBear_v1":
            return SectorRotationBear_v1(**parameters)
        elif model_name == "SectorRotationVIX_v1":
            return SectorRotationVIX_v1(**parameters)
        elif model_name == "SectorRotationSPYFilter_v1":
            return SectorRotationSPYFilter_v1(**parameters)
        elif model_name == "SectorRotationRegime_v1":
            return SectorRotationRegime_v1(**parameters)
        elif model_name == "SectorRotationAdaptive_v3":
            return SectorRotationAdaptive_v3(**parameters)
        elif model_name == "SectorRotationAdaptive_v4":
            return SectorRotationAdaptive_v4(**parameters)
        elif model_name == "AdaptiveRegimeSwitcher_v1":
            return AdaptiveRegimeSwitcher_v1(**parameters)
        elif model_name == "AdaptiveRegimeSwitcher_v2":
            return AdaptiveRegimeSwitcher_v2(**parameters)
        elif model_name == "SectorRotationConsistent_v1":
            return SectorRotationConsistent_v1(**parameters)
        elif model_name == "SectorRotationConsistent_v2":
            return SectorRotationConsistent_v2(**parameters)
        elif model_name == "SectorRotationConsistent_v3":
            return SectorRotationConsistent_v3(**parameters)
        elif model_name == "SectorRotationConsistent_v4":
            return SectorRotationConsistent_v4(**parameters)
        elif model_name == "SectorRotationConsistent_v5":
            return SectorRotationConsistent_v5(**parameters)
        elif model_name == "EquityTrendModel_v1":
            return EquityTrendModel_v1(**parameters)
        elif model_name == "EquityTrendModel_v1_Daily":
            return EquityTrendModel_v1_Daily(**parameters)
        elif model_name == "EquityTrendModel_v2_Daily":
            return EquityTrendModel_v2_Daily(**parameters)
        elif model_name == "CashSecuredPutModel_v1":
            return CashSecuredPutModel_v1(**parameters)
        elif model_name == "BearDefensiveRotation_v1":
            return BearDefensiveRotation_v1(**parameters)
        elif model_name == "BearDefensiveRotation_v2":
            return BearDefensiveRotation_v2(**parameters)
        elif model_name == "BearDefensiveRotation_v3":
            return BearDefensiveRotation_v3(**parameters)
        elif model_name == "BearDefensiveRotation_v4":
            return BearDefensiveRotation_v4(**parameters)
        elif model_name == "BearDefensiveRotation_v5":
            return BearDefensiveRotation_v5(**parameters)
        elif model_name == "BearCorrelationGated_v1":
            return BearCorrelationGated_v1(**parameters)
        elif model_name == "BearMultiAsset_v1":
            return BearMultiAsset_v1(**parameters)
        elif model_name == "BearMultiAsset_v2":
            return BearMultiAsset_v2(**parameters)
        elif model_name == "BearDipBuyer_v1":
            return BearDipBuyer_v1(**parameters)
        else:
            raise ValueError(f"Unknown model: {model_name}")

    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Load test profile from configs/profiles.yaml.

        Args:
            profile_name: Profile name

        Returns:
            Profile configuration dict
        """
        profiles_path = Path("configs/profiles.yaml")

        if not profiles_path.exists():
            raise FileNotFoundError(f"Profiles file not found: {profiles_path}")

        with open(profiles_path) as f:
            profiles = yaml.safe_load(f)

        if profile_name not in profiles['profiles']:
            raise ValueError(f"Profile not found: {profile_name}")

        return profiles['profiles'][profile_name]

    def load_benchmark_data(
        self,
        symbol: str = "SPY",
        start_date: str = None,
        end_date: str = None
    ) -> Optional[pd.DataFrame]:
        """
        Load benchmark data for comparison.

        Args:
            symbol: Benchmark symbol (default: SPY)
            start_date: Start date
            end_date: End date

        Returns:
            Benchmark DataFrame or None if not found
        """
        benchmark_path = Path(f"data/equities/{symbol}_1D.parquet")

        if not benchmark_path.exists():
            self.logger.warning(f"Benchmark data not found: {benchmark_path}")
            return None

        df = pd.read_parquet(benchmark_path)
        # Handle both timestamp as column and as index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df = df.set_index('timestamp').sort_index()
        else:
            df.index = pd.to_datetime(df.index, utc=True)

        # Filter to date range
        if start_date:
            df = df[df.index >= pd.Timestamp(start_date, tz='UTC')]
        if end_date:
            df = df[df.index <= pd.Timestamp(end_date, tz='UTC')]

        return df

    def run_analysis_from_profile(
        self,
        profile_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run analysis using a test profile.

        Args:
            profile_name: Profile name from configs/profiles.yaml
            start_date: Optional override for start date
            end_date: Optional override for end date

        Returns:
            Backtest results dict
        """
        print("\n" + "=" * 80)
        print(f"BACKTEST ANALYSIS: {profile_name}")
        print("=" * 80)

        # Load profile
        profile = self.load_profile(profile_name)
        print(f"\n✓ Loaded profile: {profile_name}")
        print(f"  Model: {profile['model']}")
        print(f"  Parameters: {json.dumps(profile['parameters'], indent=2)}")

        # Use profile dates or overrides
        start = start_date or profile.get('start_date')
        end = end_date or profile.get('end_date')

        print(f"  Period: {start} to {end}")

        # Extract leverage from parameters (if present) to move to portfolio config
        leverage_multiplier = profile['parameters'].get('target_leverage', 1.0)

        # Remove target_leverage from model parameters (it's now system-level)
        model_params = {k: v for k, v in profile['parameters'].items() if k != 'target_leverage'}

        # Calculate required lookback based on model parameters
        # For sector rotation: momentum_period + 1
        # Default to 200 to be safe for most strategies
        required_lookback = 200
        if 'momentum_period' in model_params:
            required_lookback = max(model_params['momentum_period'] + 1, required_lookback)

        # Build base config
        base_config = {
            'mode': 'backtest',
            'system': {
                'reference_assets': [
                    {'symbol': 'SPY', 'required': True},
                    {'symbol': '^VIX', 'required': False}
                ]
            },
            'data': {
                'primary_timeframe': '1D',
                'data_dir': 'data'
            },
            'backtest': {
                'lookback_bars': required_lookback  # Ensure sufficient history for momentum calculations
            },
            'portfolio': {
                'leverage_multiplier': leverage_multiplier
            },
            'risk': {
                'max_leverage': max(leverage_multiplier, 1.0),  # Risk limit should be >= portfolio leverage
                'max_position_size': 0.40,
                'max_asset_class_allocation': {
                    'equity': 1.0,
                    'crypto': 0.20
                },
                'max_drawdown_threshold': 0.15
            },
            'models': {
                profile['model']: {
                    'enabled': True,
                    'budget': 1.0,
                    'parameters': model_params,
                    'universe': profile['universe'],
                    'asset_classes': profile.get('asset_classes', ['equity'])
                }
            },
            'execution': {
                'initial_capital': 100000.0,
                'commission_rate': 0.001,
                'slippage_bps': 5.0
            }
        }

        # Run backtest
        print("\n" + "=" * 80)
        print("RUNNING BACKTEST")
        print("=" * 80)

        # Create temporary config file
        temp_config_path = self.output_dir / "temp_config.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(base_config, f)

        # Instantiate model (without target_leverage - that's system-level now)
        model_instance = self.instantiate_model(profile['model'], model_params)

        runner = BacktestRunner(str(temp_config_path), logger=self.logger)
        results = runner.run(
            model=model_instance,
            start_date=start,
            end_date=end
        )

        print(f"\n✓ Backtest completed")
        print(f"  Total trades: {results['metrics']['total_trades']}")
        print(f"  Final NAV: ${results['metrics']['final_nav']:,.2f}")
        print(f"  CAGR: {results['metrics']['cagr']:.2%}")
        print(f"  Sharpe: {results['metrics']['sharpe_ratio']:.3f}")
        print(f"  BPS: {results['metrics']['bps']:.3f}")

        # Add reproducibility info
        git_info = self.get_git_info()
        if git_info.get('warning'):
            print(f"\n⚠️  {git_info['warning']}")

        results['reproducibility'] = {
            'git': git_info,
            'profile_name': profile_name,
            'parameters': model_params,
            'model_source': self.get_model_source(model_instance),
            'full_config': base_config
        }

        return results

    def run_analysis_custom(
        self,
        model: str,
        parameters: Dict[str, Any],
        universe: list,
        start_date: str,
        end_date: str,
        asset_classes: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Run analysis with custom parameters.

        Args:
            model: Model class name
            parameters: Model parameters dict
            universe: List of symbols
            start_date: Start date
            end_date: End date
            asset_classes: List of asset classes (default: ['equity'])

        Returns:
            Backtest results dict
        """
        print("\n" + "=" * 80)
        print(f"BACKTEST ANALYSIS: {model}")
        print("=" * 80)

        # Extract leverage from parameters (if present) to move to portfolio config
        leverage_multiplier = parameters.get('target_leverage', 1.0)

        # Remove target_leverage from model parameters (it's now system-level)
        model_params = {k: v for k, v in parameters.items() if k != 'target_leverage'}

        print(f"\nParameters: {json.dumps(model_params, indent=2)}")
        if leverage_multiplier != 1.0:
            print(f"Leverage: {leverage_multiplier}x")
        print(f"Universe: {universe}")
        print(f"Period: {start_date} to {end_date}")

        # Calculate required lookback based on model parameters
        required_lookback = 200
        if 'momentum_period' in model_params:
            required_lookback = max(model_params['momentum_period'] + 1, required_lookback)

        # Build base config
        base_config = {
            'mode': 'backtest',
            'system': {
                'reference_assets': [
                    {'symbol': 'SPY', 'required': True},
                    {'symbol': '^VIX', 'required': False}
                ]
            },
            'data': {
                'primary_timeframe': '1D',
                'data_dir': 'data'
            },
            'backtest': {
                'lookback_bars': required_lookback
            },
            'portfolio': {
                'leverage_multiplier': leverage_multiplier
            },
            'risk': {
                'max_leverage': max(leverage_multiplier, 1.0),  # Risk limit should be >= portfolio leverage
                'max_position_size': 0.40,
                'max_asset_class_allocation': {
                    'equity': 1.0,
                    'crypto': 0.20
                },
                'max_drawdown_threshold': 0.15
            },
            'models': {
                model: {
                    'enabled': True,
                    'budget': 1.0,
                    'parameters': model_params,
                    'universe': universe,
                    'asset_classes': asset_classes or ['equity']
                }
            },
            'execution': {
                'initial_capital': 100000.0,
                'commission_rate': 0.001,
                'slippage_bps': 5.0
            }
        }

        # Run backtest
        print("\n" + "=" * 80)
        print("RUNNING BACKTEST")
        print("=" * 80)

        # Create temporary config file
        temp_config_path = self.output_dir / "temp_config.yaml"
        with open(temp_config_path, 'w') as f:
            yaml.dump(base_config, f)

        # Instantiate model (without target_leverage - that's system-level now)
        model_instance = self.instantiate_model(model, model_params)

        runner = BacktestRunner(str(temp_config_path), logger=self.logger)
        results = runner.run(
            model=model_instance,
            start_date=start_date,
            end_date=end_date
        )

        print(f"\n✓ Backtest completed")
        print(f"  Total trades: {results['metrics']['total_trades']}")
        print(f"  Final NAV: ${results['metrics']['final_nav']:,.2f}")
        print(f"  CAGR: {results['metrics']['cagr']:.2%}")
        print(f"  Sharpe: {results['metrics']['sharpe_ratio']:.3f}")
        print(f"  BPS: {results['metrics']['bps']:.3f}")

        return results

    def generate_reports(self, results: Dict[str, Any]):
        """
        Generate text and CSV reports.

        Args:
            results: Backtest results dict
        """
        print("\n" + "=" * 80)
        print("GENERATING REPORTS")
        print("=" * 80)

        # Generate summary report
        summary = self.reporter.generate_summary_report(results)

        # Save summary to file
        summary_path = self.output_dir / "summary_report.txt"
        with open(summary_path, 'w') as f:
            f.write(summary)
        print(f"  ✓ Summary report saved to: {summary_path}")

        # Export to CSVs
        self.reporter.export_to_csv(results, output_dir=str(self.output_dir))

        # Save metadata with full reproducibility info
        # Generate model and parameter IDs for consistent tracking
        model_name = results['model_ids'][0] if results['model_ids'] else 'unknown'
        params = results.get('reproducibility', {}).get('parameters', {})

        # Get model source for hashing (read from saved file if exists)
        model_source = None
        source_path = self.output_dir / "model_source.py"
        if source_path.exists():
            model_source = source_path.read_text()

        param_id = generate_param_id(params)
        model_hash = generate_model_hash(model_source) if model_source else None
        full_model_id = generate_model_id(model_name, params, model_source)
        param_summary = get_param_summary(params)

        metadata = {
            'model': model_name,
            'model_id': full_model_id,
            'model_hash': model_hash,
            'param_id': param_id,
            'param_summary': param_summary,
            'start_date': results['start_date'],
            'end_date': results['end_date'],
            'metrics': results['metrics'],
            'generated_at': datetime.now().isoformat()
        }

        # Add reproducibility info if available
        if 'reproducibility' in results:
            repro = results['reproducibility']
            metadata['reproducibility'] = {
                'git_commit': repro['git']['commit'],
                'git_dirty': repro['git']['is_dirty'],
                'profile_name': repro.get('profile_name'),
                'parameters': repro['parameters'],
                'full_config': repro['full_config']
            }
            if repro['git'].get('warning'):
                metadata['reproducibility']['warning'] = repro['git']['warning']

            # Save model source separately (can be large)
            source_path = self.output_dir / "model_source.py"
            with open(source_path, 'w') as f:
                f.write(repro['model_source'])
            print(f"  ✓ Model source saved to: {source_path}")

        metadata_path = self.output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ Metadata saved to: {metadata_path}")

    def generate_visualizations(
        self,
        results: Dict[str, Any],
        benchmark_symbol: str = "SPY"
    ):
        """
        Generate all visualization charts.

        Args:
            results: Backtest results dict
            benchmark_symbol: Benchmark symbol for comparison
        """
        # Load benchmark data
        benchmark_data = self.load_benchmark_data(
            symbol=benchmark_symbol,
            start_date=results['start_date'],
            end_date=results['end_date']
        )

        # Generate all charts
        self.visualizer.generate_all_charts(
            results,
            benchmark_data=benchmark_data
        )

    def run_full_analysis(
        self,
        profile_name: Optional[str] = None,
        model: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        universe: Optional[list] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        asset_classes: Optional[list] = None,
        benchmark: str = "SPY"
    ):
        """
        Run complete analysis workflow.

        Args:
            profile_name: Test profile name (if using profile)
            model: Model name (if using custom params)
            parameters: Model parameters (if using custom params)
            universe: Symbol universe (if using custom params)
            start_date: Start date
            end_date: End date
            asset_classes: Asset classes (if using custom params)
            benchmark: Benchmark symbol for comparison
        """
        # Run backtest
        if profile_name:
            results = self.run_analysis_from_profile(
                profile_name,
                start_date=start_date,
                end_date=end_date
            )
        elif model and parameters and universe:
            if not start_date or not end_date:
                raise ValueError("start_date and end_date required for custom analysis")
            results = self.run_analysis_custom(
                model,
                parameters,
                universe,
                start_date,
                end_date,
                asset_classes
            )
        else:
            raise ValueError("Must provide either profile_name or (model, parameters, universe)")

        # Generate reports
        self.generate_reports(results)

        # Generate visualizations
        self.generate_visualizations(results, benchmark_symbol=benchmark)

        # Final summary
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"\n📁 All outputs saved to: {self.output_dir}")
        print("\nGenerated files:")
        print("  - summary_report.txt         (detailed text report)")
        print("  - metadata.json              (backtest metadata)")
        print("  - nav_series.csv             (NAV time series)")
        print("  - trades.csv                 (trade log)")
        print("  - equity_curve.png           (equity vs benchmark chart)")
        print("  - drawdown.png               (drawdown over time)")
        print("  - monthly_returns_heatmap.png (monthly performance)")
        print("  - trade_analysis.png         (trade statistics)")
        print("  - rolling_metrics.png        (rolling Sharpe/volatility)")
        print("  - returns_distribution.png   (return histogram)")
        print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run backtest and generate performance analysis with visualizations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze using a profile
  python -m backtest.analyze_cli --profile sector_rotation_leverage

  # Analyze with custom parameters
  python -m backtest.analyze_cli \\
      --model SectorRotationModel_v1 \\
      --params '{"momentum_period": 126, "top_n": 3, "target_leverage": 1.25}' \\
      --universe SPY,QQQ,XLK,XLV,XLF \\
      --start 2020-01-01 \\
      --end 2024-12-31

  # Override dates for a profile
  python -m backtest.analyze_cli \\
      --profile sector_rotation_default \\
      --start 2023-01-01 \\
      --end 2024-12-31
        """
    )

    # Profile-based analysis
    parser.add_argument('--profile', type=str,
                       help='Test profile name from configs/profiles.yaml')

    # Custom parameter analysis
    parser.add_argument('--model', type=str,
                       help='Model class name (e.g., SectorRotationModel_v1)')
    parser.add_argument('--params', type=str,
                       help='Model parameters as JSON string')
    parser.add_argument('--universe', type=str,
                       help='Comma-separated list of symbols')
    parser.add_argument('--asset-classes', type=str,
                       help='Comma-separated list of asset classes (default: equity)')

    # Date range
    parser.add_argument('--start', type=str,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str,
                       help='End date (YYYY-MM-DD)')

    # Benchmark
    parser.add_argument('--benchmark', type=str, default='SPY',
                       help='Benchmark symbol for comparison (default: SPY)')

    # Output
    parser.add_argument('--output', type=str,
                       help='Output directory (default: results/analysis/{timestamp})')

    args = parser.parse_args()

    # Validate inputs
    if not args.profile and not (args.model and args.params and args.universe):
        parser.error("Must provide either --profile or (--model, --params, --universe)")

    # Initialize analyzer
    analyzer = BacktestAnalyzer(output_dir=args.output)

    # Parse custom parameters if provided
    parameters = None
    universe = None
    asset_classes = None

    if args.params:
        parameters = json.loads(args.params)

    if args.universe:
        universe = [s.strip() for s in args.universe.split(',')]

    if args.asset_classes:
        asset_classes = [s.strip() for s in args.asset_classes.split(',')]

    # Run analysis
    try:
        analyzer.run_full_analysis(
            profile_name=args.profile,
            model=args.model,
            parameters=parameters,
            universe=universe,
            start_date=args.start,
            end_date=args.end,
            asset_classes=asset_classes,
            benchmark=args.benchmark
        )
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
