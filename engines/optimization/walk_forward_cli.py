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
        "--mutation-rate",
        type=float,
        default=0.2,
        help="EA mutation rate (default: 0.2)"
    )

    parser.add_argument(
        "--crossover-rate",
        type=float,
        default=0.7,
        help="EA crossover rate (default: 0.7)"
    )

    parser.add_argument(
        "--elitism-count",
        type=int,
        default=2,
        help="Number of elite individuals to carry over each generation (default: 2)"
    )

    parser.add_argument(
        "--tournament-size",
        type=int,
        default=3,
        help="Tournament size for parent selection (default: 3)"
    )

    parser.add_argument(
        "--mutation-strength",
        type=float,
        default=0.1,
        help="Fraction of parameter range used for Gaussian mutation (default: 0.1)"
    )

    parser.add_argument(
        "--ea-seed",
        type=int,
        default=None,
        help="Random seed for the evolutionary optimizer"
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

    parser.add_argument(
        "--new-tab",
        action="store_true",
        help="[macOS only] Launch in new Terminal tab for real-time progress monitoring"
    )

    parser.add_argument(
        "--n-jobs",
        type=int,
        default=None,
        help="Number of parallel processes (default: CPU cores - 1). Use 1 for sequential."
    )

    parser.add_argument(
        "--max-windows",
        type=int,
        default=None,
        help="Limit to the first N walk-forward windows"
    )

    parser.add_argument(
        "--param-range",
        action="append",
        default=[],
        metavar="NAME=MIN:MAX",
        help="Override parameter ranges (repeat per parameter). Example: momentum_period=80:160"
    )

    args = parser.parse_args()

    # Handle --new-tab: relaunch in new terminal tab
    if args.new_tab:
        import os
        import subprocess

        # Build command without --new-tab flag
        cmd_args = [arg for arg in sys.argv[1:] if arg != "--new-tab"]
        command = f"python3 -m engines.optimization.walk_forward_cli {' '.join(cmd_args)}"

        project_dir = Path(__file__).parent.parent.parent

        # AppleScript to open new tab
        applescript = f'''
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "cd '{project_dir}' && source .venv/bin/activate && echo '🔬 Walk-Forward Optimization Starting...' && echo '' && {command}" in front window
end tell
'''

        print("🚀 Launching in new Terminal tab...")
        print(f"📊 Command: {command}")
        subprocess.run(['osascript', '-e', applescript])
        print("✅ Launched! Check the new tab for real-time progress.")
        return 0

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

    if args.param_range:
        param_types = {
            name: "int" if isinstance(bounds[0], int) and isinstance(bounds[1], int) else "float"
            for name, bounds in param_ranges.items()
        }
        for override in args.param_range:
            if "=" not in override or ":" not in override:
                parser.error(f"Invalid --param-range '{override}'. Expected format NAME=MIN:MAX.")
            name, range_spec = override.split("=", 1)
            min_str, max_str = range_spec.split(":", 1)
            name = name.strip()
            if name not in param_ranges:
                parser.error(f"Unknown parameter '{name}' for --param-range.")
            try:
                min_val = float(min_str)
                max_val = float(max_str)
            except ValueError as exc:
                parser.error(f"Invalid numeric values in --param-range '{override}': {exc}")
            if min_val > max_val:
                parser.error(f"Min must be <= max in --param-range '{override}'.")

            if param_types[name] == "int":
                param_ranges[name] = (int(min_val), int(max_val))
            else:
                param_ranges[name] = (min_val, max_val)

    print(f"\nModel: SectorRotationModel_v1")
    print(f"Parameter Ranges: {param_ranges}")
    print(f"Period: {args.start} to {args.end}")
    print(f"Windows: {args.train_months}-month train, {args.test_months}-month test, {args.step_months}-month step")
    print(
        "EA: "
        f"population={args.population}, "
        f"generations={args.generations}, "
        f"mutation_rate={args.mutation_rate}, "
        f"crossover_rate={args.crossover_rate}, "
        f"elitism={args.elitism_count}, "
        f"tournament_size={args.tournament_size}, "
        f"mutation_strength={args.mutation_strength}"
    )
    if args.max_windows:
        print(f"Limiting to first {args.max_windows} windows")

    # Create optimizer
    optimizer = WalkForwardOptimizer(
        model_class=SectorRotationModel_v1,
        param_ranges=param_ranges,
        train_period_months=args.train_months,
        test_period_months=args.test_months,
        step_months=args.step_months,
        population_size=args.population,
        generations=args.generations,
        n_jobs=args.n_jobs,
        mutation_rate=args.mutation_rate,
        crossover_rate=args.crossover_rate,
        elitism_count=args.elitism_count,
        tournament_size=args.tournament_size,
        mutation_strength=args.mutation_strength,
        seed=args.ea_seed,
        max_windows=args.max_windows
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
