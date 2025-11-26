"""
Data Burn Tracker CLI

Track and manage data usage to prevent contamination.

Usage:
    # Check if period is burned
    python -m engines.validation.data_burn_cli check \
        --model SectorRotationModel_v1 \
        --start 2020-01-01 \
        --end 2024-12-31

    # Record a test
    python -m engines.validation.data_burn_cli record \
        --model SectorRotationModel_v1 \
        --type backtest \
        --start 2020-01-01 \
        --end 2024-12-31 \
        --description "Initial baseline test"

    # View burn log
    python -m engines.validation.data_burn_cli log

    # View log for specific model
    python -m engines.validation.data_burn_cli log --model SectorRotationModel_v1

    # Get available periods
    python -m engines.validation.data_burn_cli available --model SectorRotationModel_v1
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.validation.data_burn import DataBurnTracker, get_tracker


def cmd_check(args):
    """Check if a period is burned."""
    tracker = get_tracker()

    is_burned, overlapping = tracker.is_burned(
        model_name=args.model,
        start_date=args.start,
        end_date=args.end
    )

    if is_burned:
        print(f"\n⚠️  Period {args.start} to {args.end} is BURNED")
        print(f"Model: {args.model}\n")
        print("Overlapping tests:")
        for record in overlapping:
            print(f"  - [{record.timestamp[:10]}] {record.test_type}")
            print(f"    Period: {record.start_date} to {record.end_date}")
            print(f"    Description: {record.description}")
            print()
        print("⚠️  Using burned data may lead to overfitting!\n")
        return 1
    else:
        print(f"\n✅ Period {args.start} to {args.end} is CLEAN (not burned)")
        print(f"Model: {args.model}\n")
        return 0


def cmd_record(args):
    """Record a test."""
    tracker = get_tracker()

    tracker.record_test(
        model_name=args.model,
        test_type=args.type,
        start_date=args.start,
        end_date=args.end,
        description=args.description,
        operator=args.operator
    )

    print(f"\n✅ Recorded test:")
    print(f"   Model: {args.model}")
    print(f"   Type: {args.type}")
    print(f"   Period: {args.start} to {args.end}")
    print(f"   Description: {args.description}\n")
    return 0


def cmd_log(args):
    """View burn log."""
    tracker = get_tracker()
    tracker.print_summary(model_name=args.model)
    return 0


def cmd_available(args):
    """Show available (unburned) periods."""
    tracker = get_tracker()

    available = tracker.get_available_periods(
        model_name=args.model,
        full_range_start=args.range_start,
        full_range_end=args.range_end,
        min_period_days=args.min_days
    )

    print(f"\n{'='*60}")
    print(f"AVAILABLE (UNBURNED) PERIODS")
    print(f"Model: {args.model}")
    print(f"{'='*60}\n")

    if available:
        for start, end in available:
            print(f"  {start} to {end}")
        print(f"\n{len(available)} period(s) available\n")
    else:
        print("  ⚠️  No unburned periods available!")
        print("  All data has been used for testing.\n")

    return 0


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Data Burn Tracker - Prevent data contamination",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check if period is burned')
    check_parser.add_argument('--model', type=str, required=True,
                             help='Model name')
    check_parser.add_argument('--start', type=str, required=True,
                             help='Start date (YYYY-MM-DD)')
    check_parser.add_argument('--end', type=str, required=True,
                             help='End date (YYYY-MM-DD)')

    # Record command
    record_parser = subparsers.add_parser('record', help='Record a test')
    record_parser.add_argument('--model', type=str, required=True,
                              help='Model name')
    record_parser.add_argument('--type', type=str, required=True,
                              choices=['backtest', 'optimization', 'monkey_test', 'component_test', 'validation'],
                              help='Test type')
    record_parser.add_argument('--start', type=str, required=True,
                              help='Start date (YYYY-MM-DD)')
    record_parser.add_argument('--end', type=str, required=True,
                              help='End date (YYYY-MM-DD)')
    record_parser.add_argument('--description', type=str, required=True,
                              help='Brief description of test')
    record_parser.add_argument('--operator', type=str, default='agent',
                              help='Who ran the test (default: agent)')

    # Log command
    log_parser = subparsers.add_parser('log', help='View burn log')
    log_parser.add_argument('--model', type=str,
                           help='Filter by model name')

    # Available command
    available_parser = subparsers.add_parser('available', help='Show available periods')
    available_parser.add_argument('--model', type=str, required=True,
                                 help='Model name')
    available_parser.add_argument('--range-start', type=str, default='2010-01-01',
                                 help='Start of full data range (default: 2010-01-01)')
    available_parser.add_argument('--range-end', type=str,
                                 help='End of full data range (default: today)')
    available_parser.add_argument('--min-days', type=int, default=365,
                                 help='Minimum period length in days (default: 365)')

    args = parser.parse_args()

    if args.command == 'check':
        return cmd_check(args)
    elif args.command == 'record':
        return cmd_record(args)
    elif args.command == 'log':
        return cmd_log(args)
    elif args.command == 'available':
        return cmd_available(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
