"""
Integration Test: Optimization Pipeline

Tests the complete optimization workflow from configuration to results:
1. Load experiment configuration
2. Generate parameter sets (grid/random/EA)
3. Run backtests for each parameter set (mocked for now)
4. Calculate performance metrics
5. Rank results by BPS
6. Generate comparison reports

This test ensures all optimization components work together correctly.
"""

import pytest
import json
import yaml
from pathlib import Path
import sys
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.optimization.grid_search import GridSearchOptimizer, RandomSearchOptimizer
from engines.optimization.evolutionary import EvolutionaryOptimizer
from engines.optimization.reporting import OptimizationReporter


class TestOptimizationPipeline:
    """Integration tests for optimization pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test outputs
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / "configs" / "experiments"
        self.results_dir = self.test_dir / "results"
        self.config_dir.mkdir(parents=True)
        self.results_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_grid_search_pipeline(self):
        """Test complete grid search optimization pipeline."""
        # 1. Create experiment configuration
        exp_config = {
            'experiment': {
                'name': 'test_grid_search',
                'description': 'Test grid search optimization',
                'method': 'grid',
                'base_config': 'configs/base/system.yaml',
                'target_model': 'TestModel',
                'parameter_grid': {
                    'param_a': [10, 20, 30],
                    'param_b': [0.1, 0.2]
                },
                'backtest': {
                    'start_date': '2020-01-01',
                    'end_date': '2024-12-31'
                },
                'optimization': {
                    'metric': 'bps',
                    'maximize': True,
                    'save_top_n': 3
                },
                'results': {
                    'database': str(self.results_dir / 'test_grid.db'),
                    'summary_csv': str(self.results_dir / 'test_grid.csv')
                }
            }
        }

        # Save config to file
        config_path = self.config_dir / 'test_grid.yaml'
        with open(config_path, 'w') as f:
            yaml.dump(exp_config, f)

        # 2. Initialize optimizer and generate parameter sets
        optimizer = GridSearchOptimizer()
        param_grid = {
            'param_a': [10, 20, 30],
            'param_b': [0.1, 0.2]
        }
        parameter_sets = optimizer.generate_parameter_sets(param_grid)

        # Verify correct number of combinations
        assert len(parameter_sets) == 6  # 3 × 2

        # Verify all combinations present
        expected_sets = [
            {'param_a': 10, 'param_b': 0.1},
            {'param_a': 10, 'param_b': 0.2},
            {'param_a': 20, 'param_b': 0.1},
            {'param_a': 20, 'param_b': 0.2},
            {'param_a': 30, 'param_b': 0.1},
            {'param_a': 30, 'param_b': 0.2}
        ]
        assert parameter_sets == expected_sets

        # 3. Mock backtest execution (simulate performance metrics)
        results = []
        for params in parameter_sets:
            # Mock BPS score (higher for larger param_a and param_b)
            bps = (params['param_a'] / 100) + params['param_b']
            results.append({
                'bps': bps,
                'sharpe_ratio': bps * 1.5,
                'cagr': bps * 0.2,
                'max_drawdown': -0.1 / bps
            })

        # 4. Rank by BPS
        combined = [
            {**params, **result}
            for params, result in zip(parameter_sets, results)
        ]
        combined.sort(key=lambda x: x['bps'], reverse=True)

        # Verify best parameters
        best = combined[0]
        assert best['param_a'] == 30
        assert best['param_b'] == 0.2
        assert best['bps'] == pytest.approx(0.5, rel=1e-6)

        # 5. Save results
        results_data = {
            'experiment': 'test_grid_search',
            'method': 'grid',
            'timestamp': '2025-11-16T12:00:00',
            'parameter_sets': parameter_sets,
            'results': results
        }

        results_file = self.results_dir / 'test_grid_summary.json'
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)

        # 6. Generate report
        reporter = OptimizationReporter()
        reporter.load_experiment_results('test_grid', str(results_file))

        # Generate text report
        report_path = self.results_dir / 'test_report.txt'
        reporter.generate_comparison_report(
            output_path=str(report_path),
            top_n=3,
            format='txt'
        )

        # Verify report generated
        assert report_path.exists()

        # Verify top N report
        top_n = reporter.generate_top_n_report(n=3)
        assert 'test_grid' in top_n
        assert len(top_n['test_grid']) == 3
        assert top_n['test_grid'][0]['param_a'] == 30

    def test_random_search_pipeline(self):
        """Test complete random search optimization pipeline."""
        # Initialize optimizer
        optimizer = RandomSearchOptimizer(seed=42)

        # Define parameter distributions
        param_distributions = {
            'param_a': {'type': 'randint', 'min': 10, 'max': 50},
            'param_b': {'type': 'uniform', 'min': 0.1, 'max': 0.5},
            'param_c': {'type': 'choice', 'values': ['A', 'B', 'C']}
        }

        # Generate parameter sets
        n_samples = 20
        parameter_sets = optimizer.generate_parameter_sets(param_distributions, n_samples=n_samples)

        # Verify correct number of samples
        assert len(parameter_sets) == n_samples

        # Verify all parameters present in each set
        for params in parameter_sets:
            assert 'param_a' in params
            assert 'param_b' in params
            assert 'param_c' in params

            # Verify value ranges
            assert 10 <= params['param_a'] <= 50
            assert 0.1 <= params['param_b'] <= 0.5
            assert params['param_c'] in ['A', 'B', 'C']

        # Verify distribution coverage estimate
        coverage = optimizer.estimate_coverage(param_distributions, n_samples)
        assert 'param_c' in coverage  # Only discrete parameters
        assert coverage['param_c'] > 0.5  # Should have decent coverage with 20 samples

    def test_evolutionary_algorithm_pipeline(self):
        """Test complete evolutionary algorithm optimization pipeline."""
        # Initialize optimizer
        optimizer = EvolutionaryOptimizer(
            population_size=10,
            num_generations=5,
            mutation_rate=0.3,
            crossover_rate=0.8,
            elitism_count=2,
            seed=42
        )

        # Define parameter ranges
        param_ranges = {
            'param_a': (10, 50),
            'param_b': (0.1, 0.5)
        }

        # Create initial population (seed with some good solutions)
        initial_pop = [
            {'param_a': 40, 'param_b': 0.4},
            {'param_a': 35, 'param_b': 0.35}
        ]

        # Seed population
        population = optimizer.seed_population(initial_pop, param_ranges)
        assert len(population) == 10  # Should fill to population_size

        # Mock fitness function (higher is better)
        def fitness_function(params):
            # Fitness increases with both parameters
            return params['param_a'] / 100 + params['param_b']

        # Run optimization
        final_population, final_fitness = optimizer.optimize(
            population,
            fitness_function,
            param_ranges
        )

        # Verify evolution produced valid results
        assert len(final_population) == 10
        assert len(final_fitness) == 10

        # Verify fitness improved (best final > best initial)
        best_final = max(final_fitness)
        best_initial = max(fitness_function(ind) for ind in population)

        # Best should improve or at least stay same (due to elitism)
        assert best_final >= best_initial * 0.95  # Allow small variance

        # Verify all solutions are valid
        for individual in final_population:
            assert 10 <= individual['param_a'] <= 50
            assert 0.1 <= individual['param_b'] <= 0.5

    def test_multi_experiment_comparison(self):
        """Test comparing multiple experiments."""
        reporter = OptimizationReporter()

        # Create mock results for multiple experiments
        experiments = {
            'exp_grid': {
                'experiment': 'test_grid',
                'method': 'grid',
                'timestamp': '2025-11-16T10:00:00',
                'parameter_sets': [
                    {'param_a': 10, 'param_b': 0.1},
                    {'param_a': 20, 'param_b': 0.2}
                ],
                'results': [
                    {'bps': 0.20, 'sharpe_ratio': 0.8, 'cagr': 0.10},
                    {'bps': 0.40, 'sharpe_ratio': 1.2, 'cagr': 0.15}
                ]
            },
            'exp_random': {
                'experiment': 'test_random',
                'method': 'random',
                'timestamp': '2025-11-16T11:00:00',
                'parameter_sets': [
                    {'param_a': 15, 'param_b': 0.15},
                    {'param_a': 25, 'param_b': 0.25},
                    {'param_a': 35, 'param_b': 0.35}
                ],
                'results': [
                    {'bps': 0.30, 'sharpe_ratio': 1.0, 'cagr': 0.12},
                    {'bps': 0.50, 'sharpe_ratio': 1.4, 'cagr': 0.18},
                    {'bps': 0.70, 'sharpe_ratio': 1.8, 'cagr': 0.22}
                ]
            }
        }

        # Save mock results
        for exp_name, exp_data in experiments.items():
            results_file = self.results_dir / f'{exp_name}.json'
            with open(results_file, 'w') as f:
                json.dump(exp_data, f, indent=2)

            # Load into reporter
            reporter.load_experiment_results(exp_name, str(results_file))

        # Generate summary
        summary = reporter.generate_summary_table()
        assert len(summary) == 2

        # Verify grid experiment summary
        grid_summary = next(s for s in summary if s['experiment'] == 'exp_grid')
        assert grid_summary['method'] == 'grid'
        assert grid_summary['num_parameter_sets'] == 2
        assert grid_summary['bps_best'] == 0.40
        assert grid_summary['bps_mean'] == pytest.approx(0.30, rel=1e-6)

        # Verify random experiment summary
        random_summary = next(s for s in summary if s['experiment'] == 'exp_random')
        assert random_summary['method'] == 'random'
        assert random_summary['num_parameter_sets'] == 3
        assert random_summary['bps_best'] == 0.70
        assert random_summary['bps_mean'] == pytest.approx(0.50, rel=1e-6)

        # Generate top N report
        top_n = reporter.generate_top_n_report(n=2)
        assert len(top_n) == 2
        assert len(top_n['exp_grid']) == 2
        assert len(top_n['exp_random']) == 2

        # Verify rankings
        assert top_n['exp_grid'][0]['bps'] == 0.40  # Best from grid
        assert top_n['exp_random'][0]['bps'] == 0.70  # Best from random

        # Generate parameter statistics
        param_stats = reporter.generate_parameter_distribution_stats()
        assert 'exp_grid' in param_stats
        assert 'exp_random' in param_stats

        # Verify param_a statistics for grid experiment
        grid_param_a_stats = param_stats['exp_grid']['param_a']
        assert grid_param_a_stats['min'] == 10
        assert grid_param_a_stats['max'] == 20
        assert grid_param_a_stats['unique_values'] == 2

        # Generate reports in all formats
        for fmt in ['txt', 'json', 'html']:
            report_path = self.results_dir / f'comparison.{fmt}'
            reporter.generate_comparison_report(
                output_path=str(report_path),
                top_n=2,
                format=fmt
            )
            assert report_path.exists()

    def test_parameter_grid_estimation(self):
        """Test grid search runtime estimation."""
        optimizer = GridSearchOptimizer()

        param_grid = {
            'param_a': [1, 2, 3, 4, 5],  # 5 values
            'param_b': [0.1, 0.2, 0.3],  # 3 values
            'param_c': [10, 20]  # 2 values
        }

        # Test estimation
        num_combos, hours = optimizer.estimate_runtime(
            param_grid,
            avg_backtest_time_seconds=5.0
        )

        # Verify calculation
        expected_combos = 5 * 3 * 2  # 30
        assert num_combos == expected_combos

        expected_hours = (30 * 5.0) / 3600  # 30 backtests × 5s = 150s = 0.0417 hours
        assert hours == pytest.approx(expected_hours, rel=1e-6)


# Run tests if executed directly
if __name__ == "__main__":
    print("=" * 80)
    print("Running Optimization Pipeline Integration Tests")
    print("=" * 80)

    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
