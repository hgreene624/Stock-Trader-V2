"""
Optimization CLI

Command-line interface for running parameter optimization experiments.

Usage:
    # Run a single experiment
    python -m engines.optimization.cli run --experiment configs/experiments/exp_001.yaml

    # List all experiments
    python -m engines.optimization.cli list

    # Compare experiment results
    python -m engines.optimization.cli compare exp_001 exp_002 exp_003

    # Resume interrupted experiment
    python -m engines.optimization.cli resume --experiment exp_001

Workflow:
1. Load experiment configuration from YAML
2. Initialize optimizer based on method (grid/random/evolutionary)
3. Run backtests for each parameter set
4. Rank results by optimization metric (BPS)
5. Save results to database and CSV
6. Generate summary report
"""

import argparse
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from engines.optimization.grid_search import GridSearchOptimizer, RandomSearchOptimizer
from engines.optimization.evolutionary import EvolutionaryOptimizer
from utils.logging import StructuredLogger
from backtest.runner import BacktestRunner
from models.sector_rotation_v1 import SectorRotationModel_v1
from models.equity_trend_v1 import EquityTrendModel_v1
from models.equity_trend_v1_daily import EquityTrendModel_v1_Daily
from models.equity_trend_v2_daily import EquityTrendModel_v2_Daily


class OptimizationCLI:
    """
    Command-line interface for optimization experiments.

    Manages experiment execution, result storage, and comparison.
    """

    def __init__(self):
        """Initialize optimization CLI."""
        self.logger = StructuredLogger()

    def load_experiment_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load and validate experiment configuration from YAML.

        Args:
            config_path: Path to experiment YAML file

        Returns:
            Experiment configuration dict

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Experiment config not found: {config_path}")

        with open(config_file) as f:
            config = yaml.safe_load(f)

        if 'experiment' not in config:
            raise ValueError("Config must contain 'experiment' section")

        exp_config = config['experiment']

        # Validate required fields
        required = ['name', 'method', 'base_config', 'target_model', 'backtest', 'optimization', 'results']
        for field in required:
            if field not in exp_config:
                raise ValueError(f"Missing required field: {field}")

        # Validate method-specific requirements
        method = exp_config['method']

        if method == 'grid' and 'parameter_grid' not in exp_config:
            raise ValueError("Grid search requires 'parameter_grid'")

        if method == 'random':
            if 'parameter_distributions' not in exp_config:
                raise ValueError("Random search requires 'parameter_distributions'")
            if 'random_search' not in exp_config:
                raise ValueError("Random search requires 'random_search' settings")

        if method == 'evolutionary':
            if 'parameter_ranges' not in exp_config:
                raise ValueError("Evolutionary search requires 'parameter_ranges'")
            if 'evolutionary' not in exp_config:
                raise ValueError("Evolutionary search requires 'evolutionary' settings")

        return exp_config

    def run_grid_search(self, exp_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run grid search optimization.

        Args:
            exp_config: Experiment configuration

        Returns:
            List of parameter sets to evaluate
        """
        print("\n" + "=" * 80)
        print(f"GRID SEARCH: {exp_config['name']}")
        print("=" * 80)
        print(f"Description: {exp_config['description']}")
        print()

        # Initialize grid search optimizer
        optimizer = GridSearchOptimizer(logger=self.logger)

        # Extract parameter grid
        param_grid = exp_config['parameter_grid']

        # Convert dot notation to simple parameter names
        # Example: "models.EquityTrendModel_v1.parameters.slow_ma_period" → "slow_ma_period"
        simple_grid = {}
        for param_path, values in param_grid.items():
            param_name = param_path.split('.')[-1]
            simple_grid[param_name] = values

        # Generate parameter sets
        parameter_sets = optimizer.generate_parameter_sets(simple_grid)

        print(f"Parameter grid:")
        for param, values in simple_grid.items():
            print(f"  {param}: {values}")

        print(f"\nTotal combinations: {len(parameter_sets)}")

        # Estimate runtime (assuming 10 seconds per backtest)
        num_combos, hours = optimizer.estimate_runtime(simple_grid, avg_backtest_time_seconds=10.0)
        print(f"Estimated runtime: {hours:.2f} hours ({num_combos} backtests × 10s)")

        return parameter_sets

    def run_random_search(self, exp_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run random search optimization.

        Args:
            exp_config: Experiment configuration

        Returns:
            List of parameter sets to evaluate
        """
        print("\n" + "=" * 80)
        print(f"RANDOM SEARCH: {exp_config['name']}")
        print("=" * 80)
        print(f"Description: {exp_config['description']}")
        print()

        # Initialize random search optimizer
        random_config = exp_config['random_search']
        optimizer = RandomSearchOptimizer(
            seed=random_config.get('seed'),
            logger=self.logger
        )

        # Extract parameter distributions
        param_distributions = exp_config['parameter_distributions']

        # Convert dot notation to simple parameter names
        simple_distributions = {}
        for param_path, dist_spec in param_distributions.items():
            param_name = param_path.split('.')[-1]
            simple_distributions[param_name] = dist_spec

        # Generate parameter sets
        n_samples = random_config['n_samples']
        parameter_sets = optimizer.generate_parameter_sets(simple_distributions, n_samples=n_samples)

        print(f"Parameter distributions:")
        for param, dist in simple_distributions.items():
            print(f"  {param}: {dist}")

        print(f"\nSamples: {n_samples}")
        print(f"Seed: {random_config.get('seed', 'None')}")

        # Estimate coverage
        if random_config.get('estimate_coverage'):
            coverage = optimizer.estimate_coverage(simple_distributions, n_samples)
            print(f"\nExpected coverage (discrete parameters):")
            for param, cov in coverage.items():
                print(f"  {param}: {cov*100:.1f}%")

        return parameter_sets

    def create_backtest_fitness_function(self, exp_config: Dict[str, Any]):
        """
        Create a fitness function that runs actual backtests.

        Args:
            exp_config: Experiment configuration

        Returns:
            Fitness function that takes parameters and returns BPS score
        """
        base_config = exp_config['base_config']
        target_model = exp_config['target_model']
        backtest_config = exp_config['backtest']
        opt_config = exp_config['optimization']

        # Initialize backtest runner
        runner = BacktestRunner(base_config, logger=self.logger)

        def fitness_function(params: Dict[str, Any]) -> float:
            """Run backtest and return fitness score."""
            try:
                # Instantiate model with parameters
                if target_model == "SectorRotationModel_v1":
                    model = SectorRotationModel_v1(**params)
                elif target_model == "EquityTrendModel_v1":
                    model = EquityTrendModel_v1(**params)
                elif target_model == "EquityTrendModel_v1_Daily":
                    model = EquityTrendModel_v1_Daily(**params)
                elif target_model == "EquityTrendModel_v2_Daily":
                    model = EquityTrendModel_v2_Daily(**params)
                else:
                    raise ValueError(f"Unknown model: {target_model}")

                # Run backtest
                results = runner.run(
                    model=model,
                    start_date=backtest_config['start_date'],
                    end_date=backtest_config['end_date']
                )

                # Extract fitness metric (default: BPS)
                metric = opt_config.get('metric', 'bps')
                fitness = results['metrics'].get(metric, 0.0)

                return fitness

            except Exception as e:
                # If backtest fails, return very low fitness
                print(f"  ⚠️  Backtest failed for {params}: {e}")
                return -999.0

        return fitness_function

    def run_evolutionary(self, exp_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run evolutionary algorithm optimization.

        Args:
            exp_config: Experiment configuration

        Returns:
            List of final population parameter sets
        """
        print("\n" + "=" * 80)
        print(f"EVOLUTIONARY ALGORITHM: {exp_config['name']}")
        print("=" * 80)
        print(f"Description: {exp_config['description']}")
        print()

        # Initialize EA optimizer
        ea_config = exp_config['evolutionary']
        optimizer = EvolutionaryOptimizer(
            population_size=ea_config['population_size'],
            num_generations=ea_config['num_generations'],
            mutation_rate=ea_config['mutation_rate'],
            crossover_rate=ea_config['crossover_rate'],
            elitism_count=ea_config['elitism_count'],
            tournament_size=ea_config.get('tournament_size', 3),
            seed=ea_config.get('seed'),
            logger=self.logger
        )

        # Extract parameter ranges
        param_ranges = exp_config['parameter_ranges']

        # Convert dot notation to simple parameter names
        simple_ranges = {}
        for param_path, range_spec in param_ranges.items():
            param_name = param_path.split('.')[-1]
            simple_ranges[param_name] = (range_spec['min'], range_spec['max'])

        print(f"Parameter ranges:")
        for param, (min_val, max_val) in simple_ranges.items():
            print(f"  {param}: [{min_val}, {max_val}]")

        print(f"\nEvolutionary settings:")
        print(f"  Population size: {ea_config['population_size']}")
        print(f"  Generations: {ea_config['num_generations']}")
        print(f"  Mutation rate: {ea_config['mutation_rate']}")
        print(f"  Crossover rate: {ea_config['crossover_rate']}")
        print(f"  Elitism: {ea_config['elitism_count']}")
        print(f"  Seed: {ea_config.get('seed', 'None')}")

        # Seed initial population
        # TODO: Support seeding from previous experiment results
        # For now, use provided initial_population or random
        if 'initial_population' in ea_config:
            initial_pop = ea_config['initial_population'][:ea_config['population_size']]
        else:
            initial_pop = []

        initial_population = optimizer.seed_population(initial_pop, simple_ranges)

        print(f"\nInitial population: {len(initial_population)} individuals")

        # Create real fitness function that runs backtests
        print("\nCreating backtest fitness function...")
        fitness_function = self.create_backtest_fitness_function(exp_config)

        # Run optimization
        print("\nRunning evolutionary optimization with REAL backtests...")
        print(f"This will run ~{ea_config['population_size'] * ea_config['num_generations']} backtests.")
        print("(This may take a while...)\n")

        final_population, final_fitness = optimizer.optimize(
            initial_population,
            fitness_function,
            simple_ranges
        )

        # Sort by fitness
        sorted_indices = sorted(range(len(final_population)), key=lambda i: final_fitness[i], reverse=True)

        print("\nTop 5 solutions:")
        for i, idx in enumerate(sorted_indices[:5], 1):
            print(f"  {i}. {final_population[idx]} → fitness={final_fitness[idx]:.4f}")

        return final_population

    def save_results(
        self,
        exp_config: Dict[str, Any],
        parameter_sets: List[Dict[str, Any]],
        results: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Save experiment results to database and CSV.

        Args:
            exp_config: Experiment configuration
            parameter_sets: List of parameter sets evaluated
            results: Optional list of backtest results
        """
        results_config = exp_config['results']

        # Create results directory
        results_dir = Path(results_config['database']).parent
        results_dir.mkdir(parents=True, exist_ok=True)

        # Save parameter sets to CSV
        csv_path = Path(results_config['summary_csv'])
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"\nSaving results:")
        print(f"  Database: {results_config['database']} (TODO: implement DuckDB storage)")
        print(f"  Summary CSV: {results_config['summary_csv']}")

        # Save parameter sets as JSON for now (CSV would require pandas)
        json_path = csv_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump({
                'experiment': exp_config['name'],
                'method': exp_config['method'],
                'timestamp': datetime.now().isoformat(),
                'parameter_sets': parameter_sets,
                'results': results or []
            }, f, indent=2)

        print(f"  Parameter sets saved to: {json_path}")
        print("\n✓ Results saved successfully")

    def run_experiment(self, config_path: str):
        """
        Run optimization experiment from configuration file.

        Args:
            config_path: Path to experiment YAML configuration
        """
        try:
            # Load configuration
            exp_config = self.load_experiment_config(config_path)

            # Run optimization based on method
            method = exp_config['method']

            if method == 'grid':
                parameter_sets = self.run_grid_search(exp_config)
            elif method == 'random':
                parameter_sets = self.run_random_search(exp_config)
            elif method == 'evolutionary':
                parameter_sets = self.run_evolutionary(exp_config)
            else:
                raise ValueError(f"Unknown optimization method: {method}")

            # TODO: Run backtests for each parameter set
            # This requires backtest engine integration (Phase 2)
            print("\n" + "=" * 80)
            print("BACKTEST EXECUTION")
            print("=" * 80)
            print("[Not yet implemented - requires backtest engine from Phase 2]")
            print()
            print("Next steps:")
            print("  1. Integrate with backtest engine")
            print("  2. Execute backtest for each parameter set")
            print("  3. Calculate performance metrics (BPS, Sharpe, CAGR, etc.)")
            print("  4. Rank results by optimization metric")
            print("  5. Save to DuckDB database")

            # Save results
            self.save_results(exp_config, parameter_sets)

            print("\n" + "=" * 80)
            print("EXPERIMENT COMPLETE")
            print("=" * 80)

        except Exception as e:
            self.logger.error(f"Experiment failed: {e}")
            raise

    def list_experiments(self):
        """List all available experiment configurations."""
        print("\n" + "=" * 80)
        print("AVAILABLE EXPERIMENTS")
        print("=" * 80)

        # Find all experiment configs
        exp_dir = Path("configs/experiments")
        if not exp_dir.exists():
            print("No experiments directory found")
            return

        exp_files = sorted(exp_dir.glob("*.yaml"))

        if not exp_files:
            print("No experiment configurations found")
            return

        print(f"\nFound {len(exp_files)} experiments:\n")

        for exp_file in exp_files:
            try:
                exp_config = self.load_experiment_config(str(exp_file))
                print(f"  {exp_file.stem}")
                print(f"    Name: {exp_config['name']}")
                print(f"    Method: {exp_config['method']}")
                print(f"    Model: {exp_config['target_model']}")
                print(f"    Description: {exp_config['description']}")
                print()
            except Exception as e:
                print(f"  {exp_file.stem} [ERROR: {e}]")
                print()

    def compare_experiments(self, experiment_names: List[str]):
        """
        Compare results from multiple experiments.

        Args:
            experiment_names: List of experiment names to compare
        """
        print("\n" + "=" * 80)
        print("EXPERIMENT COMPARISON")
        print("=" * 80)
        print(f"Comparing: {', '.join(experiment_names)}")
        print()

        # TODO: Load results from database and generate comparison
        print("[Not yet implemented - requires results database]")
        print()
        print("Planned comparison metrics:")
        print("  - Best BPS score per experiment")
        print("  - Best Sharpe ratio per experiment")
        print("  - Runtime comparison")
        print("  - Parameter space coverage")
        print("  - Top 5 parameter sets side-by-side")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Optimization CLI - Run parameter optimization experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run a single experiment
  python -m engines.optimization.cli run --experiment configs/experiments/exp_001_equity_trend_grid.yaml

  # List all experiments
  python -m engines.optimization.cli list

  # Compare experiment results
  python -m engines.optimization.cli compare exp_001 exp_002 exp_003
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run optimization experiment')
    run_parser.add_argument(
        '--experiment',
        required=True,
        help='Path to experiment YAML configuration'
    )

    # List command
    list_parser = subparsers.add_parser('list', help='List all experiments')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare experiment results')
    compare_parser.add_argument(
        'experiments',
        nargs='+',
        help='Experiment names to compare (e.g., exp_001 exp_002)'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize CLI
    cli = OptimizationCLI()

    # Execute command
    if args.command == 'run':
        cli.run_experiment(args.experiment)
    elif args.command == 'list':
        cli.list_experiments()
    elif args.command == 'compare':
        cli.compare_experiments(args.experiments)


if __name__ == "__main__":
    main()
