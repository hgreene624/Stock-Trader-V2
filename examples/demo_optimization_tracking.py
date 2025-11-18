#!/usr/bin/env python3
"""
Demo: Optimization Results Tracking

Shows how to use the OptimizationTracker to save and query results.
"""

import sys
sys.path.append('..')

from utils.optimization_tracker import OptimizationTracker

def demo():
    """Demonstrate optimization tracking features."""

    print("\n" + "="*80)
    print("OPTIMIZATION TRACKING DEMO")
    print("="*80)

    # Initialize tracker
    tracker = OptimizationTracker()

    # Example 1: Log an experiment (manually for demo)
    print("\n1️⃣  Logging optimization experiment...")
    exp_id = tracker.log_experiment(
        name="sector_rotation_leverage_test_2025-11-17",
        method="manual",
        model="SectorRotationModel_v1",
        backtest_period="2020-2024",
        total_runs=3,
        best_metric=0.87,
        metric_name="bps"
    )
    print(f"   ✓ Experiment logged with ID: {exp_id}")

    # Example 2: Log results
    print("\n2️⃣  Logging test results...")

    # Result 1: Baseline
    tracker.log_result(
        experiment_id=exp_id,
        parameters={'momentum_period': 126, 'top_n': 3, 'min_momentum': 0.0, 'target_leverage': 1.0},
        metrics={
            'cagr': 0.1169,
            'sharpe_ratio': 1.98,
            'max_drawdown': -0.3064,
            'total_return': 0.7346,
            'win_rate': 0.50,
            'bps': 0.69,
            'total_trades': 3325,
            'final_nav': 171107
        },
        validation_period="full",
        notes="Baseline - no leverage"
    )

    # Result 2: With leverage
    tracker.log_result(
        experiment_id=exp_id,
        parameters={'momentum_period': 126, 'top_n': 3, 'min_momentum': 0.0, 'target_leverage': 1.25},
        metrics={
            'cagr': 0.1487,
            'sharpe_ratio': 1.91,
            'max_drawdown': -0.3593,
            'total_return': 1.0190,
            'win_rate': 0.50,
            'bps': 0.87,
            'total_trades': 3325,
            'final_nav': 201548
        },
        validation_period="full",
        notes="With 1.25x leverage - BEATS SPY!"
    )

    # Result 3: EA optimized
    tracker.log_result(
        experiment_id=exp_id,
        parameters={'momentum_period': 77, 'top_n': 3, 'min_momentum': 0.044, 'target_leverage': 1.0},
        metrics={
            'cagr': 0.1139,
            'sharpe_ratio': 1.90,
            'max_drawdown': -0.2906,
            'total_return': 0.7136,
            'win_rate': 0.50,
            'bps': 0.86,
            'total_trades': 3325,
            'final_nav': 171107
        },
        validation_period="full",
        notes="EA optimized parameters (77d momentum, 4.4% min)"
    )

    print("   ✓ 3 results logged")

    # Example 3: Query leaderboard
    print("\n3️⃣  Viewing leaderboard...")
    df = tracker.get_leaderboard(limit=10)
    print(df[['experiment', 'cagr', 'sharpe_ratio', 'bps', 'validation_period']].to_string(index=False))

    # Example 4: Export best parameters
    print("\n4️⃣  Exporting best parameters...")
    tracker.export_best_parameters(
        experiment_name="sector_rotation_leverage_test_2025-11-17",
        output_path="results/best_params_demo.json"
    )

    # Clean up
    tracker.close()

    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print("\nYou can now use the CLI to query results:")
    print("  python3 -m utils.optimization_tracker_cli leaderboard --limit 10")
    print("  python3 -m utils.optimization_tracker_cli experiment --experiment sector_rotation_leverage_test_2025-11-17")
    print("  python3 -m utils.optimization_tracker_cli export --experiment my_exp --output results/best.json")
    print()


if __name__ == "__main__":
    demo()
