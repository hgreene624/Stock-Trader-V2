"""
Walk-Forward Optimization

Prevents overfitting by optimizing on rolling training windows and testing on
out-of-sample validation windows.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import logging
import sys
import yaml

from engines.optimization.evolutionary import EvolutionaryOptimizer
from backtest.runner import BacktestRunner
from utils.logging import StructuredLogger


@dataclass
class WalkForwardWindow:
    """Single walk-forward window."""

    train_start: str
    train_end: str
    test_start: str
    test_end: str
    window_id: int

    def __repr__(self):
        return (
            f"Window {self.window_id}: "
            f"Train({self.train_start} to {self.train_end}) → "
            f"Test({self.test_start} to {self.test_end})"
        )


@dataclass
class WalkForwardResult:
    """Results from a single walk-forward window."""

    window: WalkForwardWindow
    best_params: Dict[str, Any]
    train_metrics: Dict[str, float]
    test_metrics: Dict[str, float]

    @property
    def in_sample_cagr(self) -> float:
        return self.train_metrics['cagr']

    @property
    def out_of_sample_cagr(self) -> float:
        return self.test_metrics['cagr']

    def performance_degradation(self) -> float:
        """Calculate degradation from in-sample to out-of-sample."""
        return self.in_sample_cagr - self.out_of_sample_cagr


class WalkForwardOptimizer:
    """
    Walk-forward optimization using existing evolutionary optimizer.
    """

    def __init__(
        self,
        model_class: type,
        param_ranges: Dict[str, tuple],  # {param: (min, max)}
        train_period_months: int = 24,
        test_period_months: int = 12,
        step_months: int = 12,
        population_size: int = 20,
        generations: int = 15,
        logger: logging.Logger = None
    ):
        self.model_class = model_class
        self.param_ranges = param_ranges
        self.train_period_months = train_period_months
        self.test_period_months = test_period_months
        self.step_months = step_months
        self.population_size = population_size
        self.generations = generations
        self.logger = logger or StructuredLogger()

    def generate_windows(
        self,
        start_date: str,
        end_date: str
    ) -> List[WalkForwardWindow]:
        """Generate rolling walk-forward windows."""
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)

        windows = []
        window_id = 1
        current_train_start = start

        while True:
            train_end = current_train_start + pd.DateOffset(months=self.train_period_months)
            test_start = train_end + pd.DateOffset(days=1)
            test_end = test_start + pd.DateOffset(months=self.test_period_months)

            if test_end > end:
                break

            window = WalkForwardWindow(
                train_start=current_train_start.strftime("%Y-%m-%d"),
                train_end=train_end.strftime("%Y-%m-%d"),
                test_start=test_start.strftime("%Y-%m-%d"),
                test_end=test_end.strftime("%Y-%m-%d"),
                window_id=window_id
            )

            windows.append(window)
            current_train_start = current_train_start + pd.DateOffset(months=self.step_months)
            window_id += 1

        return windows

    def optimize_window(
        self,
        window: WalkForwardWindow,
        config_path: str
    ) -> WalkForwardResult:
        """Optimize parameters for a single window."""
        print(f"\n{'='*80}")
        print(f"Optimizing {window}")
        print(f"{'='*80}\n")

        # Step 1: Optimize on training period using EA
        print(f"Step 1: Optimizing on training period ({window.train_start} to {window.train_end})...")

        ea = EvolutionaryOptimizer(
            population_size=self.population_size,
            num_generations=self.generations,
            mutation_rate=0.2,
            crossover_rate=0.7,
            elitism_count=2,
            logger=self.logger
        )

        # Seed random population
        initial_pop = ea.seed_population([], self.param_ranges)

        # Define fitness function
        def fitness_fn(params):
            try:
                # Create model with params
                model = self.model_class(**params)

                # Run backtest on training period
                runner = BacktestRunner(config_path, logger=self.logger)
                result = runner.run(
                    model=model,
                    start_date=window.train_start,
                    end_date=window.train_end
                )

                # Return BPS as fitness
                return result['metrics']['bps']
            except Exception as e:
                self.logger.error(f"Error evaluating params {params}: {e}")
                return -999.0  # Very low fitness for failed runs

        # Run EA
        final_pop, history = ea.optimize(initial_pop, fitness_fn, self.param_ranges, self.generations)

        # Get best from final population
        best_individual = max(final_pop, key=lambda x: x['fitness'])
        best_params = best_individual['params']
        best_fitness = best_individual['fitness']

        print(f"\nBest training params: {best_params}")
        print(f"Best fitness (BPS): {best_fitness:.3f}")

        # Run full backtest to get all metrics
        best_model = self.model_class(**best_params)
        runner = BacktestRunner(config_path, logger=self.logger)
        train_result = runner.run(
            model=best_model,
            start_date=window.train_start,
            end_date=window.train_end
        )
        train_metrics = train_result['metrics']

        print(f"In-sample CAGR: {train_metrics['cagr']:.2%}")

        # Step 2: Test on validation period (out-of-sample)
        print(f"\nStep 2: Testing on validation period ({window.test_start} to {window.test_end})...")

        test_model = self.model_class(**best_params)
        test_result = runner.run(
            model=test_model,
            start_date=window.test_start,
            end_date=window.test_end
        )
        test_metrics = test_result['metrics']

        print(f"Out-of-sample CAGR: {test_metrics['cagr']:.2%}")
        print(f"Performance degradation: {train_metrics['cagr'] - test_metrics['cagr']:.2%}")

        return WalkForwardResult(
            window=window,
            best_params=best_params,
            train_metrics=train_metrics,
            test_metrics=test_metrics
        )

    def run(
        self,
        start_date: str,
        end_date: str,
        config_path: str,
        output_dir: str = "results/walk_forward"
    ) -> Dict[str, Any]:
        """Run full walk-forward optimization."""
        print(f"\n{'#'*80}")
        print(f"WALK-FORWARD OPTIMIZATION")
        print(f"{'#'*80}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Train window: {self.train_period_months} months")
        print(f"Test window: {self.test_period_months} months")
        print(f"Step size: {self.step_months} months")
        print(f"EA: {self.population_size} population, {self.generations} generations")

        # Generate windows
        windows = self.generate_windows(start_date, end_date)
        print(f"\nGenerated {len(windows)} walk-forward windows:")
        for window in windows:
            print(f"  {window}")

        # Optimize each window
        results = []
        for window in windows:
            result = self.optimize_window(window, config_path)
            results.append(result)

        # Aggregate out-of-sample performance
        avg_oos_cagr = np.mean([r.out_of_sample_cagr for r in results])
        avg_is_cagr = np.mean([r.in_sample_cagr for r in results])
        avg_degradation = avg_is_cagr - avg_oos_cagr

        # Check parameter stability
        param_stability = self._analyze_parameter_stability(results)

        print(f"\n{'='*80}")
        print(f"WALK-FORWARD RESULTS")
        print(f"{'='*80}")
        print(f"Average In-Sample CAGR:     {avg_is_cagr:.2%}")
        print(f"Average Out-of-Sample CAGR: {avg_oos_cagr:.2%}")
        print(f"Performance Degradation:    {avg_degradation:.2%}")
        print(f"\nParameter Stability (CV = std/mean, lower is better):")
        for param, stats in param_stability.items():
            print(f"  {param:20s}: mean={stats['mean']:7.2f}, std={stats['std']:7.2f}, cv={stats['cv']:6.1%}")

        # Save results
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_path / f"walk_forward_{timestamp}.json"

        output = {
            "methodology": {
                "train_period_months": self.train_period_months,
                "test_period_months": self.test_period_months,
                "step_months": self.step_months,
                "population_size": self.population_size,
                "generations": self.generations
            },
            "summary": {
                "num_windows": len(windows),
                "avg_in_sample_cagr": float(avg_is_cagr),
                "avg_out_of_sample_cagr": float(avg_oos_cagr),
                "performance_degradation": float(avg_degradation),
                "parameter_stability": {k: {kk: float(vv) for kk, vv in v.items()}
                                       for k, v in param_stability.items()}
            },
            "windows": [
                {
                    "window_id": r.window.window_id,
                    "train_period": f"{r.window.train_start} to {r.window.train_end}",
                    "test_period": f"{r.window.test_start} to {r.window.test_end}",
                    "best_params": r.best_params,
                    "in_sample_cagr": float(r.in_sample_cagr),
                    "out_of_sample_cagr": float(r.out_of_sample_cagr),
                    "degradation": float(r.performance_degradation()),
                    "train_metrics": {k: float(v) for k, v in r.train_metrics.items()},
                    "test_metrics": {k: float(v) for k, v in r.test_metrics.items()}
                }
                for r in results
            ]
        }

        with open(results_file, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\nResults saved to: {results_file}")

        return output

    def _analyze_parameter_stability(
        self,
        results: List[WalkForwardResult]
    ) -> Dict[str, Dict[str, float]]:
        """Analyze stability of parameters across windows."""
        param_values = {}
        for result in results:
            for param, value in result.best_params.items():
                if param not in param_values:
                    param_values[param] = []
                param_values[param].append(value)

        stability = {}
        for param, values in param_values.items():
            mean = np.mean(values)
            std = np.std(values)
            cv = std / mean if mean != 0 else 0

            stability[param] = {
                "mean": mean,
                "std": std,
                "cv": cv
            }

        return stability
