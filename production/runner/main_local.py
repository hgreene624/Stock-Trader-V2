"""
Local wrapper for production trading runner.
Adapts paths for local execution (no Docker).
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Override paths for local execution
LOGS_DIR = os.getenv('LOGS_DIR', str(PROJECT_ROOT / 'production' / 'local_logs'))
DATA_DIR = os.getenv('DATA_DIR', str(PROJECT_ROOT / 'production' / 'local_data'))
CONFIG_PATH = os.getenv('CONFIG_PATH', str(PROJECT_ROOT / 'production' / 'configs' / 'production.yaml'))

# Create directories if they don't exist
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

print(f"Local execution mode:")
print(f"  Logs: {LOGS_DIR}")
print(f"  Data: {DATA_DIR}")
print(f"  Config: {CONFIG_PATH}")
print()

# Import and patch the main runner
from production.runner import main

# Monkey-patch the paths before running
original_setup_logging = main.ProductionTradingRunner._setup_logging

def patched_setup_logging(self):
    """Patched logging setup for local execution."""
    import logging

    log_level = os.getenv('LOG_LEVEL', 'INFO')

    # Ensure logs directory exists
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{LOGS_DIR}/production.log'),
            logging.StreamHandler()
        ]
    )

    # Create JSONL log file handles for structured logging
    self.orders_log = open(f'{LOGS_DIR}/orders.jsonl', 'a')
    self.trades_log = open(f'{LOGS_DIR}/trades.jsonl', 'a')
    self.performance_log = open(f'{LOGS_DIR}/performance.jsonl', 'a')
    self.errors_log = open(f'{LOGS_DIR}/errors.jsonl', 'a')

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
            'budget_fraction': budget_fraction
        })

        main.logger.info(f"Loaded model: {model_name} (budget={budget_fraction})")

    main.logger.info(f"Successfully loaded {len(self.models)} models")

# Apply patch
main.ProductionTradingRunner._load_models = patched_load_models

# Patch data cache path
original_init = main.HybridDataFetcher.__init__

def patched_data_fetcher_init(self, broker_adapter, cache_dir=None, max_lookback_days=250, api_fetch_bars=10):
    """Patched data fetcher init for local execution."""
    if cache_dir is None:
        cache_dir = DATA_DIR
    original_init(self, broker_adapter, cache_dir, max_lookback_days, api_fetch_bars)

# Apply patch
main.HybridDataFetcher.__init__ = patched_data_fetcher_init

# Run the main function
if __name__ == '__main__':
    try:
        runner = main.ProductionTradingRunner(CONFIG_PATH)
        runner.run()
    except KeyboardInterrupt:
        print("\n\nReceived Ctrl+C, shutting down gracefully...")
        sys.exit(0)
