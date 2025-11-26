"""
Component Test CLI

Test whether strategy edge comes from entries, exits, or both.

Usage:
    # Test a profile
    python -m engines.validation.component_test_cli --profile exp_standalone_v3

    # Test with custom samples
    python -m engines.validation.component_test_cli --profile exp_standalone_v3 --samples 20

    # Test specific date range
    python -m engines.validation.component_test_cli \
        --profile exp_standalone_v3 \
        --start 2020-01-01 \
        --end 2024-12-31

Interpretation:
- Entry % > 50%: Edge comes from entry timing
- Exit % > 50%: Edge comes from exit timing
- Both > 20%: Edge comes from combination
- MFE/MAE > 1.5: Good risk/reward ratio
"""

import argparse
import yaml
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.validation.component_tests import component_test, ComponentTester
from backtest.analyze_cli import BacktestAnalyzer


def load_profile_for_component_test(profile_name: str):
    """Load profile and instantiate model."""
    # Load profiles
    profiles_path = Path('configs/profiles.yaml')
    with open(profiles_path) as f:
        profiles_data = yaml.safe_load(f)

    # Extract profiles from top-level key
    profiles = profiles_data.get('profiles', {})

    if profile_name not in profiles:
        raise ValueError(f"Profile '{profile_name}' not found in {profiles_path}")

    profile = profiles[profile_name]

    # Instantiate model using BacktestAnalyzer's method
    analyzer = BacktestAnalyzer()
    model_name = profile['model']
    parameters = profile.get('parameters', {})

    model = analyzer.instantiate_model(model_name, parameters)

    # Create temp config
    config_data = {
        'mode': 'backtest',
        'data': {
            'primary_timeframe': '1D',
            'data_dir': 'data'
        },
        'backtest': {
            'lookback_bars': profile.get('lookback_bars', 200)
        },
        'execution': {
            'initial_capital': 100000.0,
            'commission_rate': 0.001,
            'slippage_bps': 5.0
        },
        'system': {
            'reference_assets': [
                {'symbol': 'SPY', 'required': True},
                {'symbol': '^VIX', 'required': False}
            ]
        },
        'portfolio': {
            'leverage_multiplier': 1.0
        },
        'risk': {
            'max_leverage': 1.0,
            'max_position_size': 0.4,
            'max_asset_class_allocation': {
                'equity': 1.0,
                'crypto': 0.2
            },
            'max_drawdown_threshold': 0.15
        },
        'models': {
            model_name: {
                'enabled': True,
                'budget': 1.0,
                'parameters': parameters,
                'universe': profile['universe'],
                'asset_classes': ['equity']
            }
        }
    }

    # Save temp config
    temp_config_path = Path('configs/temp_component_test.yaml')
    with open(temp_config_path, 'w') as f:
        yaml.dump(config_data, f)

    return model, str(temp_config_path), profile.get('start_date'), profile.get('end_date')


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test strategy components to identify source of edge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test Standalone v3
  python -m engines.validation.component_test_cli --profile exp_standalone_v3

  # Test with more samples for higher confidence
  python -m engines.validation.component_test_cli --profile exp_standalone_v3 --samples 20

  # Test specific date range
  python -m engines.validation.component_test_cli \\
      --profile exp_standalone_v3 \\
      --start 2020-01-01 \\
      --end 2024-12-31

Interpretation:
  Entry % > 50%:  Edge comes primarily from entry timing
  Exit % > 50%:   Edge comes primarily from exit timing
  Both > 20%:     Edge comes from combination of both
  MFE/MAE > 1.5:  Good risk/reward ratio on trades

Use this to:
- Identify which component to focus improvement efforts on
- Determine if entries or exits need work
- Validate that both components contribute value
        """
    )

    parser.add_argument('--profile', type=str, required=True,
                       help='Test profile name from configs/profiles.yaml')

    parser.add_argument('--samples', type=int, default=10,
                       help='Number of random samples (default: 10)')

    parser.add_argument('--start', type=str,
                       help='Start date override (YYYY-MM-DD)')

    parser.add_argument('--end', type=str,
                       help='End date override (YYYY-MM-DD)')

    parser.add_argument('--save-results', action='store_true',
                       help='Save detailed results to file')

    args = parser.parse_args()

    # Load profile and model
    print(f"\n{'='*60}")
    print(f"COMPONENT TEST")
    print(f"{'='*60}")
    print(f"Profile: {args.profile}")
    print(f"Samples: {args.samples}")
    print(f"{'='*60}\n")

    try:
        model, config_path, default_start, default_end = load_profile_for_component_test(args.profile)

        # Use date overrides if provided
        start_date = args.start or default_start
        end_date = args.end or default_end

        print(f"Period: {start_date} to {end_date}")
        print(f"Model: {model.name}")
        print()

        # Run component test
        result = component_test(
            model=model,
            config_path=config_path,
            n_samples=args.samples,
            start_date=start_date,
            end_date=end_date
        )

        # Print interpretation
        if result.passes():
            print("\n✅ Strategy PASSED component test")
            if result.entry_pct > 50:
                print(f"   Primary edge: ENTRY timing ({result.entry_pct:.1f}%)")
            elif result.exit_pct > 50:
                print(f"   Primary edge: EXIT timing ({result.exit_pct:.1f}%)")
            else:
                print(f"   Edge from combination (Entry: {result.entry_pct:.1f}%, Exit: {result.exit_pct:.1f}%)")
            return_code = 0
        else:
            print("\n⚠️  Strategy has WEAK component contribution")
            print(f"   Entry: {result.entry_pct:.1f}%, Exit: {result.exit_pct:.1f}% (both < 20%)")
            print("   Strategy may be overfitting or relying on luck")
            return_code = 1

        # Save results if requested
        if args.save_results:
            output_dir = Path(f'results/component_tests/{args.profile}')
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = output_dir / f'component_test_{timestamp}.json'

            results_data = {
                'profile': args.profile,
                'timestamp': timestamp,
                'n_samples': args.samples,
                'period': {'start': start_date, 'end': end_date},
                'full_strategy': {
                    'cagr': result.full_strategy_cagr,
                    'sharpe': result.full_strategy_sharpe
                },
                'components': {
                    'entry_only_cagr': result.entry_only_cagr,
                    'exit_only_cagr': result.exit_only_cagr,
                    'random_both_cagr': result.random_both_cagr
                },
                'contributions': {
                    'entry_pct': result.entry_pct,
                    'exit_pct': result.exit_pct,
                    'entry_contribution': result.entry_contribution,
                    'exit_contribution': result.exit_contribution
                },
                'trade_quality': {
                    'mfe_mean': result.mfe_mean,
                    'mae_mean': result.mae_mean,
                    'mfe_mae_ratio': result.mfe_mae_ratio
                },
                'passes': result.passes()
            }

            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2)

            print(f"\n📁 Results saved to: {results_file}")

        return return_code

    except Exception as e:
        print(f"\n❌ Component test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
