"""
Walk-Forward Optimization CLI

Usage:
    python -m engines.optimization.walk_forward_cli

This will run walk-forward optimization on the sector rotation model with sensible defaults.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.optimization.walk_forward import WalkForwardOptimizer
from models.sector_rotation_v1 import SectorRotationModel_v1


def main():
    parser = argparse.ArgumentParser(
        description="Walk-Forward Optimization for Sector Rotation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--start",
        type=str,
        default="2020-01-01",
        help="Overall start date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end",
        type=str,
        default="2024-12-31",
        help="Overall end date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--train-months",
        type=int,
        default=18,
        help="Training window size in months (default: 18)"
    )

    parser.add_argument(
        "--test-months",
        type=int,
        default=12,
        help="Test window size in months (default: 12)"
    )

    parser.add_argument(
        "--step-months",
        type=int,
        default=12,
        help="Roll-forward step size in months (default: 12)"
    )

    parser.add_argument(
        "--population",
        type=int,
        default=20,
        help="EA population size (default: 20)"
    )

    parser.add_argument(
        "--generations",
        type=int,
        default=15,
        help="EA generations (default: 15)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/base/system.yaml",
        help="System config path"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="results/walk_forward",
        help="Output directory"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test with smaller windows and fewer generations"
    )

    args = parser.parse_args()

    # Adjust for quick mode
    if args.quick:
        args.train_months = 12
        args.test_months = 6
        args.step_months = 6
        args.population = 10
        args.generations = 10
        print("\n🚀 QUICK MODE: Using shorter windows and fewer generations for faster testing\n")

    # Parameter ranges for sector rotation
    param_ranges = {
        "momentum_period": (60, 200),    # 60 to 200 days
        "min_momentum": (0.0, 0.15),     # 0% to 15% minimum momentum
        "top_n": (2, 4),                 # Top 2-4 sectors (will round to int)
    }

    print(f"\nModel: SectorRotationModel_v1")
    print(f"Parameter Ranges: {param_ranges}")
    print(f"Period: {args.start} to {args.end}")
    print(f"Windows: {args.train_months}-month train, {args.test_months}-month test, {args.step_months}-month step")
    print(f"EA: {args.population} population, {args.generations} generations")

    # Create optimizer
    optimizer = WalkForwardOptimizer(
        model_class=SectorRotationModel_v1,
        param_ranges=param_ranges,
        train_period_months=args.train_months,
        test_period_months=args.test_months,
        step_months=args.step_months,
        population_size=args.population,
        generations=args.generations
    )

    # Run walk-forward optimization
    results = optimizer.run(
        start_date=args.start,
        end_date=args.end,
        config_path=args.config,
        output_dir=args.output
    )

    # Print final summary
    print(f"\n{'='*80}")
    print(f"FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Number of windows: {results['summary']['num_windows']}")
    print(f"\nPerformance:")
    print(f"  In-Sample CAGR:     {results['summary']['avg_in_sample_cagr']:.2%}")
    print(f"  Out-of-Sample CAGR: {results['summary']['avg_out_of_sample_cagr']:.2%}")
    print(f"  Degradation:        {results['summary']['performance_degradation']:.2%}")

    degradation = results['summary']['performance_degradation']
    if degradation < 0.02:
        print(f"\n✅ Low degradation ({degradation:.2%}) - strategy generalizes well!")
    elif degradation < 0.05:
        print(f"\n⚠️  Moderate degradation ({degradation:.2%}) - some overfitting present")
    else:
        print(f"\n❌ High degradation ({degradation:.2%}) - severe overfitting, use baseline params!")

    print(f"\nRecommended Parameters (mean across windows):")
    for param, stats in results['summary']['parameter_stability'].items():
        if param == 'top_n':
            print(f"  {param}: {int(round(stats['mean']))}")
        else:
            print(f"  {param}: {stats['mean']:.4f}")

    print(f"\n📁 Full results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
