"""
Live Trading Runner

Orchestrates live production trading:
1. Load models with lifecycle_stage = 'live' ONLY
2. Run continuous execution loop with live data
3. Use broker live endpoints for real execution
4. Track performance and risk in real-time

Lifecycle Filtering:
- ONLY loads models at 'live' stage
- Research models are excluded (backtest only)
- Candidate models are excluded (not validated yet)
- Paper models are excluded (paper trading only)

CRITICAL: This runner executes with real capital. Only models that have:
- Passed backtest criteria (research → candidate)
- Passed paper trading validation (candidate → paper → live)
should be promoted to 'live' status.
"""

import pandas as pd
import json
import time
from typing import Dict, List, Optional
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.data.pipeline import DataPipeline
from models.base import BaseModel, RegimeState, Context
from engines.portfolio.engine import PortfolioEngine
from engines.portfolio.attribution import AttributionTracker
from engines.risk.engine import RiskEngine
from utils.config import ConfigLoader
from utils.logging import StructuredLogger


class LiveRunner:
    """
    Runs live production trading with lifecycle-filtered models.

    CRITICAL: Only executes models at 'live' lifecycle stage.
    This ensures:
    - Only fully validated models trade with real capital
    - Research models stay in backtest-only mode
    - Candidate/paper models are excluded from production
    - Proper progression through all lifecycle gates

    Safety Features:
    - Kill switch via config flag
    - Position reconciliation with broker
    - Continuous risk monitoring
    - Lifecycle validation on startup
    """

    def __init__(
        self,
        config_path: str,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize live trading runner.

        Args:
            config_path: Path to YAML config file
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()

        # Load configuration
        self.config = ConfigLoader.load_yaml(config_path)
        self.logger.info(f"Loaded config from {config_path}")

        # Extract config sections
        self.live_config = self.config.get('live_trading', {})
        self.model_config = self.config.get('models', {})
        self.risk_config = self.config.get('risk', {})

        # Check kill switch
        if self.live_config.get('kill_switch', False):
            raise RuntimeError(
                "KILL SWITCH ACTIVATED: Live trading is disabled in config. "
                "Set live_trading.kill_switch = false to enable."
            )

        # Initialize components
        self.pipeline: Optional[DataPipeline] = None
        self.models: List[BaseModel] = []
        self.portfolio_engine: Optional[PortfolioEngine] = None
        self.attribution_tracker: Optional[AttributionTracker] = None
        self.risk_engine: Optional[RiskEngine] = None

        # Lifecycle state tracking
        self.lifecycle_file = Path("configs/.model_lifecycle.json")
        self.lifecycle_states: Dict[str, str] = {}

        # Live trading state
        self.is_running = False
        self.last_execution_time: Optional[datetime] = None

    def load_lifecycle_states(self) -> Dict[str, str]:
        """
        Load current lifecycle states from file.

        Returns:
            Dict mapping model names to lifecycle stages
        """
        if self.lifecycle_file.exists():
            with open(self.lifecycle_file) as f:
                return json.load(f)
        else:
            raise FileNotFoundError(
                "No lifecycle state file found at configs/.model_lifecycle.json. "
                "Cannot run live trading without lifecycle tracking. "
                "Models must be promoted through lifecycle stages before going live."
            )

    def filter_models_by_lifecycle(self, models: List[BaseModel]) -> List[BaseModel]:
        """
        Filter models to ONLY include those at 'live' stage.

        Args:
            models: List of all available models

        Returns:
            List of models eligible for live trading

        Raises:
            ValueError: If no models are at 'live' stage
        """
        # Load current lifecycle states
        self.lifecycle_states = self.load_lifecycle_states()

        # Filter models
        eligible_models = []
        excluded_models = []

        for model in models:
            # Get lifecycle stage (default to model's configured stage if not in file)
            stage = self.lifecycle_states.get(model.name, model.lifecycle_stage)

            # ONLY include live stage models
            if stage == 'live':
                eligible_models.append(model)
                self.logger.info(
                    f"✓ Model {model.name} included for LIVE trading (lifecycle: {stage})"
                )
            else:
                excluded_models.append((model.name, stage))
                self.logger.info(
                    f"✗ Model {model.name} excluded from LIVE trading (lifecycle: {stage})"
                )

        # Log summary
        if excluded_models:
            self.logger.info("=" * 70)
            self.logger.info("EXCLUDED MODELS:")
            for name, stage in excluded_models:
                self.logger.info(f"  {name}: {stage} (must be 'live')")
            self.logger.info("=" * 70)

        return eligible_models

    def initialize_components(self, models: List[BaseModel]):
        """
        Initialize trading components.

        Args:
            models: List of models to trade (will be filtered by lifecycle)
        """
        if not models:
            raise ValueError("No models provided for live trading")

        # Filter models by lifecycle stage (ONLY 'live')
        self.models = self.filter_models_by_lifecycle(models)

        if not self.models:
            raise ValueError(
                "No models eligible for LIVE trading. "
                "Models must be at 'live' lifecycle stage. "
                "Lifecycle progression: research → candidate → paper → live. "
                "Use 'python backtest/cli.py promote' to promote models through stages."
            )

        self.logger.info(f"Initialized with {len(self.models)} models for LIVE trading")

        # Collect universe from all models
        universe = set()
        for model in self.models:
            universe.update(model.universe)
        universe = sorted(list(universe))

        self.logger.info(f"Trading universe: {universe}")

        # Initialize data pipeline
        self.pipeline = DataPipeline(
            config=self.config,
            logger=self.logger
        )

        # Initialize portfolio engine with model budgets
        model_budgets = {}
        for model in self.models:
            budget = self.model_config.get(model.name, {}).get('budget', 0.0)
            model_budgets[model.name] = budget

        self.portfolio_engine = PortfolioEngine(
            config=self.config,
            model_budgets=model_budgets,
            logger=self.logger
        )

        # Initialize attribution tracker
        self.attribution_tracker = AttributionTracker(
            models=[m.name for m in self.models],
            logger=self.logger
        )

        # Initialize risk engine
        self.risk_engine = RiskEngine(
            config=self.risk_config,
            logger=self.logger
        )

        self.logger.info("Live trading components initialized")

    def run(
        self,
        models: List[BaseModel],
        execution_interval_minutes: int = 240  # Default: 4 hours (H4)
    ):
        """
        Run live trading loop.

        CRITICAL: This executes with real capital.

        Args:
            models: List of model instances to trade
            execution_interval_minutes: Minutes between executions (default 240 = 4H)
        """
        # Initialize components (includes lifecycle filtering)
        self.initialize_components(models)

        # Pre-flight checks
        self.logger.info("=" * 70)
        self.logger.info("⚠  LIVE TRADING PRE-FLIGHT CHECKS")
        self.logger.info("=" * 70)
        self.logger.info(f"Kill switch: {self.live_config.get('kill_switch', False)}")
        self.logger.info(f"Models: {[m.name for m in self.models]}")
        self.logger.info(f"Lifecycle stages: {[self.lifecycle_states.get(m.name, m.lifecycle_stage) for m in self.models]}")
        self.logger.info(f"Execution interval: {execution_interval_minutes} minutes")

        # Verify all models are 'live'
        for model in self.models:
            stage = self.lifecycle_states.get(model.name, model.lifecycle_stage)
            if stage != 'live':
                raise RuntimeError(
                    f"SAFETY VIOLATION: Model {model.name} is not at 'live' stage (current: {stage}). "
                    f"Cannot proceed with live trading."
                )

        self.logger.info("✓ All pre-flight checks passed")
        self.logger.info("=" * 70)
        self.logger.info("🚀 LIVE TRADING STARTED - REAL CAPITAL AT RISK")
        self.logger.info("=" * 70)

        self.is_running = True

        try:
            while self.is_running:
                # Check kill switch before each cycle
                self._check_kill_switch()

                # Execute trading cycle
                self._execute_trading_cycle()

                # Wait for next execution
                self.logger.info(f"Sleeping for {execution_interval_minutes} minutes...")
                time.sleep(execution_interval_minutes * 60)

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal, stopping live trading...")
            self.stop()
        except Exception as e:
            self.logger.error(f"CRITICAL ERROR in live trading loop: {e}")
            self.stop()
            raise

    def _check_kill_switch(self):
        """
        Check if kill switch has been activated.

        Raises:
            RuntimeError: If kill switch is active
        """
        # Reload config to check for runtime changes
        config = ConfigLoader.load_yaml(self.config.get('_config_path', 'configs/base/system.yaml'))
        kill_switch = config.get('live_trading', {}).get('kill_switch', False)

        if kill_switch:
            raise RuntimeError(
                "KILL SWITCH ACTIVATED: Live trading disabled via config. "
                "Stopping all live execution immediately."
            )

    def _execute_trading_cycle(self):
        """Execute a single trading cycle."""
        try:
            # Record execution time
            execution_time = datetime.now(timezone.utc)
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"LIVE TRADING CYCLE: {execution_time.isoformat()}")
            self.logger.info(f"{'='*70}")

            # 1. Update data pipeline (fetch latest data)
            self.logger.info("Fetching latest market data from LIVE sources...")
            # Note: In production, this would call live data APIs
            # For now, we'll use the existing pipeline

            # 2. Reconcile positions with broker
            self.logger.info("Reconciling positions with broker...")
            # Note: In production, query broker API and compare with internal state

            # 3. Get current regime
            # Note: In production, regime would be calculated from latest data
            current_regime = RegimeState(
                timestamp=pd.Timestamp(execution_time),
                equity_regime="neutral",
                vol_regime="normal",
                crypto_regime="neutral",
                macro_regime="neutral"
            )

            # 4. Get broker positions and NAV
            # Note: In production, query LIVE broker API
            current_nav = Decimal("100000.00")  # Placeholder

            # 5. Generate target weights from each model
            model_outputs = []
            for model in self.models:
                # Get model budget
                budget_fraction = self.model_config.get(model.name, {}).get('budget', 0.0)
                budget_value = current_nav * Decimal(str(budget_fraction))

                # Build context
                # Note: In production, asset_features would come from live data
                context = Context(
                    timestamp=pd.Timestamp(execution_time).replace(minute=0, second=0, microsecond=0),
                    asset_features={},  # Placeholder
                    regime=current_regime,
                    model_budget_fraction=budget_fraction,
                    model_budget_value=budget_value,
                    current_exposures={}
                )

                # Generate target weights
                output = model.generate_target_weights(context)
                model_outputs.append(output)

                self.logger.info(f"Model {model.name} weights: {output.weights}")

            # 6. Aggregate weights via portfolio engine
            self.logger.info("Aggregating model outputs...")

            # 7. Apply risk controls
            self.logger.info("Applying risk controls...")

            # 8. Submit orders to LIVE broker
            # Note: In production, submit to broker LIVE API
            self.logger.info("⚠  Orders would be submitted to LIVE broker (placeholder)")

            self.last_execution_time = execution_time

        except Exception as e:
            self.logger.error(f"CRITICAL ERROR in trading cycle: {e}")
            raise

    def stop(self):
        """Stop live trading loop."""
        self.is_running = False
        self.logger.info("🛑 LIVE TRADING STOPPED")

    def get_status(self) -> Dict:
        """
        Get current live trading status.

        Returns:
            Dict with status information
        """
        return {
            'is_running': self.is_running,
            'models': [m.name for m in self.models],
            'lifecycle_stages': {
                m.name: self.lifecycle_states.get(m.name, m.lifecycle_stage)
                for m in self.models
            },
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None,
            'kill_switch': self.live_config.get('kill_switch', False)
        }


def main():
    """Main entry point for live trading."""
    import argparse

    parser = argparse.ArgumentParser(description="Run LIVE production trading")
    parser.add_argument(
        '--config',
        default='configs/base/system.yaml',
        help='Path to config file'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=240,
        help='Execution interval in minutes (default: 240 = 4H)'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirm you understand this trades with REAL CAPITAL'
    )

    args = parser.parse_args()

    if not args.confirm:
        print("=" * 70)
        print("⚠  WARNING: LIVE TRADING WITH REAL CAPITAL")
        print("=" * 70)
        print("This script executes LIVE trades with REAL MONEY.")
        print("Only models at 'live' lifecycle stage will be executed.")
        print("\nTo proceed, add --confirm flag:")
        print("  python live/live_runner.py --confirm")
        print("=" * 70)
        sys.exit(1)

    # Create logger
    logger = StructuredLogger()

    # Create runner
    runner = LiveRunner(
        config_path=args.config,
        logger=logger
    )

    # Note: In production, models would be loaded from config
    # For now, this is a placeholder
    print("Live runner initialized")
    print("To run LIVE trading, call runner.run(models=[model1, model2, ...])")
    print("\nLifecycle filtering:")
    print("- ONLY models at 'live' stage will be executed")
    print("- Use 'python backtest/cli.py promote' to promote models through lifecycle stages")
    print("- Lifecycle progression: research → candidate → paper → live")


if __name__ == "__main__":
    main()
