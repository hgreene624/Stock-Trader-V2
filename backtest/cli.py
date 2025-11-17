"""
Backtest CLI

Command-line interface for running backtests.

Commands:
- run: Run a backtest
- results: View backtest results

Example:
    python -m backtest.cli run --config configs/base/system.yaml --model EquityTrendModel_v1
"""

import argparse
import sys
from pathlib import Path
sys.path.append('..')
from backtest.runner import BacktestRunner
from models.equity_trend_v1 import EquityTrendModel_v1
from utils.logging import StructuredLogger


def run_backtest(args):
    """Run a backtest."""
    logger = StructuredLogger()

    # Initialize model
    if args.model == "EquityTrendModel_v1":
        model = EquityTrendModel_v1()
    else:
        raise ValueError(
            f"Unknown model: {args.model}. "
            f"Available models: EquityTrendModel_v1"
        )

    # Create runner
    runner = BacktestRunner(args.config, logger=logger)

    # Run backtest
    try:
        results = runner.run(
            model=model,
            start_date=args.start,
            end_date=args.end
        )

        # Print results
        print("\n" + "=" * 70)
        print("BACKTEST RESULTS")
        print("=" * 70)

        print(f"\nModel: {results['model_id']}")
        print(f"Period: {results['start_date']} to {results['end_date']}")

        # Performance metrics
        print("\n" + "-" * 70)
        print("PERFORMANCE METRICS")
        print("-" * 70)

        metrics = results['metrics']

        print(f"\nReturns:")
        print(f"  Total Return:     {metrics['total_return']:>10.2%}")
        print(f"  CAGR:             {metrics['cagr']:>10.2%}")

        print(f"\nRisk Metrics:")
        print(f"  Max Drawdown:     {metrics['max_drawdown']:>10.2%}")
        print(f"  Sharpe Ratio:     {metrics['sharpe_ratio']:>10.2f}")

        print(f"\nTrading Metrics:")
        print(f"  Total Trades:     {metrics['total_trades']:>10}")
        print(f"  Win Rate:         {metrics['win_rate']:>10.2%}")

        print(f"\nBalanced Performance Score (BPS):")
        print(f"  BPS:              {metrics['bps']:>10.4f}")

        print(f"\nNAV:")
        print(f"  Initial NAV:      ${metrics['initial_nav']:>10,.2f}")
        print(f"  Final NAV:        ${metrics['final_nav']:>10,.2f}")

        # Trade log summary
        print("\n" + "-" * 70)
        print("TRADE LOG SUMMARY")
        print("-" * 70)

        trade_log = results['trade_log']

        if len(trade_log) > 0:
            print(f"\nTotal Trades: {len(trade_log)}")

            # Group by symbol
            by_symbol = trade_log.groupby('symbol').agg({
                'quantity': 'count',
                'gross_value': 'sum',
                'commission': 'sum'
            })

            print("\nTrades by Symbol:")
            print(f"{'Symbol':<10} {'Count':>8} {'Value':>15} {'Commission':>12}")
            print("-" * 50)
            for symbol, row in by_symbol.iterrows():
                print(f"{symbol:<10} {int(row['quantity']):>8} "
                      f"${row['gross_value']:>14,.2f} "
                      f"${row['commission']:>11,.2f}")

            # Show first and last 5 trades
            print("\nFirst 5 Trades:")
            print(trade_log.head(5)[['timestamp', 'symbol', 'side', 'quantity', 'price', 'commission']].to_string(index=False))

            if len(trade_log) > 10:
                print("\nLast 5 Trades:")
                print(trade_log.tail(5)[['timestamp', 'symbol', 'side', 'quantity', 'price', 'commission']].to_string(index=False))
        else:
            print("\nNo trades executed")

        # NAV curve summary
        print("\n" + "-" * 70)
        print("NAV CURVE")
        print("-" * 70)

        nav_series = results['nav_series']

        print(f"\nData Points: {len(nav_series)}")
        print(f"Start: {nav_series.index[0]} → ${nav_series.iloc[0]:,.2f}")
        print(f"End:   {nav_series.index[-1]} → ${nav_series.iloc[-1]:,.2f}")

        # Show monthly stats if available
        if len(nav_series) > 0:
            monthly = nav_series.resample('M').last()
            monthly_returns = monthly.pct_change().dropna()

            if len(monthly_returns) > 0:
                print(f"\nMonthly Returns:")
                print(f"  Mean:     {monthly_returns.mean():>8.2%}")
                print(f"  Std Dev:  {monthly_returns.std():>8.2%}")
                print(f"  Best:     {monthly_returns.max():>8.2%}")
                print(f"  Worst:    {monthly_returns.min():>8.2%}")

        print("\n" + "=" * 70)

        # Save results if requested
        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save NAV series
            nav_path = output_dir / "nav_series.csv"
            nav_series.to_csv(nav_path)
            print(f"\nSaved NAV series to {nav_path}")

            # Save trade log
            if len(trade_log) > 0:
                trade_path = output_dir / "trade_log.csv"
                trade_log.to_csv(trade_path, index=False)
                print(f"Saved trade log to {trade_path}")

            # Save metrics
            import json
            metrics_path = output_dir / "metrics.json"
            with open(metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2)
            print(f"Saved metrics to {metrics_path}")

        print("\n✓ Backtest complete")

    except Exception as e:
        print(f"\n✗ Backtest failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Backtest CLI for algorithmic trading platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run backtest with default dates from config
  python -m backtest.cli run --config configs/base/system.yaml

  # Run backtest for specific period
  python -m backtest.cli run --config configs/base/system.yaml --start 2023-01-01 --end 2024-01-01

  # Run and save results
  python -m backtest.cli run --config configs/base/system.yaml --output results/equity_trend_v1
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run a backtest')
    run_parser.add_argument(
        '--config',
        required=True,
        help='Path to config file (e.g., configs/base/system.yaml)'
    )
    run_parser.add_argument(
        '--model',
        default='EquityTrendModel_v1',
        help='Model to backtest (default: EquityTrendModel_v1)'
    )
    run_parser.add_argument(
        '--start',
        help='Start date (YYYY-MM-DD), overrides config'
    )
    run_parser.add_argument(
        '--end',
        help='End date (YYYY-MM-DD), overrides config'
    )
    run_parser.add_argument(
        '--output',
        help='Output directory for results'
    )
    run_parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if args.command == 'run':
        run_backtest(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
