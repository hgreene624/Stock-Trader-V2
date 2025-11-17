#!/usr/bin/env python3
"""
Optimization Tracker CLI

Command-line interface for viewing and managing optimization results.
"""

import argparse
from utils.optimization_tracker import OptimizationTracker


def main():
    parser = argparse.ArgumentParser(description="View optimization results")
    parser.add_argument('command', choices=['leaderboard', 'experiment', 'compare', 'export'],
                        help="Command to execute")
    parser.add_argument('--limit', type=int, default=20,
                        help="Number of results to show (default: 20)")
    parser.add_argument('--metric', default='bps',
                        choices=['bps', 'cagr', 'sharpe_ratio', 'max_drawdown'],
                        help="Metric to sort by (default: bps)")
    parser.add_argument('--experiment', type=str,
                        help="Experiment name for 'experiment' or 'export' commands")
    parser.add_argument('--experiments', nargs='+',
                        help="List of experiments for 'compare' command")
    parser.add_argument('--output', type=str,
                        help="Output path for 'export' command")

    args = parser.parse_args()

    tracker = OptimizationTracker()

    try:
        if args.command == 'leaderboard':
            print("\n" + "="*80)
            print(f"OPTIMIZATION LEADERBOARD (Top {args.limit} by {args.metric.upper()})")
            print("="*80)
            df = tracker.get_leaderboard(limit=args.limit, metric=args.metric)

            if len(df) == 0:
                print("No results found. Run some optimization experiments first!")
            else:
                # Format display
                pd_options = {
                    'display.max_rows': None,
                    'display.max_columns': None,
                    'display.width': None,
                    'display.max_colwidth': 50
                }
                import pandas as pd
                with pd.option_context(*[item for pair in pd_options.items() for item in pair]):
                    print(df.to_string(index=False))

        elif args.command == 'experiment':
            if not args.experiment:
                print("Error: --experiment required for 'experiment' command")
                return

            print("\n" + "="*80)
            print(f"RESULTS FOR EXPERIMENT: {args.experiment}")
            print("="*80)
            df = tracker.get_experiment_results(args.experiment)

            if len(df) == 0:
                print(f"No results found for experiment: {args.experiment}")
            else:
                print(f"\nTotal results: {len(df)}")
                print(f"Best BPS: {df['bps'].max():.4f}")
                print(f"Best CAGR: {df['cagr'].max():.2%}")
                print(f"Best Sharpe: {df['sharpe_ratio'].max():.2f}")
                print(f"\nTop 10 results:")
                import pandas as pd
                print(df.head(10).to_string(index=False))

        elif args.command == 'compare':
            if not args.experiments:
                print("Error: --experiments required for 'compare' command")
                print("Example: --experiments exp1 exp2 exp3")
                return

            print("\n" + "="*80)
            print(f"EXPERIMENT COMPARISON")
            print("="*80)
            df = tracker.compare_experiments(args.experiments)
            import pandas as pd
            print(df.to_string(index=False))

        elif args.command == 'export':
            if not args.experiment or not args.output:
                print("Error: --experiment and --output required for 'export' command")
                return

            tracker.export_best_parameters(args.experiment, args.output)

    finally:
        tracker.close()


if __name__ == "__main__":
    main()
