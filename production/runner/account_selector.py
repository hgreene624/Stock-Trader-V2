"""
Multi-Account Selector

Allows users to select which Alpaca account to use at runtime by:
1. Loading all configured accounts from accounts.yaml
2. Querying each account's balance and status
3. Presenting an interactive selection menu
4. Returning the selected account credentials

Usage:
    from production.runner.account_selector import select_account

    api_key, secret_key, account_info = select_account()
    # Or skip selection:
    api_key, secret_key, account_info = select_account(account_name="paper_main")
"""

import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import yaml
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

# Load environment variables from .env file
load_dotenv()


def load_accounts_config(config_path: Optional[Path] = None) -> Dict:
    """
    Load accounts configuration from YAML file.

    Args:
        config_path: Path to accounts.yaml. If None, uses default location.

    Returns:
        Dictionary of account configurations
    """
    if config_path is None:
        # Try multiple locations
        possible_paths = [
            Path(__file__).parent.parent / 'configs' / 'accounts.yaml',
            Path('configs/accounts.yaml'),
            Path('/app/configs/accounts.yaml'),  # Docker
        ]

        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            raise FileNotFoundError("Could not find accounts.yaml in any expected location")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Expand environment variables in API keys
    accounts = {}
    for name, account in config.get('accounts', {}).items():
        api_key = account['api_key']
        secret_key = account['secret_key']

        # Replace ${VAR_NAME} with environment variable
        if api_key.startswith('${') and api_key.endswith('}'):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var)
            if not api_key:
                print(f"Warning: Environment variable {env_var} not set for account '{name}', skipping")
                continue

        if secret_key.startswith('${') and secret_key.endswith('}'):
            env_var = secret_key[2:-1]
            secret_key = os.getenv(env_var)

            # Fallback: Try alternative names
            if not secret_key:
                if env_var == 'ALPACA_SECRET_KEY':
                    secret_key = os.getenv('ALPACA_API_SECRET')
                elif env_var == 'ALPACA_API_SECRET':
                    secret_key = os.getenv('ALPACA_SECRET_KEY')

            if not secret_key:
                print(f"Warning: Environment variable {env_var} not set for account '{name}', skipping")
                continue

        accounts[name] = {
            'api_key': api_key,
            'secret_key': secret_key,
            'paper': account.get('paper', True),
            'health_port': account.get('health_port', 8080),
            'models': account.get('models', []),
            'param_profile': account.get('param_profile', 'default')
        }

    return accounts


def get_account_info(api_key: str, secret_key: str, paper: bool = True) -> Optional[Dict]:
    """
    Fetch account information from Alpaca.

    Args:
        api_key: Alpaca API key
        secret_key: Alpaca secret key
        paper: Whether this is a paper trading account

    Returns:
        Dictionary with account info, or None if connection failed
    """
    try:
        client = TradingClient(api_key, secret_key, paper=paper)
        account = client.get_account()

        return {
            'account_number': account.account_number,
            'status': account.status.value,
            'cash': float(account.cash),
            'portfolio_value': float(account.portfolio_value),
            'buying_power': float(account.buying_power),
            'pattern_day_trader': account.pattern_day_trader,
            'trading_blocked': account.trading_blocked,
            'account_blocked': account.account_blocked,
        }
    except Exception as e:
        return {
            'error': str(e),
            'status': 'ERROR'
        }


def format_currency(amount: float) -> str:
    """Format a number as currency."""
    return f"${amount:,.2f}"


def format_models(models: list) -> str:
    """Format model list for display."""
    if not models:
        return "None"
    if len(models) == 1:
        return models[0].replace('SectorRotation', 'SR')
    elif len(models) <= 3:
        # Abbreviate model names
        abbrev = []
        for m in models:
            m = m.replace('SectorRotation', 'SR').replace('_v1', '').replace('_v3', '')
            abbrev.append(m)
        return ', '.join(abbrev)
    else:
        return f"{len(models)} models"


def get_version() -> str:
    """Get the deployed version from environment or VERSION file."""
    # Check environment variable first (set by Docker)
    version = os.getenv('BOT_VERSION')
    if version:
        return version

    # Try reading VERSION file
    version_paths = [
        Path('/app/VERSION'),  # Docker
        Path(__file__).parent.parent.parent / 'production' / 'deploy' / 'VERSION',
        Path('production/deploy/VERSION'),
    ]

    for path in version_paths:
        if path.exists():
            try:
                return path.read_text().strip()
            except:
                pass

    return "unknown"


def display_accounts_from_config(accounts: Dict[str, Dict]) -> None:
    """
    Display accounts from config in standardized table format.
    Used by dashboard.py for account selection.

    Args:
        accounts: Dict mapping account name/id to config dict
    """
    import requests

    version = get_version()
    print("\n" + "=" * 100)
    print(f"Available Alpaca Accounts                                                    [v{version}]")
    print("=" * 100)
    print(f"{'#':<3} {'Port':<6} {'Account':<14} {'Type':<6} {'Status':<10} {'Profile':<15} {'Models':<25}")
    print("-" * 100)

    for i, (acc_id, acc_config) in enumerate(accounts.items(), 1):
        models = acc_config.get('models', [])
        # Shorten model names for display
        short_models = []
        for model in models[:3]:
            short_name = model.replace('SectorRotation', 'SR').replace('_v1', '').replace('_v3', '')
            short_models.append(short_name)
        models_str = ', '.join(short_models) if short_models else 'None'
        if len(models) > 3:
            models_str += f' +{len(models)-3}'

        paper = "PAPER" if acc_config.get('paper', True) else "LIVE"
        health_port = acc_config.get('health_port', 8080)
        profile = acc_config.get('param_profile', 'default')

        # Check if bot is running on this account
        is_running = False
        try:
            resp = requests.get(f'http://localhost:{health_port}/health', timeout=1)
            if resp.status_code == 200:
                is_running = True
        except Exception:
            pass

        status = "running" if is_running else "stopped"
        print(f"{i:<3} {health_port:<6} {acc_id:<14} {paper:<6} {status:<10} {profile:<15} {models_str:<25}")

    print("=" * 100)


def display_accounts(accounts_info: Dict[str, Dict], accounts_config: Dict[str, Dict]) -> None:
    """
    Display accounts in a formatted table.

    Args:
        accounts_info: Dict mapping account name to account info
        accounts_config: Dict mapping account name to config (with 'paper' field)
    """
    version = get_version()
    print("\n" + "=" * 120)
    print(f"Available Alpaca Accounts                                                              [v{version}]")
    print("=" * 120)
    print(f"{'#':<3} {'Port':<6} {'Account':<14} {'Type':<6} {'Balance':<12} {'Profile':<15} {'Models':<30}")
    print("-" * 120)

    for idx, (name, info) in enumerate(accounts_info.items(), 1):
        config = accounts_config.get(name, {})
        port = str(config.get('health_port', 'N/A'))
        profile = config.get('param_profile', 'default')
        models = format_models(config.get('models', []))

        if 'error' in info:
            print(f"{idx:<3} {port:<6} {name:<14} {'ERR':<6} {'N/A':<12} {profile:<15} {models:<30}")
            print(f"    Error: {info['error']}")
        else:
            # Use config to determine if paper or live
            is_paper = config.get('paper', True)
            account_type = "PAPER" if is_paper else "LIVE"
            balance = format_currency(info['portfolio_value'])

            print(f"{idx:<3} {port:<6} {name:<14} {account_type:<6} {balance:<12} {profile:<15} {models:<30}")

    print("=" * 120)


def select_account(account_name: Optional[str] = None, skip_selection: bool = False) -> Tuple[str, str, Dict]:
    """
    Interactive account selector.

    Args:
        account_name: If provided, use this account without prompting
        skip_selection: If True and only one account exists, use it automatically

    Returns:
        Tuple of (api_key, secret_key, account_info)

    Raises:
        ValueError: If account selection fails
    """
    # Load all configured accounts
    try:
        accounts_config = load_accounts_config()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nFalling back to .env credentials...")
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY') or os.getenv('ALPACA_API_SECRET')
        if not api_key or not secret_key:
            raise ValueError("No accounts.yaml found and ALPACA_API_KEY/ALPACA_SECRET_KEY not in .env")

        # Get account info for fallback
        info = get_account_info(api_key, secret_key, paper=True)
        if not info or 'error' in info:
            raise ValueError(f"Failed to connect to Alpaca with .env credentials: {info.get('error', 'Unknown error')}")

        return api_key, secret_key, info

    if not accounts_config:
        raise ValueError("No accounts configured in accounts.yaml")

    # If account_name specified, use it directly
    if account_name:
        if account_name not in accounts_config:
            raise ValueError(f"Account '{account_name}' not found in accounts.yaml")

        config = accounts_config[account_name]
        info = get_account_info(config['api_key'], config['secret_key'], config['paper'])

        if 'error' in info:
            raise ValueError(f"Failed to connect to account '{account_name}': {info['error']}")

        print(f"Using account: {account_name} ({info['account_number']})")
        return config['api_key'], config['secret_key'], info

    # Fetch info for all accounts
    print("Checking available accounts...")
    accounts_info = {}
    for name, config in accounts_config.items():
        print(f"   Checking {name}...", end=' ')
        info = get_account_info(config['api_key'], config['secret_key'], config['paper'])
        accounts_info[name] = info

        if 'error' in info:
            print(f"Error: {info['error']}")
        else:
            print(f"{info['account_number']} - {format_currency(info['portfolio_value'])}")

    # Filter out accounts with errors
    valid_accounts = {name: info for name, info in accounts_info.items() if 'error' not in info}

    if not valid_accounts:
        raise ValueError("No valid accounts found. All accounts failed to connect.")

    # If only one valid account and skip_selection=True, use it
    if len(valid_accounts) == 1 and skip_selection:
        name = list(valid_accounts.keys())[0]
        config = accounts_config[name]
        info = valid_accounts[name]
        print(f"\nUsing only available account: {name} ({info['account_number']})")
        return config['api_key'], config['secret_key'], info

    # Display accounts
    display_accounts(accounts_info, accounts_config)

    # Prompt for selection
    print("\nSelect an account by number (or 'q' to quit):")

    account_list = list(accounts_config.keys())

    while True:
        try:
            selection = input("Account #: ").strip()

            if selection.lower() == 'q':
                print("Account selection cancelled")
                sys.exit(0)

            idx = int(selection) - 1
            if 0 <= idx < len(account_list):
                selected_name = account_list[idx]
                selected_info = accounts_info[selected_name]

                # Check if account has error
                if 'error' in selected_info:
                    print(f"Cannot use account '{selected_name}': {selected_info['error']}")
                    print("Please select a different account.")
                    continue

                # Confirm selection
                config = accounts_config[selected_name]
                print(f"\nSelected: {selected_name}")
                print(f"   Account: {selected_info['account_number']}")
                print(f"   Balance: {format_currency(selected_info['portfolio_value'])}")
                print(f"   Status: {selected_info['status']}")

                return config['api_key'], config['secret_key'], selected_info
            else:
                print(f"Invalid selection. Please enter a number between 1 and {len(account_list)}")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")
        except KeyboardInterrupt:
            print("\nAccount selection cancelled")
            sys.exit(0)


if __name__ == '__main__':
    # Test the selector
    api_key, secret_key, info = select_account()
    print(f"\nAccount selected successfully!")
    print(f"   Account: {info['account_number']}")
    print(f"   Balance: {format_currency(info['portfolio_value'])}")
