"""
Monkey Test CLI

Run monkey tests to validate if strategies have genuine edge beyond random chance.

Usage:
    # Test a profile
    python -m engines.validation.monkey_test_cli --profile exp_standalone_v3

    # Test with custom variants
    python -m engines.validation.monkey_test_cli --profile exp_standalone_v3 --variants 5000

    # Test specific date range
    python -m engines.validation.monkey_test_cli \\
        --profile exp_standalone_v3 \\
        --start 2020-01-01 \\
        --end 2024-12-31 \\
        --variants 1000

Validation Criteria (from "Building Algorithmic Trading Systems"):
- Strategy must beat >90% of random variants to pass
- p-value < 0.10 for statistical significance
- Run periodically (every 6-12 months) to detect fading edges
"""

import argparse
import yaml
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.validation.monkey_tests import monkey_test, MonkeyTester
from backtest.analyze_cli import BacktestAnalyzer


def load_profile_for_monkey_test(profile_name: str):
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
    temp_config_path = Path('configs/temp_monkey_test.yaml')
    with open(temp_config_path, 'w') as f:
        yaml.dump(config_data, f)

    return model, str(temp_config_path), profile.get('start_date'), profile.get('end_date')


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run monkey tests to validate strategy edge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test Standalone v3 with 1000 random variants
  python -m engines.validation.monkey_test_cli --profile exp_standalone_v3

  # Test with more variants for higher confidence
  python -m engines.validation.monkey_test_cli --profile exp_standalone_v3 --variants 5000

  # Test specific date range
  python -m engines.validation.monkey_test_cli \\
      --profile exp_standalone_v3 \\
      --start 2020-01-01 \\
      --end 2024-12-31

Validation Criteria:
  ✅ PASS: Beat >90% of random variants (p < 0.10)
  ❌ FAIL: Beat <90% of random variants

Strategy should be retested every 6-12 months to detect fading edges.
        """
    )

    parser.add_argument('--profile', type=str, required=True,
                       help='Test profile name from configs/profiles.yaml')

    parser.add_argument('--variants', type=int, default=1000,
                       help='Number of random variants to test (default: 1000)')

    parser.add_argument('--variant-type', type=str, default='selection',
                       choices=['selection', 'entries', 'exits', 'full'],
                       help='Type of randomization (default: selection)')

    parser.add_argument('--start', type=str,
                       help='Start date override (YYYY-MM-DD)')

    parser.add_argument('--end', type=str,
                       help='End date override (YYYY-MM-DD)')

    parser.add_argument('--save-results', action='store_true',
                       help='Save detailed results to file')

    args = parser.parse_args()

    # Load profile and model
    print(f"\n{'='*60}")
    print(f"MONKEY TEST VALIDATION")
    print(f"{'='*60}")
    print(f"Profile: {args.profile}")
    print(f"Variants: {args.variants}")
    print(f"Type: {args.variant_type}")
    print(f"{'='*60}\n")

    try:
        model, config_path, default_start, default_end = load_profile_for_monkey_test(args.profile)

        # Use date overrides if provided
        start_date = args.start or default_start
        end_date = args.end or default_end

        print(f"Period: {start_date} to {end_date}")
        print(f"Model: {model.name}")
        print()

        # Run monkey test
        result = monkey_test(
            model=model,
            config_path=config_path,
            n_variants=args.variants,
            variant_type=args.variant_type,
            start_date=start_date,
            end_date=end_date
        )

        # Print result (already done by monkey_test, but also return code)
        if result.passes():
            print("\n✅ Strategy PASSED monkey test validation")
            print(f"   Beat {result.beat_pct*100:.1f}% of random variants (target: >90%)")
            return_code = 0
        else:
            print("\n❌ Strategy FAILED monkey test validation")
            print(f"   Only beat {result.beat_pct*100:.1f}% of random variants (target: >90%)")
            print("   Strategy may not have genuine edge beyond random chance")
            return_code = 1

        # Save results if requested
        if args.save_results:
            output_dir = Path(f'results/monkey_tests/{args.profile}')
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            results_file = output_dir / f'monkey_test_{timestamp}.json'

            results_data = {
                'profile': args.profile,
                'timestamp': timestamp,
                'n_variants': args.variants,
                'variant_type': args.variant_type,
                'period': {'start': start_date, 'end': end_date},
                'real_strategy': {
                    'cagr': result.real_cagr,
                    'sharpe': result.real_sharpe,
                    'max_dd': result.real_max_dd
                },
                'random_baselines': {
                    'cagr_mean': float(sum(result.random_cagrs) / len(result.random_cagrs)),
                    'cagr_std': float((sum((x - sum(result.random_cagrs)/len(result.random_cagrs))**2 for x in result.random_cagrs) / len(result.random_cagrs))**0.5)
                },
                'validation': {
                    'percentile': result.percentile,
                    'beat_pct': result.beat_pct,
                    'p_value': result.p_value,
                    'passes': result.passes()
                }
            }

            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2)

            print(f"\n📁 Results saved to: {results_file}")

        return return_code

    except Exception as e:
        print(f"\n❌ Monkey test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
