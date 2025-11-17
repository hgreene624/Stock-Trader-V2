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
import pandas as pd
import numpy as np
sys.path.append('..')
from backtest.runner import BacktestRunner
from models.equity_trend_v1 import EquityTrendModel_v1
from models.equity_trend_v1_daily import EquityTrendModel_v1_Daily
from models.equity_trend_v2_daily import EquityTrendModel_v2_Daily
from models.sector_rotation_v1 import SectorRotationModel_v1
from utils.logging import StructuredLogger
from utils.config import ConfigLoader


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def colorize(value, threshold_good, threshold_bad, reverse=False, percentage=False):
    """
    Colorize a metric value based on thresholds.

    Args:
        value: The value to colorize
        threshold_good: Threshold for green (good)
        threshold_bad: Threshold for red (bad)
        reverse: If True, lower is better (like drawdown)
        percentage: If True, format as percentage

    Returns:
        Colored string
    """
    if percentage:
        formatted = f"{value:>10.2%}"
    else:
        formatted = f"{value:>10.2f}"

    if reverse:
        # Lower is better (e.g., drawdown)
        if value <= threshold_good:
            color = Colors.GREEN
        elif value <= threshold_bad:
            color = Colors.YELLOW
        else:
            color = Colors.RED
    else:
        # Higher is better (e.g., returns, Sharpe)
        if value >= threshold_good:
            color = Colors.GREEN
        elif value >= threshold_bad:
            color = Colors.YELLOW
        else:
            color = Colors.RED

    return f"{color}{formatted}{Colors.RESET}"


def calculate_spy_benchmark(start_date: str, end_date: str) -> dict:
    """
    Calculate SPY benchmark returns for comparison.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Dictionary with SPY metrics
    """
    try:
        # Try to load SPY data from our data directory
        spy_file = Path("data/equities/SPY_1D.parquet")

        if not spy_file.exists():
            return None

        spy_data = pd.read_parquet(spy_file)
        spy_data['timestamp'] = pd.to_datetime(spy_data['timestamp'], utc=True)
        spy_data = spy_data.set_index('timestamp')

        # Filter to backtest period
        start_ts = pd.Timestamp(start_date, tz='UTC')
        end_ts = pd.Timestamp(end_date, tz='UTC')

        spy_period = spy_data[(spy_data.index >= start_ts) & (spy_data.index <= end_ts)]

        if len(spy_period) < 2:
            return None

        # Calculate SPY metrics
        initial_price = spy_period['close'].iloc[0]
        final_price = spy_period['close'].iloc[-1]

        total_return = (final_price - initial_price) / initial_price

        # Calculate CAGR
        days = (spy_period.index[-1] - spy_period.index[0]).days
        years = days / 365.25
        cagr = (final_price / initial_price) ** (1 / years) - 1 if years > 0 else 0

        # Calculate max drawdown
        cumulative = (1 + spy_period['close'].pct_change()).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()

        # Calculate Sharpe (simplified - using daily returns)
        daily_returns = spy_period['close'].pct_change().dropna()
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0

        return {
            'total_return': total_return,
            'cagr': cagr,
            'max_drawdown': abs(max_dd),
            'sharpe': sharpe,
            'initial_price': initial_price,
            'final_price': final_price
        }

    except Exception as e:
        print(f"Warning: Could not calculate SPY benchmark: {e}")
        return None


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

    # Get actual backtest period from NAV series
    nav_series = results.get('nav_series')
    if nav_series is not None and len(nav_series) > 0:
        actual_start = nav_series.index[0].strftime('%Y-%m-%d')
        actual_end = nav_series.index[-1].strftime('%Y-%m-%d')
    else:
        actual_start = results.get('start_date', 'N/A')
        actual_end = results.get('end_date', 'N/A')

    last_run = {
        "timestamp": datetime.now().isoformat(),
        "model": model_names,
        "start_date": results.get('start_date', 'N/A'),  # Requested period
        "end_date": results.get('end_date', 'N/A'),
        "actual_start_date": actual_start,  # Actual period (may be shorter due to data availability)
        "actual_end_date": actual_end,
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

    # Show both requested and actual periods if different
    requested_start = last_run.get('start_date', 'N/A')
    requested_end = last_run.get('end_date', 'N/A')
    actual_start = last_run.get('actual_start_date', requested_start)
    actual_end = last_run.get('actual_end_date', requested_end)

    if actual_start != requested_start or actual_end != requested_end:
        print(f"Period:      {requested_start} to {requested_end} (requested)")
        print(f"             {actual_start} to {actual_end} (actual - limited by data)")
    else:
        print(f"Period:      {actual_start} to {actual_end}")

    # Config info
    config_info = last_run.get('config', {})
    if config_info:
        print(f"\nConfiguration:")
        if 'profile' in config_info:
            print(f"  Profile:   {config_info['profile']}")
        if 'config_file' in config_info:
            print(f"  Config:    {config_info['config_file']}")

    # Calculate SPY benchmark using ACTUAL backtest period
    spy_bench = calculate_spy_benchmark(actual_start, actual_end)

    # Performance metrics
    print("\n" + "-" * 80)
    print("PERFORMANCE SUMMARY")
    print("-" * 80)

    # Market Comparison (prominently displayed first)
    if spy_bench:
        print(f"\n{Colors.BOLD}📊 VS MARKET (SPY):{Colors.RESET}")
        alpha = metrics.get('cagr', 0) - spy_bench['cagr']
        outperformance = metrics.get('total_return', 0) - spy_bench['total_return']

        # Color-code alpha
        if alpha >= 0.05:  # Beat by 5%+
            alpha_color = Colors.GREEN
        elif alpha >= 0:  # Beat market
            alpha_color = Colors.YELLOW
        else:  # Underperformed
            alpha_color = Colors.RED

        print(f"  Alpha (CAGR):        {alpha_color}{alpha:>9.2%}{Colors.RESET}  (Strategy: {metrics.get('cagr', 0):.2%} vs SPY: {spy_bench['cagr']:.2%})")
        print(f"  Outperformance:      {alpha_color}{outperformance:>9.2%}{Colors.RESET}  (Strategy: {metrics.get('total_return', 0):.2%} vs SPY: {spy_bench['total_return']:.2%})")

        # Risk-adjusted comparison
        sharpe_diff = metrics.get('sharpe_ratio', 0) - spy_bench['sharpe']
        if sharpe_diff >= 0.5:
            sharpe_color = Colors.GREEN
        elif sharpe_diff >= 0:
            sharpe_color = Colors.YELLOW
        else:
            sharpe_color = Colors.RED
        print(f"  Sharpe Advantage:    {sharpe_color}{sharpe_diff:>9.2f}{Colors.RESET}  (Strategy: {metrics.get('sharpe_ratio', 0):.2f} vs SPY: {spy_bench['sharpe']:.2f})")
        print()

    print(f"\nReturns:")
    # Color-code returns
    if spy_bench:
        total_ret_color = colorize(metrics.get('total_return', 0), spy_bench['total_return'], spy_bench['total_return'] * 0.8, percentage=True)
        cagr_color = colorize(metrics.get('cagr', 0), spy_bench['cagr'], spy_bench['cagr'] * 0.8, percentage=True)
    else:
        total_ret_color = colorize(metrics.get('total_return', 0), 0.15, 0.05, percentage=True)
        cagr_color = colorize(metrics.get('cagr', 0), 0.12, 0.06, percentage=True)

    print(f"  Total Return:     {total_ret_color}")
    print(f"  CAGR:             {cagr_color}")

    print(f"\nRisk Metrics:")
    dd_color = colorize(metrics.get('max_drawdown', 0), 0.15, 0.25, reverse=True, percentage=True)
    sharpe_color = colorize(metrics.get('sharpe_ratio', 0), 1.5, 0.5, percentage=False)

    print(f"  Max Drawdown:     {dd_color}")
    print(f"  Sharpe Ratio:     {sharpe_color}")

    print(f"\nTrading Metrics:")
    print(f"  Total Trades:     {last_run.get('trade_count', 0):>10}")
    wr_color = colorize(metrics.get('win_rate', 0), 0.55, 0.45, percentage=True)
    print(f"  Win Rate:         {wr_color}")

    print(f"\nBalanced Performance Score:")
    bps_color = colorize(metrics.get('bps', 0), 1.0, 0.5, percentage=False)
    print(f"  BPS:              {bps_color}")

    print(f"\nNAV:")
    print(f"  Initial NAV:      ${metrics.get('initial_nav', 0):>10,.2f}")
    print(f"  Final NAV:        ${metrics.get('final_nav', 0):>10,.2f}")

    print("\n" + "=" * 80)
    print(f"\nFull results saved in: results/")
    print("=" * 80 + "\n")


def create_profile(args):
    """Create a new test profile in configs/profiles.yaml"""
    profiles_file = Path("configs/profiles.yaml")

    # Load existing profiles
    with open(profiles_file) as f:
        profiles_data = yaml.safe_load(f) or {}

    if 'profiles' not in profiles_data:
        profiles_data['profiles'] = {}

    # Check if profile already exists
    if args.name in profiles_data['profiles']:
        print(f"❌ Profile '{args.name}' already exists!")
        print("   Choose a different name or edit the existing profile manually.")
        sys.exit(1)

    # Parse parameters
    params = {}
    if args.params:
        for param_str in args.params.split(','):
            if '=' in param_str:
                key, value = param_str.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Try to convert to appropriate type
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    # Keep as string
                    pass
                params[key] = value

    # Create new profile
    new_profile = {
        'description': args.description or f"Custom profile for {args.model}",
        'model': args.model,
        'universe': args.universe.split(',') if args.universe else [],
        'start_date': args.start_date or "2020-01-01",
        'end_date': args.end_date or "2024-12-31"
    }

    if args.lookback_bars:
        new_profile['lookback_bars'] = args.lookback_bars

    if params:
        new_profile['parameters'] = params

    # Add to profiles
    profiles_data['profiles'][args.name] = new_profile

    # Save back to file
    with open(profiles_file, 'w') as f:
        yaml.safe_dump(profiles_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Created profile '{args.name}' in {profiles_file}")
    print(f"\nProfile details:")
    print(f"  Model: {new_profile['model']}")
    print(f"  Universe: {', '.join(new_profile['universe'])}")
    print(f"  Period: {new_profile['start_date']} to {new_profile['end_date']}")
    if params:
        print(f"  Parameters:")
        for k, v in params.items():
            print(f"    {k}: {v}")

    print(f"\n🚀 Run it with:")
    print(f"   python3 -m backtest.cli run --profile {args.name}")


def list_profiles():
    """List all available profiles in configs/profiles.yaml"""
    profiles_file = Path("configs/profiles.yaml")

    if not profiles_file.exists():
        print("❌ No profiles file found at configs/profiles.yaml")
        return

    with open(profiles_file) as f:
        profiles_data = yaml.safe_load(f) or {}

    profiles = profiles_data.get('profiles', {})

    if not profiles:
        print("No profiles found in configs/profiles.yaml")
        return

    print("\n" + "=" * 80)
    print("AVAILABLE PROFILES")
    print("=" * 80 + "\n")

    for profile_name, profile_config in profiles.items():
        desc = profile_config.get('description', 'No description')
        model = profile_config.get('model', 'Unknown')
        universe = profile_config.get('universe', [])

        print(f"📋 {profile_name}")
        print(f"   Model: {model}")
        print(f"   Description: {desc}")
        print(f"   Universe: {', '.join(universe[:5])}{'...' if len(universe) > 5 else ''}")
        print()

    print(f"Total: {len(profiles)} profiles")
    print("\n💡 Run with: python3 -m backtest.cli run --profile <name>")
    print("=" * 80 + "\n")


def create_model(args):
    """Create a new model from a template."""
    # Template mapping
    templates = {
        'sector_rotation': 'sector_rotation_template.py',
        'trend_following': 'trend_following_template.py',
        'mean_reversion': 'mean_reversion_template.py'
    }

    if args.template not in templates:
        print(f"❌ Unknown template: {args.template}")
        print(f"Available templates: {', '.join(templates.keys())}")
        sys.exit(1)

    # Default parameters by template
    defaults = {
        'sector_rotation': {
            'MOMENTUM_PERIOD': 126,
            'TOP_N': 3,
            'MIN_MOMENTUM': 0.0,
            'DESCRIPTION': 'Momentum-based sector rotation strategy'
        },
        'trend_following': {
            'MA_PERIOD': 200,
            'MOMENTUM_PERIOD': 120,
            'MOMENTUM_THRESHOLD': 0.0,
            'DESCRIPTION': 'Trend-following strategy with MA and momentum'
        },
        'mean_reversion': {
            'RSI_PERIOD': 14,
            'RSI_OVERSOLD': 30,
            'RSI_OVERBOUGHT': 70,
            'BB_PERIOD': 20,
            'BB_STD': 2.0,
            'DESCRIPTION': 'Mean reversion using RSI and Bollinger Bands'
        }
    }

    # Load template
    template_path = Path(f"templates/models/{templates[args.template]}")
    if not template_path.exists():
        print(f"❌ Template file not found: {template_path}")
        sys.exit(1)

    with open(template_path) as f:
        template_code = f.read()

    # Parse custom parameters
    params = defaults[args.template].copy()
    if args.params:
        for param_str in args.params.split(','):
            if '=' in param_str:
                key, value = param_str.split('=', 1)
                key = key.strip().upper()
                value = value.strip()
                # Try to convert to appropriate type
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    # Keep as string
                    pass
                params[key] = value

    # Replace placeholders
    model_class_name = args.name
    model_id = args.name
    if args.description:
        params['DESCRIPTION'] = args.description

    replacements = {
        '{MODEL_NAME}': model_class_name,
        '{MODEL_ID}': model_id,
        **{f'{{{key}}}': str(value) for key, value in params.items()}
    }

    for placeholder, value in replacements.items():
        template_code = template_code.replace(placeholder, value)

    # Save new model
    output_path = Path(f"models/{args.name.lower()}.py")
    if output_path.exists() and not args.force:
        print(f"❌ Model file already exists: {output_path}")
        print("   Use --force to overwrite")
        sys.exit(1)

    with open(output_path, 'w') as f:
        f.write(template_code)

    print(f"\n✅ Created model '{model_class_name}' at {output_path}")
    print(f"\nModel details:")
    print(f"  Class: {model_class_name}")
    print(f"  Template: {args.template}")
    print(f"  Parameters:")
    for key, value in params.items():
        print(f"    {key}: {value}")

    print(f"\n📝 Next steps:")
    print(f"1. Register model in backtest/cli.py:")
    print(f"   Add import: from models.{args.name.lower()} import {model_class_name}")
    print(f"   Add to model initialization:")
    print(f"   elif model_name == \"{model_class_name}\":")
    print(f"       model = {model_class_name}()")
    print(f"\n2. Create a profile in configs/profiles.yaml to test it")
    print(f"\n3. Run: python3 -m backtest.cli run --profile <your_profile>")


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
        lookback_bars = profile.get('lookback_bars')

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
        lookback_bars = None  # Not supported in config-based mode (yet)

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

    # Initialize model with parameters from profile (if available)
    model_params = parameters if 'parameters' in locals() else {}

    if model_name == "EquityTrendModel_v1":
        model = EquityTrendModel_v1(**model_params)
    elif model_name == "EquityTrendModel_v1_Daily":
        model = EquityTrendModel_v1_Daily(**model_params)
    elif model_name == "EquityTrendModel_v2_Daily":
        model = EquityTrendModel_v2_Daily(**model_params)
    elif model_name == "SectorRotationModel_v1":
        model = SectorRotationModel_v1(**model_params)
    else:
        raise ValueError(
            f"Unknown model: {model_name}. "
            f"Available models: EquityTrendModel_v1, EquityTrendModel_v1_Daily, "
            f"EquityTrendModel_v2_Daily, SectorRotationModel_v1"
        )

    # Create runner
    runner = BacktestRunner(config_path, logger=logger)

    # Run backtest
    try:
        print(f"\n🚀 Starting backtest...")

        # Build backtest config overrides
        backtest_config_overrides = {}
        if lookback_bars is not None:
            backtest_config_overrides['lookback_bars'] = lookback_bars

        results = runner.run(
            model=model,
            start_date=start_date,
            end_date=end_date,
            backtest_config_overrides=backtest_config_overrides if backtest_config_overrides else None
        )

        # Handle JSON output format
        if hasattr(args, 'format') and args.format == 'json':
            # Get actual backtest period
            nav_series = results.get('nav_series')
            if nav_series is not None and len(nav_series) > 0:
                actual_start = nav_series.index[0].strftime('%Y-%m-%d')
                actual_end = nav_series.index[-1].strftime('%Y-%m-%d')
            else:
                actual_start = results['start_date']
                actual_end = results['end_date']

            # Calculate SPY benchmark
            spy_bench = calculate_spy_benchmark(actual_start, actual_end)

            # Build JSON output
            json_output = {
                "status": "success",
                "model": results.get('model_ids', results.get('model_id', 'Unknown')),
                "period": {
                    "requested_start": results['start_date'],
                    "requested_end": results['end_date'],
                    "actual_start": actual_start,
                    "actual_end": actual_end
                },
                "metrics": results['metrics'],
                "vs_spy": {
                    "spy_cagr": spy_bench['cagr'] if spy_bench else None,
                    "spy_total_return": spy_bench['total_return'] if spy_bench else None,
                    "spy_sharpe": spy_bench['sharpe'] if spy_bench else None,
                    "alpha": results['metrics']['cagr'] - spy_bench['cagr'] if spy_bench else None,
                    "outperformance": results['metrics']['total_return'] - spy_bench['total_return'] if spy_bench else None,
                    "sharpe_advantage": results['metrics']['sharpe_ratio'] - spy_bench['sharpe'] if spy_bench else None,
                    "beats_spy": results['metrics']['cagr'] > spy_bench['cagr'] if spy_bench else None
                },
                "trade_count": len(results.get('trade_log', [])),
                "config": config_info
            }

            print(json.dumps(json_output, indent=2))
            return

        # Text output (default)
        # Print results
        print("\n" + "=" * 70)
        print("BACKTEST RESULTS")
        print("=" * 70)

        # Handle both single and multi-model results
        model_names = results.get('model_ids', results.get('model_id', 'Unknown'))
        if isinstance(model_names, list):
            model_names = ', '.join(model_names)

        print(f"\nModel(s): {model_names}")

        # Get actual backtest period from NAV series (may differ from requested due to data availability)
        nav_series = results.get('nav_series')
        if nav_series is not None and len(nav_series) > 0:
            actual_start = nav_series.index[0].strftime('%Y-%m-%d')
            actual_end = nav_series.index[-1].strftime('%Y-%m-%d')
        else:
            actual_start = results['start_date']
            actual_end = results['end_date']

        # Show both requested and actual periods if different
        requested_start = results['start_date']
        requested_end = results['end_date']

        if actual_start != requested_start or actual_end != requested_end:
            print(f"Period: {requested_start} to {requested_end} (requested)")
            print(f"        {actual_start} to {actual_end} (actual - limited by data)")
        else:
            print(f"Period: {actual_start} to {actual_end}")

        # Calculate SPY benchmark using ACTUAL period (not requested)
        spy_bench = calculate_spy_benchmark(actual_start, actual_end)

        # Performance metrics
        print("\n" + "-" * 70)
        print("PERFORMANCE METRICS")
        print("-" * 70)

        metrics = results['metrics']

        # Market Comparison (prominently displayed first)
        if spy_bench:
            print(f"\n{Colors.BOLD}📊 VS MARKET (SPY):{Colors.RESET}")
            alpha = metrics['cagr'] - spy_bench['cagr']
            outperformance = metrics['total_return'] - spy_bench['total_return']

            # Color-code alpha
            if alpha >= 0.05:  # Beat by 5%+
                alpha_color = Colors.GREEN
            elif alpha >= 0:  # Beat market
                alpha_color = Colors.YELLOW
            else:  # Underperformed
                alpha_color = Colors.RED

            print(f"  Alpha (CAGR):        {alpha_color}{alpha:>9.2%}{Colors.RESET}  (Strategy: {metrics['cagr']:.2%} vs SPY: {spy_bench['cagr']:.2%})")
            print(f"  Outperformance:      {alpha_color}{outperformance:>9.2%}{Colors.RESET}  (Strategy: {metrics['total_return']:.2%} vs SPY: {spy_bench['total_return']:.2%})")

            # Risk-adjusted comparison
            sharpe_diff = metrics['sharpe_ratio'] - spy_bench['sharpe']
            if sharpe_diff >= 0.5:
                sharpe_color = Colors.GREEN
            elif sharpe_diff >= 0:
                sharpe_color = Colors.YELLOW
            else:
                sharpe_color = Colors.RED
            print(f"  Sharpe Advantage:    {sharpe_color}{sharpe_diff:>9.2f}{Colors.RESET}  (Strategy: {metrics['sharpe_ratio']:.2f} vs SPY: {spy_bench['sharpe']:.2f})")
            print()

        print(f"\nReturns:")
        # Color-code returns based on SPY comparison if available
        if spy_bench:
            total_ret_color = colorize(metrics['total_return'], spy_bench['total_return'], spy_bench['total_return'] * 0.8, percentage=True)
            cagr_color = colorize(metrics['cagr'], spy_bench['cagr'], spy_bench['cagr'] * 0.8, percentage=True)
        else:
            # Fallback to absolute thresholds
            total_ret_color = colorize(metrics['total_return'], 0.15, 0.05, percentage=True)
            cagr_color = colorize(metrics['cagr'], 0.12, 0.06, percentage=True)

        print(f"  Total Return:     {total_ret_color}")
        print(f"  CAGR:             {cagr_color}")

        print(f"\nRisk Metrics:")
        # Max Drawdown: green < 15%, yellow 15-25%, red > 25%
        dd_color = colorize(metrics['max_drawdown'], 0.15, 0.25, reverse=True, percentage=True)
        # Sharpe: green > 1.5, yellow 0.5-1.5, red < 0.5
        sharpe_color = colorize(metrics['sharpe_ratio'], 1.5, 0.5, percentage=False)

        print(f"  Max Drawdown:     {dd_color}")
        print(f"  Sharpe Ratio:     {sharpe_color}")

        print(f"\nTrading Metrics:")
        print(f"  Total Trades:     {metrics['total_trades']:>10}")

        # Win Rate: green > 55%, yellow 45-55%, red < 45%
        wr_color = colorize(metrics['win_rate'], 0.55, 0.45, percentage=True)
        print(f"  Win Rate:         {wr_color}")

        print(f"\nBalanced Performance Score (BPS):")
        # BPS: green > 1.0, yellow 0.5-1.0, red < 0.5
        bps_color = colorize(metrics['bps'], 1.0, 0.5, percentage=False)
        print(f"  BPS:              {bps_color}")

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

        # Always save results to results/ directory for audit purposes
        output_dir = Path(args.output) if args.output else Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save NAV series
        nav_path = output_dir / "nav_series.csv"
        nav_series.to_csv(nav_path)

        # Save trade log
        if len(trade_log) > 0:
            trade_path = output_dir / "trade_log.csv"
            trade_log.to_csv(trade_path, index=False)

        # Save metrics
        metrics_path = output_dir / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)

        if args.output:
            print(f"\nSaved results to {output_dir}/")

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
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format: text (human-readable) or json (machine-readable)'
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

    # Create profile command
    create_profile_parser = subparsers.add_parser('create-profile', help='Create a new test profile')
    create_profile_parser.add_argument('--name', required=True, help='Profile name')
    create_profile_parser.add_argument('--model', required=True, help='Model name (e.g., SectorRotationModel_v1)')
    create_profile_parser.add_argument('--universe', required=True, help='Comma-separated ticker list (e.g., XLK,XLF,XLE)')
    create_profile_parser.add_argument('--params', help='Comma-separated parameters (e.g., momentum_period=90,top_n=4)')
    create_profile_parser.add_argument('--description', help='Profile description')
    create_profile_parser.add_argument('--start-date', help='Start date (default: 2020-01-01)')
    create_profile_parser.add_argument('--end-date', help='End date (default: 2024-12-31)')
    create_profile_parser.add_argument('--lookback-bars', type=int, help='Lookback bars for historical data')

    # List profiles command
    list_profiles_parser = subparsers.add_parser('list-profiles', help='List all available profiles')

    # Create model command
    create_model_parser = subparsers.add_parser('create-model', help='Create a new model from template')
    create_model_parser.add_argument('--template', required=True,
                                     choices=['sector_rotation', 'trend_following', 'mean_reversion'],
                                     help='Template to use')
    create_model_parser.add_argument('--name', required=True, help='Model class name (e.g., MySectorRotation)')
    create_model_parser.add_argument('--params', help='Comma-separated parameters (e.g., momentum_period=90,top_n=4)')
    create_model_parser.add_argument('--description', help='Model description')
    create_model_parser.add_argument('--force', action='store_true', help='Overwrite existing model file')

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
    elif args.command == 'create-profile':
        create_profile(args)
    elif args.command == 'list-profiles':
        list_profiles()
    elif args.command == 'create-model':
        create_model(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
