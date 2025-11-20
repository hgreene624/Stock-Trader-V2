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
            Path('production/configs/accounts.yaml'),
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
            'paper': account.get('paper', True)
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


def display_accounts(accounts_info: Dict[str, Dict], accounts_config: Dict[str, Dict]) -> None:
    """
    Display accounts in a formatted table.

    Args:
        accounts_info: Dict mapping account name to account info
        accounts_config: Dict mapping account name to config (with 'paper' field)
    """
    print("\n" + "=" * 100)
    print("Available Alpaca Accounts")
    print("=" * 100)
    print(f"{'#':<4} {'Name':<20} {'Account #':<15} {'Type':<8} {'Balance':<15} {'Cash':<15} {'Status':<10}")
    print("-" * 100)

    for idx, (name, info) in enumerate(accounts_info.items(), 1):
        if 'error' in info:
            print(f"{idx:<4} {name:<20} {'ERROR':<15} {'N/A':<8} {'N/A':<15} {'N/A':<15} {info['status']:<10}")
            print(f"     Error: {info['error']}")
        else:
            # Use config to determine if paper or live
            is_paper = accounts_config.get(name, {}).get('paper', True)
            account_type = "PAPER" if is_paper else "LIVE"
            balance = format_currency(info['portfolio_value'])
            cash = format_currency(info['cash'])
            status = info['status']
            account_num = info['account_number'][-6:]  # Last 6 digits

            print(f"{idx:<4} {name:<20} {account_num:<15} {account_type:<8} {balance:<15} {cash:<15} {status:<10}")

    print("=" * 100)


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
