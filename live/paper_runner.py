"""
Paper Trading Runner

Orchestrates paper trading execution:
1. Load models with lifecycle_stage in ['candidate', 'paper']
2. Run continuous execution loop with live data
3. Use broker paper endpoints for execution
4. Track performance for lifecycle promotion validation

Lifecycle Filtering:
- Only loads models at 'candidate' or 'paper' stages
- Research models are excluded (backtest only)
- Live models are excluded (production trading only)
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


class PaperRunner:
    """
    Runs paper trading with lifecycle-filtered models.

    Only executes models at 'candidate' or 'paper' lifecycle stages.
    This ensures:
    - Research models stay in backtest-only mode
    - Production models are reserved for live trading
    - Proper progression through lifecycle gates
    """

    def __init__(
        self,
        config_path: str,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize paper trading runner.

        Args:
            config_path: Path to YAML config file
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()

        # Load configuration
        self.config = ConfigLoader.load_yaml(config_path)
        self.logger.info(f"Loaded config from {config_path}")

        # Extract config sections
        self.paper_config = self.config.get('paper_trading', {})
        self.model_config = self.config.get('models', {})
        self.risk_config = self.config.get('risk', {})

        # Initialize components
        self.pipeline: Optional[DataPipeline] = None
        self.models: List[BaseModel] = []
        self.portfolio_engine: Optional[PortfolioEngine] = None
        self.attribution_tracker: Optional[AttributionTracker] = None
        self.risk_engine: Optional[RiskEngine] = None

        # Lifecycle state tracking
        self.lifecycle_file = Path("configs/.model_lifecycle.json")
        self.lifecycle_states: Dict[str, str] = {}

        # Paper trading state
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
            self.logger.info("No lifecycle state file found, assuming all models are 'research'")
            return {}

    def filter_models_by_lifecycle(self, models: List[BaseModel]) -> List[BaseModel]:
        """
        Filter models to only include those at 'candidate' or 'paper' stages.

        Args:
            models: List of all available models

        Returns:
            List of models eligible for paper trading
        """
        # Load current lifecycle states
        self.lifecycle_states = self.load_lifecycle_states()

        # Filter models
        eligible_models = []
        for model in models:
            # Get lifecycle stage (default to model's configured stage if not in file)
            stage = self.lifecycle_states.get(model.name, model.lifecycle_stage)

            # Only include candidate or paper stage models
            if stage in ['candidate', 'paper']:
                eligible_models.append(model)
                self.logger.info(
                    f"Model {model.name} included for paper trading (lifecycle: {stage})"
                )
            else:
                self.logger.info(
                    f"Model {model.name} excluded from paper trading (lifecycle: {stage})"
                )

        return eligible_models

    def initialize_components(self, models: List[BaseModel]):
        """
        Initialize trading components.

        Args:
            models: List of models to trade (pre-filtered by lifecycle)
        """
        if not models:
            raise ValueError("No models provided for paper trading")

        # Filter models by lifecycle stage
        self.models = self.filter_models_by_lifecycle(models)

        if not self.models:
            raise ValueError(
                "No models eligible for paper trading. "
                "Models must be at 'candidate' or 'paper' lifecycle stage. "
                "Use 'python backtest/cli.py promote' to promote models."
            )

        self.logger.info(f"Initialized with {len(self.models)} models for paper trading")

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

        self.logger.info("Paper trading components initialized")

    def run(
        self,
        models: List[BaseModel],
        execution_interval_minutes: int = 240  # Default: 4 hours (H4)
    ):
        """
        Run paper trading loop.

        Args:
            models: List of model instances to trade
            execution_interval_minutes: Minutes between executions (default 240 = 4H)
        """
        # Initialize components (includes lifecycle filtering)
        self.initialize_components(models)

        self.logger.info("=" * 70)
        self.logger.info("PAPER TRADING STARTED")
        self.logger.info("=" * 70)
        self.logger.info(f"Models: {[m.name for m in self.models]}")
        self.logger.info(f"Lifecycle stages: {[self.lifecycle_states.get(m.name, m.lifecycle_stage) for m in self.models]}")
        self.logger.info(f"Execution interval: {execution_interval_minutes} minutes")
        self.logger.info("=" * 70)

        self.is_running = True

        try:
            while self.is_running:
                # Execute trading cycle
                self._execute_trading_cycle()

                # Wait for next execution
                self.logger.info(f"Sleeping for {execution_interval_minutes} minutes...")
                time.sleep(execution_interval_minutes * 60)

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal, stopping paper trading...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Error in paper trading loop: {e}")
            raise

    def _execute_trading_cycle(self):
        """Execute a single trading cycle."""
        try:
            # Record execution time
            execution_time = datetime.now(timezone.utc)
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"TRADING CYCLE: {execution_time.isoformat()}")
            self.logger.info(f"{'='*70}")

            # 1. Update data pipeline (fetch latest data)
            self.logger.info("Fetching latest market data...")
            # Note: In production, this would call live data APIs
            # For now, we'll use the existing pipeline

            # 2. Get current regime
            # Note: In production, regime would be calculated from latest data
            # For now, create a placeholder
            current_regime = RegimeState(
                timestamp=pd.Timestamp(execution_time),
                equity_regime="neutral",
                vol_regime="normal",
                crypto_regime="neutral",
                macro_regime="neutral"
            )

            # 3. Get broker positions and NAV
            # Note: In production, query paper broker API
            # For now, placeholder
            current_nav = Decimal("100000.00")

            # 4. Generate target weights from each model
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

            # 5. Aggregate weights via portfolio engine
            # Note: In production, this would generate actual orders
            self.logger.info("Aggregating model outputs...")

            # 6. Apply risk controls
            self.logger.info("Applying risk controls...")

            # 7. Submit orders to paper broker
            # Note: In production, submit to broker paper API
            self.logger.info("Orders submitted to paper broker (placeholder)")

            self.last_execution_time = execution_time

        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}")
            raise

    def stop(self):
        """Stop paper trading loop."""
        self.is_running = False
        self.logger.info("Paper trading stopped")

    def get_status(self) -> Dict:
        """
        Get current paper trading status.

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
            'last_execution_time': self.last_execution_time.isoformat() if self.last_execution_time else None
        }


def main():
    """Main entry point for paper trading."""
    import argparse

    parser = argparse.ArgumentParser(description="Run paper trading")
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

    args = parser.parse_args()

    # Create logger
    logger = StructuredLogger()

    # Create runner
    runner = PaperRunner(
        config_path=args.config,
        logger=logger
    )

    # Note: In production, models would be loaded from config
    # For now, this is a placeholder
    print("Paper runner initialized")
    print("To run paper trading, call runner.run(models=[model1, model2, ...])")
    print("\nLifecycle filtering:")
    print("- Only models at 'candidate' or 'paper' stages will be executed")
    print("- Use 'python backtest/cli.py promote' to promote models")


if __name__ == "__main__":
    main()
