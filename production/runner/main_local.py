"""
Local wrapper for production trading runner.
Adapts paths for local execution (no Docker).
Supports multi-account operation with instance locking.
"""

import os
import sys
import argparse
import yaml
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from production.runner.instance_lock import get_lock_manager, acquire_lock, release_lock

# Override paths for local execution
LOGS_DIR = os.getenv('LOGS_DIR', str(PROJECT_ROOT / 'production' / 'local_logs'))
DATA_DIR = os.getenv('DATA_DIR', str(PROJECT_ROOT / 'production' / 'local_data'))
CONFIG_PATH = os.getenv('CONFIG_PATH', str(PROJECT_ROOT / 'production' / 'configs' / 'production.yaml'))
ACCOUNTS_PATH = PROJECT_ROOT / 'production' / 'configs' / 'accounts.yaml'


def load_accounts():
    """Load accounts configuration."""
    with open(ACCOUNTS_PATH, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('accounts', {}), config.get('default_models', [])


def resolve_env_vars(value):
    """Resolve ${VAR} environment variable references."""
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        var_name = value[2:-1]
        return os.getenv(var_name, '')
    return value


def select_account(requested_account=None):
    """
    Select an account to use.

    Args:
        requested_account: Specific account to use, or None for auto-select

    Returns:
        tuple: (account_name, account_config) or (None, None) if no account available
    """
    accounts, default_models = load_accounts()
    lock_manager = get_lock_manager()

    if requested_account:
        # Use specific account
        if requested_account not in accounts:
            print(f"Error: Account '{requested_account}' not found in accounts.yaml")
            print(f"Available accounts: {', '.join(accounts.keys())}")
            return None, None

        account_config = accounts[requested_account]

        # Check if locked
        if lock_manager.is_locked(requested_account):
            lock_info = lock_manager.get_lock_info(requested_account)
            print(f"Error: Account '{requested_account}' is locked by PID {lock_info.get('pid')} on {lock_info.get('hostname')}")
            return None, None

        # Resolve env vars
        account_config['api_key'] = resolve_env_vars(account_config['api_key'])
        account_config['secret_key'] = resolve_env_vars(account_config['secret_key'])

        # Use default models if not specified
        if 'models' not in account_config:
            account_config['models'] = default_models

        return requested_account, account_config

    # Auto-select first available account
    for account_name, account_config in accounts.items():
        if not lock_manager.is_locked(account_name):
            # Resolve env vars
            account_config['api_key'] = resolve_env_vars(account_config['api_key'])
            account_config['secret_key'] = resolve_env_vars(account_config['secret_key'])

            # Use default models if not specified
            if 'models' not in account_config:
                account_config['models'] = default_models

            return account_name, account_config

    print("Error: All accounts are currently locked")
    print("Active locks:")
    for name, info in lock_manager.list_locks().items():
        print(f"  {name}: PID {info.get('pid')} on {info.get('hostname')}")

    return None, None


def list_accounts():
    """List all accounts and their lock status."""
    accounts, _ = load_accounts()
    lock_manager = get_lock_manager()

    print("\nAvailable Accounts:")
    print("-" * 60)

    for name, config in accounts.items():
        status = "LOCKED" if lock_manager.is_locked(name) else "available"
        paper = "paper" if config.get('paper', True) else "LIVE"
        models = config.get('models', ['default'])
        desc = config.get('description', '')

        print(f"  {name} [{paper}] - {status}")
        if desc:
            print(f"    Description: {desc}")
        print(f"    Models: {', '.join(models)}")

        if lock_manager.is_locked(name):
            info = lock_manager.get_lock_info(name)
            print(f"    Locked by: PID {info.get('pid')} on {info.get('hostname')}")
        print()

    print("-" * 60)

# Create directories if they don't exist
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

print(f"Local execution mode:")
print(f"  Logs: {LOGS_DIR}")
print(f"  Data: {DATA_DIR}")
print(f"  Config: {CONFIG_PATH}")
print()

# Set environment variables for main.py to use
os.environ['DATA_DIR'] = DATA_DIR
os.environ['LOGS_DIR'] = LOGS_DIR

# Import and patch the main runner
from production.runner import main

# Monkey-patch the paths before running
original_setup_logging = main.ProductionTradingRunner._setup_logging

def patched_setup_logging(self):
    """Patched logging setup for local execution."""
    import logging

    log_level = os.getenv('LOG_LEVEL', 'INFO')
    # Use environment variable to get account-specific logs directory
    logs_dir = os.getenv('LOGS_DIR', LOGS_DIR)

    # Ensure logs directory exists
    Path(logs_dir).mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{logs_dir}/production.log'),
            logging.StreamHandler()
        ]
    )

    # Create JSONL log file handles for structured logging
    self.orders_log = open(f'{logs_dir}/orders.jsonl', 'a')
    self.trades_log = open(f'{logs_dir}/trades.jsonl', 'a')
    self.performance_log = open(f'{logs_dir}/performance.jsonl', 'a')
    self.errors_log = open(f'{logs_dir}/errors.jsonl', 'a')

    main.logger.info("Logging configured (JSONL audit logs enabled) - LOCAL MODE")

# Apply patch
main.ProductionTradingRunner._setup_logging = patched_setup_logging

# Patch model loading to use local paths
original_load_models = main.ProductionTradingRunner._load_models

def patched_load_models(self):
    """Patched model loading for local execution."""
    import importlib.util
    from pathlib import Path

    models_dir = PROJECT_ROOT / 'production' / 'models'

    if not models_dir.exists():
        raise RuntimeError(f"Models directory not found: {models_dir}")

    model_dirs = [d for d in models_dir.iterdir() if d.is_dir() and not d.name.startswith('__')]
    main.logger.info(f"Loading models from {models_dir} ({len(model_dirs)} found)")

    for model_dir in model_dirs:
        manifest_path = model_dir / 'manifest.json'

        if not manifest_path.exists():
            main.logger.warning(f"No manifest found in {model_dir.name}")
            continue

        # Load manifest
        import json
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        model_name = manifest['model_name']
        class_name = manifest['class_name']
        budget_fraction = manifest.get('budget_fraction', 1.0)

        # Load model module
        model_file = model_dir / 'model.py'
        spec = importlib.util.spec_from_file_location(model_name, model_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Instantiate model
        model_class = getattr(module, class_name)
        model_instance = model_class(**manifest.get('parameters', {}))

        self.models.append({
            'instance': model_instance,
            'name': model_name,
            'budget_fraction': budget_fraction,
            'universe': manifest.get('universe', [])
        })

        main.logger.info(f"Loaded model: {model_name} (budget={budget_fraction})")

    main.logger.info(f"Successfully loaded {len(self.models)} models")

# Apply patch
main.ProductionTradingRunner._load_models = patched_load_models

# Patch data cache path - DISABLED (causing method binding issues)
# Instead, we'll update main.py to use environment variable for cache_dir

def create_filtered_model_loader(account_config):
    """Create a model loader that filters by account's models list."""
    def patched_load_models_with_filter(self):
        import importlib.util
        import json
        from pathlib import Path

        models_dir = PROJECT_ROOT / 'production' / 'models'

        if not models_dir.exists():
            raise RuntimeError(f"Models directory not found: {models_dir}")

        model_dirs = [d for d in models_dir.iterdir() if d.is_dir() and not d.name.startswith('__')]
        main.logger.info(f"Loading models from {models_dir} ({len(model_dirs)} found)")

        # Get allowed models from account config
        allowed_models = None
        if account_config:
            allowed_models = account_config.get('models', None)
            if allowed_models:
                main.logger.info(f"Filtering to account models: {allowed_models}")

        for model_dir in model_dirs:
            manifest_path = model_dir / 'manifest.json'

            if not manifest_path.exists():
                main.logger.warning(f"No manifest found in {model_dir.name}")
                continue

            # Load manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            model_name = manifest['model_name']

            # Filter by account's allowed models
            if allowed_models and model_name not in allowed_models:
                main.logger.info(f"Skipping model {model_name} (not in account's models list)")
                continue

            class_name = manifest['class_name']
            budget_fraction = manifest.get('budget_fraction', 1.0)

            # Load model module
            model_file = model_dir / 'model.py'
            spec = importlib.util.spec_from_file_location(model_name, model_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Instantiate model
            model_class = getattr(module, class_name)
            model_instance = model_class(**manifest.get('parameters', {}))

            self.models.append({
                'instance': model_instance,
                'name': model_name,
                'budget_fraction': budget_fraction,
                'universe': manifest.get('universe', [])
            })

            main.logger.info(f"Loaded model: {model_name} (budget={budget_fraction})")

        main.logger.info(f"Successfully loaded {len(self.models)} models")

    return patched_load_models_with_filter


# Run the main function
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run trading bot locally')
    parser.add_argument('--account', type=str, help='Account name to use (auto-selects if not specified)')
    parser.add_argument('--list', action='store_true', help='List all accounts and exit')
    parser.add_argument('--force', action='store_true', help='Force acquire lock even if already locked')
    args = parser.parse_args()

    # List accounts mode
    if args.list:
        list_accounts()
        sys.exit(0)

    # Select account
    account_name, account_config = select_account(args.account)
    if not account_name:
        sys.exit(1)

    # Acquire lock
    if not acquire_lock(account_name, force=args.force):
        print(f"Failed to acquire lock for account '{account_name}'")
        sys.exit(1)

    # Use the filtered model loading with account config bound
    main.ProductionTradingRunner._load_models = create_filtered_model_loader(account_config)

    # Set API credentials in environment for the runner
    os.environ['ALPACA_API_KEY'] = account_config['api_key']
    os.environ['ALPACA_SECRET_KEY'] = account_config['secret_key']

    # Set health port for this account
    health_port = account_config.get('health_port', 8080)
    os.environ['HEALTH_PORT'] = str(health_port)

    # Create account-specific log directory
    account_logs_dir = Path(LOGS_DIR) / account_name
    account_logs_dir.mkdir(parents=True, exist_ok=True)
    os.environ['LOGS_DIR'] = str(account_logs_dir)

    paper_mode = "PAPER" if account_config.get('paper', True) else "LIVE"
    print(f"\n{'='*60}")
    print(f"Starting trading bot")
    print(f"  Account: {account_name} ({paper_mode})")
    print(f"  Models: {', '.join(account_config.get('models', ['default']))}")
    print(f"  Logs: {account_logs_dir}")
    print(f"  Data: {DATA_DIR}")
    print(f"{'='*60}\n")

    try:
        runner = main.ProductionTradingRunner(CONFIG_PATH)
        runner.run()
    except KeyboardInterrupt:
        print("\n\nReceived Ctrl+C, shutting down gracefully...")
    finally:
        release_lock()
        sys.exit(0)
