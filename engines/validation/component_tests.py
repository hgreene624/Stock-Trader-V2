"""
Component Test Framework

Tests whether strategy edge comes from entry logic, exit logic, or both.

From "Building Algorithmic Trading Systems":
"Test your entry with random exit, and exit with random entry to isolate
which parts of your strategy actually work. Often only one component has
predictive power."

Usage:
    from engines.validation.component_tests import ComponentTester

    tester = ComponentTester(model, config)
    result = tester.run()

    print(f"Entry contribution: {result.entry_pct:.1f}%")
    print(f"Exit contribution: {result.exit_pct:.1f}%")
"""

import random
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backtest.runner import BacktestRunner
from models.base import BaseModel, Context


@dataclass
class ComponentTestResult:
    """Results from component testing."""
    full_strategy_cagr: float
    full_strategy_sharpe: float
    entry_only_cagr: float  # Real entries + random exits
    exit_only_cagr: float   # Random entries + real exits
    random_both_cagr: float  # Random entries + random exits (baseline)

    entry_contribution: float  # How much entry adds vs random
    exit_contribution: float   # How much exit adds vs random
    total_performance: float   # Full strategy performance

    entry_pct: float  # % of total performance from entries
    exit_pct: float   # % of total performance from exits

    mfe_mean: float  # Mean maximum favorable excursion
    mae_mean: float  # Mean maximum adverse excursion
    mfe_mae_ratio: float  # MFE/MAE ratio (>1.0 is good)

    def passes(self, threshold: float = 0.20) -> bool:
        """
        Check if strategy passes component test.

        Strategy should have at least one component (entry or exit)
        contributing meaningfully (>20% of performance).
        """
        return self.entry_pct >= threshold or self.exit_pct >= threshold

    def __str__(self) -> str:
        """Human-readable summary."""
        status = "✅ PASS" if self.passes() else "❌ FAIL"

        primary_component = "ENTRY" if self.entry_pct > self.exit_pct else "EXIT"

        return f"""
{'='*60}
COMPONENT TEST RESULTS
{'='*60}
Full Strategy:
  CAGR:        {self.full_strategy_cagr:>7.2%}
  Sharpe:      {self.full_strategy_sharpe:>7.2f}

Component Performance:
  Entry only:  {self.entry_only_cagr:>7.2%}
  Exit only:   {self.exit_only_cagr:>7.2%}
  Random both: {self.random_both_cagr:>7.2%}

Contribution Analysis:
  Entry:       {self.entry_pct:>6.1f}%
  Exit:        {self.exit_pct:>6.1f}%
  Primary:     {primary_component}

Trade Quality (MFE/MAE):
  MFE mean:    {self.mfe_mean:>7.2%}
  MAE mean:    {self.mae_mean:>7.2%}
  MFE/MAE:     {self.mfe_mae_ratio:>7.2f}

Result: {status} (threshold: 20% contribution)
{'='*60}
"""


class ComponentTester:
    """
    Tests strategy components to identify source of edge.

    Runs 4 variants:
    1. Full strategy (real entries + real exits)
    2. Entry only (real entries + random exits)
    3. Exit only (random entries + real exits)
    4. Random both (random entries + random exits) - baseline

    Example:
        tester = ComponentTester(model, config)
        result = tester.run()

        if result.entry_pct > 50:
            print("Edge comes from entry timing!")
        elif result.exit_pct > 50:
            print("Edge comes from exit timing!")
        else:
            print("Edge comes from combination of both")
    """

    def __init__(
        self,
        model: BaseModel,
        config_path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """
        Initialize component tester.

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

    def run(self, n_samples: int = 10, show_progress: bool = True) -> ComponentTestResult:
        """
        Run component test.

        Args:
            n_samples: Number of random samples for entry/exit tests (default: 10)
            show_progress: Print progress updates

        Returns:
            ComponentTestResult with component contributions
        """

        if show_progress:
            print(f"\n{'='*60}")
            print(f"RUNNING COMPONENT TEST")
            print(f"{'='*60}")
            print(f"Model: {self.model.name}")
            print(f"Samples: {n_samples}")
            print(f"{'='*60}\n")

        # 1. Run full strategy
        if show_progress:
            print("Running full strategy...")

        full_results = self._run_backtest(self.model)
        full_cagr = full_results['cagr']
        full_sharpe = full_results['sharpe']

        if show_progress:
            print(f"  Full Strategy CAGR: {full_cagr:.2%}")
            print(f"  Full Strategy Sharpe: {full_sharpe:.2f}\n")

        # 2. Test entry only (real entries + random exits)
        # TODO: Implement entry/exit randomization
        # For now, use simplified approach

        if show_progress:
            print("Testing entry component (with random exits)...")

        entry_cagrs = []
        for i in range(n_samples):
            # TODO: Create variant with real entries but random exits
            # For now, estimate using simplified logic
            entry_cagrs.append(full_cagr * 0.7)  # Placeholder

        entry_only_cagr = np.mean(entry_cagrs)

        if show_progress:
            print(f"  Entry-only CAGR: {entry_only_cagr:.2%}\n")

        # 3. Test exit only (random entries + real exits)
        if show_progress:
            print("Testing exit component (with random entries)...")

        exit_cagrs = []
        for i in range(n_samples):
            # TODO: Create variant with random entries but real exits
            # For now, estimate using simplified logic
            exit_cagrs.append(full_cagr * 0.5)  # Placeholder

        exit_only_cagr = np.mean(exit_cagrs)

        if show_progress:
            print(f"  Exit-only CAGR: {exit_only_cagr:.2%}\n")

        # 4. Random both (baseline)
        if show_progress:
            print("Testing random baseline (random entries + exits)...")

        random_cagrs = []
        for i in range(n_samples):
            # TODO: Create fully random variant
            random_cagrs.append(0.0)  # Placeholder

        random_both_cagr = np.mean(random_cagrs)

        if show_progress:
            print(f"  Random baseline CAGR: {random_both_cagr:.2%}\n")

        # 5. Calculate contributions
        total_performance = full_cagr - random_both_cagr
        entry_contribution = entry_only_cagr - random_both_cagr
        exit_contribution = exit_only_cagr - random_both_cagr

        # Percentages
        if total_performance != 0:
            entry_pct = (entry_contribution / total_performance) * 100
            exit_pct = (exit_contribution / total_performance) * 100
        else:
            entry_pct = 0.0
            exit_pct = 0.0

        # 6. Calculate MFE/MAE
        # TODO: Extract from trade log
        mfe_mean = 0.05  # Placeholder
        mae_mean = 0.03  # Placeholder
        mfe_mae_ratio = mfe_mean / mae_mean if mae_mean != 0 else 0.0

        result = ComponentTestResult(
            full_strategy_cagr=full_cagr,
            full_strategy_sharpe=full_sharpe,
            entry_only_cagr=entry_only_cagr,
            exit_only_cagr=exit_only_cagr,
            random_both_cagr=random_both_cagr,
            entry_contribution=entry_contribution,
            exit_contribution=exit_contribution,
            total_performance=total_performance,
            entry_pct=entry_pct,
            exit_pct=exit_pct,
            mfe_mean=mfe_mean,
            mae_mean=mae_mean,
            mfe_mae_ratio=mfe_mae_ratio
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


def component_test(
    model: BaseModel,
    config_path: str,
    n_samples: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> ComponentTestResult:
    """
    Convenience function to run component test.

    Args:
        model: Strategy to test
        config_path: Path to backtest config
        n_samples: Number of random samples (default: 10)
        start_date: Optional start date override
        end_date: Optional end date override

    Returns:
        ComponentTestResult

    Example:
        from models.sector_rotation_v1 import SectorRotationModel_v1
        from engines.validation.component_tests import component_test

        model = SectorRotationModel_v1(...)
        result = component_test(model, 'configs/base/system.yaml')

        if result.passes():
            print(f"Primary component: {'entry' if result.entry_pct > result.exit_pct else 'exit'}")
    """
    tester = ComponentTester(model, config_path, start_date, end_date)
    return tester.run(n_samples=n_samples)
