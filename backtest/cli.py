"""
Backtest CLI

Command-line interface for running backtests and managing model lifecycle.

Commands:
- run: Run a backtest
- results: View backtest results
- promote: Promote model to next lifecycle stage
- demote: Demote model to previous lifecycle stage
- list-models: List all models with their lifecycle stages

Example:
    python -m backtest.cli run --config configs/base/system.yaml --model EquityTrendModel_v1
    python -m backtest.cli promote --model EquityTrendModel_v1 --reason "Passed backtest criteria"
"""

import argparse
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
sys.path.append('..')
from backtest.runner import BacktestRunner
from models.equity_trend_v1 import EquityTrendModel_v1
from utils.logging import StructuredLogger
from utils.config import ConfigLoader


def load_profile(profile_name: str) -> dict:
    """
    Load a test profile from configs/profiles.yaml.

    Args:
        profile_name: Name of the profile to load

    Returns:
        Dictionary with profile configuration
    """
    profiles_path = Path("configs/profiles.yaml")

    if not profiles_path.exists():
        raise FileNotFoundError(
            f"Profiles file not found: {profiles_path}\n"
            f"Create it with pre-configured test scenarios."
        )

    with open(profiles_path) as f:
        config = yaml.safe_load(f)

    profiles = config.get('profiles', {})

    if profile_name not in profiles:
        available = ', '.join(profiles.keys())
        raise ValueError(
            f"Profile '{profile_name}' not found.\n"
            f"Available profiles: {available}"
        )

    return profiles[profile_name]


def check_and_download_data(symbols: list, start_date: str, asset_class: str = "equity"):
    """
    Check if data exists for symbols, download if missing.

    Args:
        symbols: List of ticker symbols
        start_date: Start date (YYYY-MM-DD)
        asset_class: Asset class (equity or crypto)
    """
    # Map to plural directory names
    dir_map = {"equity": "equities", "crypto": "cryptos"}
    data_dir = Path("data") / dir_map.get(asset_class, asset_class + "s")

    if not data_dir.exists():
        print(f"\n📦 Data directory not found, creating: {data_dir}")
        data_dir.mkdir(parents=True, exist_ok=True)

    missing_symbols = []

    for symbol in symbols:
        # Check for both 1D and 4H data files
        symbol_safe = symbol.replace('/', '-')
        daily_file = data_dir / f"{symbol_safe}_1D.parquet"
        h4_file = data_dir / f"{symbol_safe}_4H.parquet"

        if not daily_file.exists() or not h4_file.exists():
            missing_symbols.append(symbol)

    if missing_symbols:
        print(f"\n📥 Missing data for: {', '.join(missing_symbols)}")
        print(f"   Attempting auto-download...")

        try:
            # Try to import and use data CLI
            import subprocess

            cmd = [
                sys.executable, "-m", "engines.data.cli", "download",
                "--symbols"] + missing_symbols + [
                "--asset-class", asset_class,
                "--timeframes", "1D", "4H",
                "--start", start_date
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"\n⚠️  Auto-download failed. Please download manually:")
                print(f"   {sys.executable} -m engines.data.cli download \\")
                print(f"       --symbols {' '.join(missing_symbols)} \\")
                print(f"       --asset-class {asset_class} \\")
                print(f"       --timeframes 1D 4H \\")
                print(f"       --start {start_date}")
                print(f"\n   Error: {result.stderr}")
                print(f"\n   NOTE: The data CLI stub needs full implementation.")
                print(f"   See engines/data/cli.py")
                sys.exit(1)
            else:
                print(f"   ✓ Data downloaded successfully")

        except Exception as e:
            print(f"\n⚠️  Auto-download not available: {e}")
            print(f"   Please download data manually:")
            print(f"   {sys.executable} -m engines.data.cli download \\")
            print(f"       --symbols {' '.join(missing_symbols)} \\")
            print(f"       --asset-class {asset_class} \\")
            print(f"       --timeframes 1D 4H \\")
            print(f"       --start {start_date}")
            print(f"\n   NOTE: The data CLI needs to be fully implemented.")
            print(f"   See engines/data/cli.py for the stub.")
            sys.exit(1)
    else:
        print(f"✓ Data already available for: {', '.join(symbols)}")


def save_last_run(results: dict, config_info: dict):
    """
    Save information about the last backtest run for quick viewing.

    Args:
        results: Backtest results dictionary
        config_info: Configuration information
    """
    last_run_file = Path("results/.last_run.json")
    last_run_file.parent.mkdir(parents=True, exist_ok=True)

    # Handle both single and multi-model results
    model_names = results.get('model_ids', results.get('model_id', 'Unknown'))
    if isinstance(model_names, list):
        model_names = ', '.join(model_names)

    last_run = {
        "timestamp": datetime.now().isoformat(),
        "model": model_names,
        "start_date": results.get('start_date', 'N/A'),
        "end_date": results.get('end_date', 'N/A'),
        "config": config_info,
        "metrics": results.get('metrics', {}),
        "trade_count": len(results.get('trade_log', [])),
        "nav_series_path": str(Path("results") / "nav_series.csv"),
        "trade_log_path": str(Path("results") / "trade_log.csv")
    }

    with open(last_run_file, 'w') as f:
        json.dump(last_run, f, indent=2)


def show_last_run():
    """Display results from the last backtest run."""
    last_run_file = Path("results/.last_run.json")

    if not last_run_file.exists():
        print("No previous backtest run found.")
        print("Run a backtest first with: python -m backtest.cli run ...")
        return

    with open(last_run_file) as f:
        last_run = json.load(f)

    metrics = last_run.get('metrics', {})

    print("\n" + "=" * 80)
    print("LAST BACKTEST RUN")
    print("=" * 80)

    print(f"\nRun Time:    {last_run.get('timestamp', 'N/A')}")
    print(f"Model:       {last_run.get('model', 'N/A')}")
    print(f"Period:      {last_run.get('start_date', 'N/A')} to {last_run.get('end_date', 'N/A')}")

    # Config info
    config_info = last_run.get('config', {})
    if config_info:
        print(f"\nConfiguration:")
        if 'profile' in config_info:
            print(f"  Profile:   {config_info['profile']}")
        if 'config_file' in config_info:
            print(f"  Config:    {config_info['config_file']}")

    # Performance metrics
    print("\n" + "-" * 80)
    print("PERFORMANCE SUMMARY")
    print("-" * 80)

    print(f"\nReturns:")
    print(f"  Total Return:     {metrics.get('total_return', 0):>10.2%}")
    print(f"  CAGR:             {metrics.get('cagr', 0):>10.2%}")

    print(f"\nRisk Metrics:")
    print(f"  Max Drawdown:     {metrics.get('max_drawdown', 0):>10.2%}")
    print(f"  Sharpe Ratio:     {metrics.get('sharpe_ratio', 0):>10.2f}")

    print(f"\nTrading Metrics:")
    print(f"  Total Trades:     {last_run.get('trade_count', 0):>10}")
    print(f"  Win Rate:         {metrics.get('win_rate', 0):>10.2%}")

    print(f"\nBalanced Performance Score:")
    print(f"  BPS:              {metrics.get('bps', 0):>10.4f}")

    print(f"\nNAV:")
    print(f"  Initial NAV:      ${metrics.get('initial_nav', 0):>10,.2f}")
    print(f"  Final NAV:        ${metrics.get('final_nav', 0):>10,.2f}")

    print("\n" + "=" * 80)
    print(f"\nFull results saved in: results/")
    print("=" * 80 + "\n")


def run_backtest(args):
    """Run a backtest."""
    logger = StructuredLogger()

    # Track configuration for saving
    config_info = {}

    # Handle profile-based configuration
    if hasattr(args, 'profile') and args.profile:
        print(f"\n📋 Loading profile: {args.profile}")
        profile = load_profile(args.profile)

        config_info['profile'] = args.profile
        config_info['profile_description'] = profile.get('description', '')

        # Extract profile settings
        model_name = profile.get('model', 'EquityTrendModel_v1')
        universe = profile.get('universe', [])
        start_date = args.start or profile.get('start_date')
        end_date = args.end or profile.get('end_date')
        parameters = profile.get('parameters', {})

        # Check for data and auto-download if needed
        if universe and start_date and not args.no_download:
            asset_class = "crypto" if any('-' in s or '/' in s for s in universe) else "equity"
            check_and_download_data(universe, start_date, asset_class)

        # Use profile's config or fall back to provided config
        config_path = args.config or "configs/base/system.yaml"

        print(f"   Model: {model_name}")
        print(f"   Universe: {', '.join(universe)}")
        print(f"   Period: {start_date} to {end_date}")

    else:
        # Traditional config-based approach
        if not args.config:
            print("Error: Either --profile or --config must be specified")
            sys.exit(1)

        config_path = args.config
        config_info['config_file'] = config_path

        model_name = args.model
        start_date = args.start
        end_date = args.end

        # Load config to extract universe for data checking
        config = ConfigLoader.load_yaml(config_path)
        models_config = config.get('models', {})

        if model_name in models_config:
            universe = models_config[model_name].get('universe', [])
            if universe and start_date and not args.no_download:
                asset_class = "crypto" if any('-' in s or '/' in s for s in universe) else "equity"
                check_and_download_data(universe, start_date, asset_class)

    # Set smart defaults for dates if not specified
    if not start_date:
        # Default to 5 years back
        start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
        print(f"\n📅 Using default start date: {start_date}")

    if not end_date:
        # Default to today
        end_date = datetime.now().strftime('%Y-%m-%d')
        print(f"📅 Using default end date: {end_date}")

    # Initialize model
    if model_name == "EquityTrendModel_v1":
        model = EquityTrendModel_v1()
    else:
        raise ValueError(
            f"Unknown model: {model_name}. "
            f"Available models: EquityTrendModel_v1"
        )

    # Create runner
    runner = BacktestRunner(config_path, logger=logger)

    # Run backtest
    try:
        print(f"\n🚀 Starting backtest...")

        results = runner.run(
            model=model,
            start_date=start_date,
            end_date=end_date
        )

        # Print results
        print("\n" + "=" * 70)
        print("BACKTEST RESULTS")
        print("=" * 70)

        # Handle both single and multi-model results
        model_names = results.get('model_ids', results.get('model_id', 'Unknown'))
        if isinstance(model_names, list):
            model_names = ', '.join(model_names)

        print(f"\nModel(s): {model_names}")
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
            monthly = nav_series.resample('ME').last()
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

        # Save last run info for quick viewing
        save_last_run(results, config_info)

        print("\n✓ Backtest complete")
        print(f"\n💡 View this run anytime with: python -m backtest.cli show-last")

    except Exception as e:
        print(f"\n✗ Backtest failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def get_lifecycle_log_path():
    """Get path to lifecycle events log file."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir / "model_lifecycle_events.jsonl"


def log_lifecycle_event(model_name: str, from_stage: str, to_stage: str, reason: str, operator: str = "system"):
    """
    Log a lifecycle transition event.

    Args:
        model_name: Name of the model
        from_stage: Previous lifecycle stage
        to_stage: New lifecycle stage
        reason: Reason for transition
        operator: User or system performing the transition
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "model_name": model_name,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "reason": reason,
        "operator": operator
    }

    log_path = get_lifecycle_log_path()
    with open(log_path, 'a') as f:
        f.write(json.dumps(event) + '\n')

    return event


def validate_promotion_criteria(model_name: str, from_stage: str, to_stage: str, force: bool = False) -> tuple[bool, str]:
    """
    Validate that model meets criteria for promotion.

    Args:
        model_name: Name of the model
        from_stage: Current lifecycle stage
        to_stage: Target lifecycle stage
        force: Skip validation checks

    Returns:
        Tuple of (is_valid, message)
    """
    if force:
        return True, "Validation skipped (--force)"

    # Define minimum criteria for each transition
    promotion_criteria = {
        ("research", "candidate"): {
            "min_sharpe": 1.0,
            "min_cagr": 0.10,
            "max_drawdown": -0.20,
            "min_trades": 10
        },
        ("candidate", "paper"): {
            "min_sharpe": 1.2,
            "min_cagr": 0.12,
            "max_drawdown": -0.15,
            "min_trades": 20
        },
        ("paper", "live"): {
            "paper_days": 30,
            "min_paper_trades": 10,
            "max_paper_slippage": 0.001  # 10 bps
        }
    }

    # Get criteria for this transition
    criteria = promotion_criteria.get((from_stage, to_stage))

    if not criteria:
        # No specific criteria defined, allow promotion
        return True, f"No validation criteria defined for {from_stage} → {to_stage}"

    # For research → candidate and candidate → paper: check backtest results
    if to_stage in ["candidate", "paper"]:
        # Look for most recent backtest results
        # In production, this would query the database
        # For now, we'll just return a warning that validation should be manual
        return True, f"WARNING: Manual validation required. Ensure model meets: {criteria}"

    # For paper → live: check paper trading results
    if to_stage == "live":
        # In production, this would check paper trading history
        return True, f"WARNING: Manual validation required. Ensure paper trading meets: {criteria}"

    return True, "Promotion criteria met"


def promote_model(args):
    """Promote model to next lifecycle stage."""
    model_name = args.model
    reason = args.reason or "Manual promotion"
    operator = args.operator or "cli_user"
    force = getattr(args, 'force', False)

    # Define lifecycle progression
    lifecycle_progression = {
        "research": "candidate",
        "candidate": "paper",
        "paper": "live"
    }

    # For now, we'll track lifecycle in a simple JSON file
    # In production, this would be in the database
    lifecycle_file = Path("configs/.model_lifecycle.json")
    lifecycle_file.parent.mkdir(exist_ok=True)

    # Load current lifecycle states
    if lifecycle_file.exists():
        with open(lifecycle_file) as f:
            lifecycle_states = json.load(f)
    else:
        lifecycle_states = {}

    # Get current stage (default to research)
    current_stage = lifecycle_states.get(model_name, "research")

    # Check if promotion is possible
    if current_stage == "live":
        print(f"✗ Cannot promote {model_name}: already at 'live' stage")
        sys.exit(1)

    # Get next stage
    next_stage = lifecycle_progression[current_stage]

    # Validate promotion criteria
    is_valid, validation_message = validate_promotion_criteria(
        model_name, current_stage, next_stage, force
    )

    if not is_valid:
        print(f"✗ Promotion validation failed: {validation_message}")
        sys.exit(1)

    if validation_message.startswith("WARNING"):
        print(f"\n⚠  {validation_message}\n")

    # Update lifecycle state
    lifecycle_states[model_name] = next_stage

    # Save updated states
    with open(lifecycle_file, 'w') as f:
        json.dump(lifecycle_states, f, indent=2)

    # Log the event
    event = log_lifecycle_event(
        model_name=model_name,
        from_stage=current_stage,
        to_stage=next_stage,
        reason=reason,
        operator=operator
    )

    print("=" * 70)
    print("MODEL LIFECYCLE PROMOTION")
    print("=" * 70)
    print(f"\nModel:       {model_name}")
    print(f"From Stage:  {current_stage}")
    print(f"To Stage:    {next_stage}")
    print(f"Reason:      {reason}")
    print(f"Operator:    {operator}")
    print(f"Timestamp:   {event['timestamp']}")

    if validation_message and not validation_message.startswith("WARNING"):
        print(f"Validation:  {validation_message}")

    print(f"\n✓ Model promoted successfully")
    print(f"\nLifecycle log: {get_lifecycle_log_path()}")
    print("=" * 70)


def demote_model(args):
    """Demote model to previous lifecycle stage."""
    model_name = args.model
    reason = args.reason or "Manual demotion"
    operator = args.operator or "cli_user"

    # Define lifecycle regression
    lifecycle_regression = {
        "live": "paper",
        "paper": "candidate",
        "candidate": "research"
    }

    lifecycle_file = Path("configs/.model_lifecycle.json")

    # Load current lifecycle states
    if lifecycle_file.exists():
        with open(lifecycle_file) as f:
            lifecycle_states = json.load(f)
    else:
        lifecycle_states = {}

    # Get current stage (default to research)
    current_stage = lifecycle_states.get(model_name, "research")

    # Check if demotion is possible
    if current_stage == "research":
        print(f"✗ Cannot demote {model_name}: already at 'research' stage")
        sys.exit(1)

    # Get previous stage
    previous_stage = lifecycle_regression[current_stage]

    # Update lifecycle state
    lifecycle_states[model_name] = previous_stage

    # Save updated states
    with open(lifecycle_file, 'w') as f:
        json.dump(lifecycle_states, f, indent=2)

    # Log the event
    event = log_lifecycle_event(
        model_name=model_name,
        from_stage=current_stage,
        to_stage=previous_stage,
        reason=reason,
        operator=operator
    )

    print("=" * 70)
    print("MODEL LIFECYCLE DEMOTION")
    print("=" * 70)
    print(f"\nModel:       {model_name}")
    print(f"From Stage:  {current_stage}")
    print(f"To Stage:    {previous_stage}")
    print(f"Reason:      {reason}")
    print(f"Operator:    {operator}")
    print(f"Timestamp:   {event['timestamp']}")
    print(f"\n✓ Model demoted successfully")
    print(f"\nLifecycle log: {get_lifecycle_log_path()}")
    print("=" * 70)


def list_models(args):
    """List all models with their lifecycle stages."""
    lifecycle_file = Path("configs/.model_lifecycle.json")

    # Load current lifecycle states
    if lifecycle_file.exists():
        with open(lifecycle_file) as f:
            lifecycle_states = json.load(f)
    else:
        lifecycle_states = {}

    if not lifecycle_states:
        print("No models registered yet")
        return

    print("=" * 70)
    print("MODEL LIFECYCLE STATUS")
    print("=" * 70)
    print(f"\n{'Model':<40} {'Stage':<15}")
    print("-" * 70)

    for model_name, stage in sorted(lifecycle_states.items()):
        print(f"{model_name:<40} {stage:<15}")

    print("\n" + "=" * 70)
    print(f"\nTotal models: {len(lifecycle_states)}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Backtest CLI for algorithmic trading platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick run using profile (easiest for iteration)
  python -m backtest.cli run --profile equity_trend_default

  # Run profile with different dates
  python -m backtest.cli run --profile equity_trend_default --start 2023-01-01

  # Traditional config-based run
  python -m backtest.cli run --config configs/base/system.yaml

  # View last backtest results
  python -m backtest.cli show-last

  # Promote model to next stage
  python -m backtest.cli promote --model EquityTrendModel_v1 --reason "Passed backtest criteria"

  # Demote model to previous stage
  python -m backtest.cli demote --model EquityTrendModel_v1 --reason "Failed paper trading"

  # List all models
  python -m backtest.cli list-models

Workflow Tips:
  1. Edit a profile in configs/profiles.yaml
  2. Run: python -m backtest.cli run --profile <name>
  3. Review results immediately or later with: python -m backtest.cli show-last
  4. Iterate: edit profile parameters and re-run
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run a backtest')
    run_parser.add_argument(
        '--profile',
        help='Profile name from configs/profiles.yaml (e.g., equity_trend_default)'
    )
    run_parser.add_argument(
        '--config',
        help='Path to config file (e.g., configs/base/system.yaml). Required if --profile not used.'
    )
    run_parser.add_argument(
        '--model',
        default='EquityTrendModel_v1',
        help='Model to backtest (default: EquityTrendModel_v1). Ignored if --profile is used.'
    )
    run_parser.add_argument(
        '--start',
        help='Start date (YYYY-MM-DD), overrides config/profile. Defaults to 5 years ago.'
    )
    run_parser.add_argument(
        '--end',
        help='End date (YYYY-MM-DD), overrides config/profile. Defaults to today.'
    )
    run_parser.add_argument(
        '--no-download',
        action='store_true',
        help='Skip automatic data download check'
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

    # Promote command
    promote_parser = subparsers.add_parser('promote', help='Promote model to next lifecycle stage')
    promote_parser.add_argument(
        '--model',
        required=True,
        help='Model name to promote'
    )
    promote_parser.add_argument(
        '--reason',
        help='Reason for promotion'
    )
    promote_parser.add_argument(
        '--operator',
        help='Operator performing the promotion (default: cli_user)'
    )

    # Demote command
    demote_parser = subparsers.add_parser('demote', help='Demote model to previous lifecycle stage')
    demote_parser.add_argument(
        '--model',
        required=True,
        help='Model name to demote'
    )
    demote_parser.add_argument(
        '--reason',
        help='Reason for demotion'
    )
    demote_parser.add_argument(
        '--operator',
        help='Operator performing the demotion (default: cli_user)'
    )

    # List models command
    list_parser = subparsers.add_parser('list-models', help='List all models with lifecycle stages')

    # Show last run command
    show_last_parser = subparsers.add_parser('show-last', help='View results from last backtest run')

    args = parser.parse_args()

    if args.command == 'run':
        run_backtest(args)
    elif args.command == 'promote':
        promote_model(args)
    elif args.command == 'demote':
        demote_model(args)
    elif args.command == 'list-models':
        list_models(args)
    elif args.command == 'show-last':
        show_last_run()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
