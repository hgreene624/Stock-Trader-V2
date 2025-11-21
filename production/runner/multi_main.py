#!/usr/bin/env python3
"""
Multi-Account Trading Bot Orchestrator

Spawns multiple TradingBot processes from accounts.yaml configuration.
Each account runs in its own process with isolated credentials and health endpoints.

Usage:
    python -m production.runner.multi_main
    python -m production.runner.multi_main --accounts PA3T8N36NVJK PA3I05031HZL
    python -m production.runner.multi_main --config production/configs/accounts.yaml
"""

import argparse
import logging
import multiprocessing
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# Use 'fork' on macOS to avoid pickle issues with signal handlers
if sys.platform == 'darwin':
    multiprocessing.set_start_method('fork', force=True)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from production.runner.main import main as run_single_account

logger = logging.getLogger(__name__)


class MultiAccountOrchestrator:
    """Orchestrates multiple TradingBot processes for different accounts."""

    def __init__(self, accounts_config: Dict, selected_accounts: Optional[List[str]] = None):
        """
        Initialize orchestrator.

        Args:
            accounts_config: Parsed accounts.yaml configuration
            selected_accounts: List of account IDs to run (None = all)
        """
        self.accounts_config = accounts_config
        self.selected_accounts = selected_accounts
        self.processes: Dict[str, multiprocessing.Process] = {}
        self.shutdown_requested = False

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True

    def _get_accounts_to_run(self) -> Dict[str, Dict]:
        """Get accounts to run based on selection."""
        all_accounts = self.accounts_config.get('accounts', {})

        if self.selected_accounts:
            # Filter to selected accounts
            accounts = {}
            for account_id in self.selected_accounts:
                if account_id in all_accounts:
                    accounts[account_id] = all_accounts[account_id]
                else:
                    logger.warning(f"Account {account_id} not found in config, skipping")
            return accounts
        else:
            # Run all accounts
            return all_accounts

    def _run_account_process(self, account_id: str, account_config: Dict):
        """
        Run a single account's TradingBot in a subprocess.

        This function is called in a separate process.
        """
        try:
            # Set environment variables for this account
            os.environ['ALPACA_API_KEY'] = account_config['api_key']
            os.environ['ALPACA_SECRET_KEY'] = account_config['secret_key']
            os.environ['ACCOUNT_ID'] = account_id
            os.environ['HEALTH_PORT'] = str(account_config.get('health_port', 8080))

            # Set config path - use local path if not in Docker
            if not os.path.exists('/app/configs/production.yaml'):
                os.environ['CONFIG_PATH'] = str(project_root / 'production' / 'configs' / 'production.yaml')

            # Set paper/live mode
            if account_config.get('paper', True):
                os.environ['MODE'] = 'paper'
            else:
                os.environ['MODE'] = 'live'

            # Set models filter
            models = account_config.get('models', [])
            if models:
                os.environ['ACCOUNT_MODELS'] = ','.join(models)

            # Configure logging for this process
            base_log_dir = os.getenv('LOG_DIR', str(project_root / 'production' / 'local_logs'))
            log_dir = Path(base_log_dir) / account_id
            log_dir.mkdir(parents=True, exist_ok=True)
            os.environ['LOG_DIR'] = str(log_dir)

            # Run the trading bot
            logger.info(f"[{account_id}] Starting TradingBot on port {account_config.get('health_port', 8080)}")
            run_single_account()

        except Exception as e:
            logger.error(f"[{account_id}] Process failed: {e}")
            raise

    def start(self):
        """Start all account processes."""
        accounts = self._get_accounts_to_run()

        if not accounts:
            logger.error("No accounts to run!")
            return

        logger.info(f"Starting {len(accounts)} account(s)...")

        for account_id, account_config in accounts.items():
            logger.info(f"Spawning process for account: {account_id}")

            process = multiprocessing.Process(
                target=self._run_account_process,
                args=(account_id, account_config),
                name=f"TradingBot-{account_id}"
            )
            process.start()
            self.processes[account_id] = process

            # Small delay between spawns to avoid port conflicts
            time.sleep(1)

        logger.info(f"All {len(self.processes)} account(s) started")

        # Setup signal handlers AFTER all processes are started
        # (to avoid pickle issues on macOS with 'spawn' start method)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def monitor(self):
        """Monitor running processes and restart if needed."""
        while not self.shutdown_requested:
            for account_id, process in list(self.processes.items()):
                if not process.is_alive():
                    exit_code = process.exitcode
                    logger.warning(
                        f"[{account_id}] Process died with exit code {exit_code}"
                    )

                    # Restart the process
                    if not self.shutdown_requested:
                        logger.info(f"[{account_id}] Restarting process...")
                        accounts = self._get_accounts_to_run()
                        if account_id in accounts:
                            new_process = multiprocessing.Process(
                                target=self._run_account_process,
                                args=(account_id, accounts[account_id]),
                                name=f"TradingBot-{account_id}"
                            )
                            new_process.start()
                            self.processes[account_id] = new_process

            time.sleep(5)  # Check every 5 seconds

    def shutdown(self):
        """Gracefully shutdown all processes."""
        logger.info("Shutting down all account processes...")

        # Send SIGTERM to all processes
        for account_id, process in self.processes.items():
            if process.is_alive():
                logger.info(f"[{account_id}] Sending SIGTERM...")
                process.terminate()

        # Wait for processes to finish
        timeout = 30
        start = time.time()
        for account_id, process in self.processes.items():
            remaining = timeout - (time.time() - start)
            if remaining > 0:
                process.join(timeout=remaining)

            if process.is_alive():
                logger.warning(f"[{account_id}] Force killing process...")
                process.kill()
                process.join(timeout=5)

        logger.info("All processes stopped")


def load_accounts_config(config_path: str) -> Dict:
    """Load accounts configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point for multi-account orchestrator."""
    parser = argparse.ArgumentParser(
        description='Multi-Account Trading Bot Orchestrator'
    )
    parser.add_argument(
        '--config',
        default='production/configs/accounts.yaml',
        help='Path to accounts configuration file'
    )
    parser.add_argument(
        '--accounts',
        nargs='+',
        help='Specific account IDs to run (default: all)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    accounts_config = load_accounts_config(str(config_path))

    # Create and run orchestrator
    orchestrator = MultiAccountOrchestrator(
        accounts_config=accounts_config,
        selected_accounts=args.accounts
    )

    try:
        orchestrator.start()
        orchestrator.monitor()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        orchestrator.shutdown()


if __name__ == '__main__':
    main()
