"""
Monkey Test Framework

Tests if a strategy beats random chance by comparing it against random baseline variants.

From "Building Algorithmic Trading Systems" p.123-128:
"Run 'monkey tests' by replacing your entry and/or exit with randomized logic;
demand your system beat >90% of random runs when built, and rerun these tests
every 6-12 months to detect fading edges before losses pile up."

Usage:
    from engines.validation.monkey_tests import MonkeyTester

    tester = MonkeyTester(model, config)
    result = tester.run(n_variants=1000, variant_type='random_selection')

    print(f"Beat {result.beat_pct*100}% of random variants")
    # Target: >90% to validate strategy has edge
"""

import random
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backtest.runner import BacktestRunner
from models.base import BaseModel, Context


@dataclass
class MonkeyTestResult:
    """Results from monkey test validation."""
    real_cagr: float
    real_sharpe: float
    real_max_dd: float
    random_cagrs: List[float]
    random_sharpes: List[float]
    percentile: float
    beat_pct: float
    p_value: float
    n_variants: int
    variant_type: str

    def passes(self, threshold: float = 0.90) -> bool:
        """Check if strategy passes monkey test."""
        return self.beat_pct >= threshold

    def __str__(self) -> str:
        """Human-readable summary."""
        status = "✅ PASS" if self.passes() else "❌ FAIL"
        return f"""
{'='*60}
MONKEY TEST RESULTS ({self.variant_type})
{'='*60}
Real Strategy:
  CAGR:        {self.real_cagr:>7.2%}
  Sharpe:      {self.real_sharpe:>7.2f}
  Max DD:      {self.real_max_dd:>7.2%}

Random Baselines (n={self.n_variants}):
  CAGR mean:   {np.mean(self.random_cagrs):>7.2%}
  CAGR std:    {np.std(self.random_cagrs):>7.2%}

Ranking:
  Percentile:  {self.percentile:>7.1f}
  Beat %:      {self.beat_pct*100:>6.1f}%
  p-value:     {self.p_value:>7.4f}

Result: {status} (threshold: 90%)
{'='*60}
"""


class RandomModelWrapper(BaseModel):
    """
    Wraps a model to randomize specific behaviors.

    Supports:
    - Random selection: Random asset/sector picks
    - Random entries: Random entry timing
    - Random exits: Random exit timing
    - Fully random: All random
    """

    def __init__(self, base_model: BaseModel, randomize_mode: str = 'selection'):
        """
        Args:
            base_model: Original model to wrap
            randomize_mode: 'selection', 'entries', 'exits', or 'full'
        """
        self.base_model = base_model
        self.randomize_mode = randomize_mode
        self.random_seed = None

        # Set model_id if base model has it
        if hasattr(base_model, 'model_id'):
            self.model_id = f"{base_model.model_id}_random_{randomize_mode}"
        else:
            self.model_id = f"{base_model.name}_random_{randomize_mode}"

        # Inherit base model properties
        super().__init__(
            name=f"{base_model.name}_random_{randomize_mode}",
            version=base_model.version,
            universe=base_model.universe
        )

    def set_seed(self, seed: int):
        """Set random seed for reproducibility."""
        self.random_seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def generate_target_weights(self, context: Context):
        """Generate weights with randomization."""
        from models.base import ModelOutput

        # Get base model's output
        base_output = self.base_model.generate_target_weights(context)

        # Extract weights from ModelOutput
        base_weights = base_output.weights if isinstance(base_output, ModelOutput) else base_output

        # Randomize based on mode
        if self.randomize_mode == 'selection':
            # Keep timing (when to trade) but randomize what to trade
            random_weights = self._randomize_selection(base_weights, context)
        elif self.randomize_mode == 'entries':
            # TODO: Randomize entry timing (more complex, requires state tracking)
            random_weights = base_weights
        elif self.randomize_mode == 'exits':
            # TODO: Randomize exit timing (more complex, requires state tracking)
            random_weights = base_weights
        elif self.randomize_mode == 'full':
            # Fully random weights
            random_weights = self._generate_fully_random_weights(context)
        else:
            random_weights = base_weights

        # Return ModelOutput with randomized weights
        return ModelOutput(
            model_name=self.model_id,
            timestamp=context.timestamp,
            weights=random_weights,
            hold_current=base_output.hold_current if isinstance(base_output, ModelOutput) else False
        )

    def _randomize_selection(self, base_weights: Dict[str, float], context: Context) -> Dict[str, float]:
        """Randomize WHICH assets are selected, preserve total allocation."""

        # Count how many assets are selected (non-zero weights)
        n_selected = sum(1 for w in base_weights.values() if w > 0)
        total_weight = sum(base_weights.values())

        if n_selected == 0:
            return {}

        # Randomly select same number of assets
        available_assets = list(context.asset_features.keys())
        selected = random.sample(available_assets, min(n_selected, len(available_assets)))

        # Distribute weight randomly among selected
        random_weights = np.random.dirichlet(np.ones(len(selected)))

        # Scale to match total weight
        weights = {}
        for asset, weight in zip(selected, random_weights):
            weights[asset] = weight * total_weight

        return weights

    def _generate_fully_random_weights(self, context: Context) -> Dict[str, float]:
        """Generate completely random weights."""

        # Randomly decide how many assets to hold (1 to 4)
        n_assets = random.randint(1, min(4, len(self.universe)))

        # Randomly select assets
        selected = random.sample(list(context.asset_features.keys()), n_assets)

        # Random weights using Dirichlet (ensures they sum to 1)
        random_weights = np.random.dirichlet(np.ones(n_assets))

        weights = {}
        for asset, weight in zip(selected, random_weights):
            weights[asset] = weight

        return weights


class MonkeyTester:
    """
    Runs monkey tests to validate strategy edge.

    Example:
        tester = MonkeyTester(model, config)
        result = tester.run(n_variants=1000)

        if result.passes():
            print("Strategy has real edge!")
        else:
            print("Strategy is no better than random")
    """

    def __init__(
        self,
        model: BaseModel,
        config_path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """
        Initialize monkey tester.

        Args:
            model: Strategy to test
            config_path: Path to backtest config
            start_date: Optional start date override
            end_date: Optional end date override
        """
        self.model = model
        self.config_path = config_path
        self.start_date = start_date
        self.end_date = end_date

    def run(
        self,
        n_variants: int = 1000,
        variant_type: str = 'selection',
        show_progress: bool = True
    ) -> MonkeyTestResult:
        """
        Run monkey test.

        Args:
            n_variants: Number of random variants to generate (default: 1000)
            variant_type: 'selection', 'entries', 'exits', or 'full'
            show_progress: Print progress updates

        Returns:
            MonkeyTestResult with percentile ranking and pass/fail
        """

        if show_progress:
            print(f"\n{'='*60}")
            print(f"RUNNING MONKEY TEST")
            print(f"{'='*60}")
            print(f"Variants: {n_variants}")
            print(f"Type: {variant_type}")
            print(f"Model: {self.model.name}")
            print(f"{'='*60}\n")

        # 1. Run real strategy
        if show_progress:
            print("Running real strategy...")

        real_results = self._run_backtest(self.model)
        real_cagr = real_results['cagr']
        real_sharpe = real_results['sharpe']
        real_max_dd = real_results['max_drawdown']

        if show_progress:
            print(f"  Real CAGR: {real_cagr:.2%}")
            print(f"  Real Sharpe: {real_sharpe:.2f}\n")

        # 2. Run random variants
        if show_progress:
            print(f"Running {n_variants} random variants...")

        random_cagrs = []
        random_sharpes = []

        for i in range(n_variants):
            # Create random variant
            random_model = RandomModelWrapper(self.model, randomize_mode=variant_type)
            random_model.set_seed(i)  # Reproducible randomness

            # Run backtest
            results = self._run_backtest(random_model)
            random_cagrs.append(results['cagr'])
            random_sharpes.append(results['sharpe'])

            # Progress update
            if show_progress and (i + 1) % 100 == 0:
                print(f"  Completed {i+1}/{n_variants} variants...")

        # 3. Calculate statistics
        percentile = self._calculate_percentile(real_cagr, random_cagrs)
        beat_pct = sum(real_cagr > r for r in random_cagrs) / n_variants
        p_value = 1.0 - beat_pct  # Simplified p-value

        result = MonkeyTestResult(
            real_cagr=real_cagr,
            real_sharpe=real_sharpe,
            real_max_dd=real_max_dd,
            random_cagrs=random_cagrs,
            random_sharpes=random_sharpes,
            percentile=percentile,
            beat_pct=beat_pct,
            p_value=p_value,
            n_variants=n_variants,
            variant_type=variant_type
        )

        if show_progress:
            print(result)

        return result

    def _run_backtest(self, model: BaseModel) -> Dict[str, float]:
        """Run backtest and return key metrics."""
        runner = BacktestRunner(self.config_path)

        results = runner.run(
            model=model,
            start_date=self.start_date,
            end_date=self.end_date
        )

        metrics = results['metrics']
        return {
            'cagr': metrics['cagr'],
            'sharpe': metrics['sharpe_ratio'],
            'max_drawdown': metrics['max_drawdown'],
            'total_return': metrics['total_return']
        }

    def _calculate_percentile(self, value: float, distribution: List[float]) -> float:
        """Calculate percentile rank of value in distribution."""
        below = sum(1 for x in distribution if x < value)
        return (below / len(distribution)) * 100


def monkey_test(
    model: BaseModel,
    config_path: str,
    n_variants: int = 1000,
    variant_type: str = 'selection',
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> MonkeyTestResult:
    """
    Convenience function to run monkey test.

    Args:
        model: Strategy to test
        config_path: Path to backtest config
        n_variants: Number of random variants (default: 1000)
        variant_type: 'selection', 'entries', 'exits', or 'full'
        start_date: Optional start date override
        end_date: Optional end date override

    Returns:
        MonkeyTestResult

    Example:
        from models.sector_rotation_v3 import SectorRotationModel_v3
        from engines.validation.monkey_tests import monkey_test

        model = SectorRotationModel_v3(...)
        result = monkey_test(model, 'configs/base/system.yaml', n_variants=1000)

        if result.passes():
            print("Strategy validated!")
    """
    tester = MonkeyTester(model, config_path, start_date, end_date)
    return tester.run(n_variants=n_variants, variant_type=variant_type)
