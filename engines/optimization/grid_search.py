"""
Grid Search and Random Search Optimizers

Explores parameter space using:
- Grid Search: Exhaustive evaluation of all parameter combinations
- Random Search: Random sampling from parameter distributions

Both methods:
1. Generate parameter sets from YAML experiment config
2. Run backtest for each parameter set
3. Rank results by Balanced Performance Score (BPS)
4. Store results for analysis and EA seeding
"""

import itertools
import random
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logging import StructuredLogger


class GridSearchOptimizer:
    """
    Exhaustive grid search over parameter space.
    
    Evaluates all combinations of parameters defined in experiment config.
    Best for small parameter spaces (< 1000 combinations).
    
    Example parameter grid:
        {
            'ma_period': [50, 100, 200],
            'momentum_period': [30, 60, 120],
            'rsi_period': [14, 21]
        }
        → 3 × 3 × 2 = 18 combinations
    """
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize grid search optimizer.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()
        
    def generate_parameter_sets(
        self,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations from grid.
        
        Args:
            param_grid: Dict mapping parameter name to list of values
            
        Returns:
            List of parameter dicts, one for each combination
            
        Example:
            >>> optimizer = GridSearchOptimizer()
            >>> grid = {'ma_period': [50, 100], 'rsi_period': [14, 21]}
            >>> param_sets = optimizer.generate_parameter_sets(grid)
            >>> len(param_sets)
            4
            >>> param_sets[0]
            {'ma_period': 50, 'rsi_period': 14}
        """
        if not param_grid:
            return [{}]
        
        # Get parameter names and their value lists
        param_names = list(param_grid.keys())
        param_values = [param_grid[name] for name in param_names]
        
        # Generate all combinations using itertools.product
        combinations = itertools.product(*param_values)
        
        # Convert to list of dicts
        parameter_sets = [
            dict(zip(param_names, combo))
            for combo in combinations
        ]
        
        self.logger.info(
            f"Generated {len(parameter_sets)} parameter combinations",
            extra={
                "num_combinations": len(parameter_sets),
                "parameters": param_names,
                "grid_size": {name: len(values) for name, values in param_grid.items()}
            }
        )
        
        return parameter_sets
    
    def estimate_runtime(
        self,
        param_grid: Dict[str, List[Any]],
        avg_backtest_time_seconds: float = 10.0
    ) -> Tuple[int, float]:
        """
        Estimate total runtime for grid search.
        
        Args:
            param_grid: Parameter grid
            avg_backtest_time_seconds: Average time per backtest (default: 10s)
            
        Returns:
            Tuple of (num_combinations, estimated_hours)
        """
        param_sets = self.generate_parameter_sets(param_grid)
        num_combinations = len(param_sets)
        total_seconds = num_combinations * avg_backtest_time_seconds
        total_hours = total_seconds / 3600
        
        return num_combinations, total_hours


class RandomSearchOptimizer:
    """
    Random search over parameter space.
    
    Samples random parameter combinations from defined distributions.
    More efficient than grid search for large parameter spaces.
    Good for initial exploration before EA refinement.
    
    Supports:
    - Discrete values: sample uniformly from list
    - Continuous ranges: uniform sampling from [min, max]
    - Log-scale ranges: for parameters spanning orders of magnitude
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize random search optimizer.
        
        Args:
            seed: Random seed for reproducibility
            logger: Optional logger instance
        """
        self.logger = logger or StructuredLogger()
        self.rng = random.Random(seed)
        
    def generate_parameter_sets(
        self,
        param_distributions: Dict[str, Dict[str, Any]],
        n_samples: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Generate random parameter samples from distributions.
        
        Args:
            param_distributions: Dict mapping parameter name to distribution spec
            n_samples: Number of random samples to generate
            
        Returns:
            List of parameter dicts
            
        Distribution spec formats:
            - Discrete: {'type': 'choice', 'values': [50, 100, 200]}
            - Continuous: {'type': 'uniform', 'min': 10, 'max': 100}
            - Log-scale: {'type': 'loguniform', 'min': 0.001, 'max': 1.0}
            - Integer: {'type': 'randint', 'min': 10, 'max': 100}
            
        Example:
            >>> optimizer = RandomSearchOptimizer(seed=42)
            >>> distributions = {
            ...     'ma_period': {'type': 'choice', 'values': [50, 100, 200]},
            ...     'rsi_threshold': {'type': 'uniform', 'min': 20, 'max': 40}
            ... }
            >>> param_sets = optimizer.generate_parameter_sets(distributions, n_samples=10)
            >>> len(param_sets)
            10
        """
        parameter_sets = []
        
        for _ in range(n_samples):
            param_set = {}
            
            for param_name, distribution in param_distributions.items():
                dist_type = distribution.get('type', 'choice')
                
                if dist_type == 'choice':
                    # Discrete choice from list
                    values = distribution['values']
                    param_set[param_name] = self.rng.choice(values)
                    
                elif dist_type == 'uniform':
                    # Continuous uniform distribution
                    min_val = distribution['min']
                    max_val = distribution['max']
                    param_set[param_name] = self.rng.uniform(min_val, max_val)
                    
                elif dist_type == 'loguniform':
                    # Log-uniform distribution (for parameters spanning orders of magnitude)
                    import math
                    min_val = distribution['min']
                    max_val = distribution['max']
                    log_min = math.log(min_val)
                    log_max = math.log(max_val)
                    param_set[param_name] = math.exp(self.rng.uniform(log_min, log_max))
                    
                elif dist_type == 'randint':
                    # Random integer in range [min, max]
                    min_val = distribution['min']
                    max_val = distribution['max']
                    param_set[param_name] = self.rng.randint(min_val, max_val)
                    
                else:
                    raise ValueError(f"Unknown distribution type: {dist_type}")
            
            parameter_sets.append(param_set)
        
        self.logger.info(
            f"Generated {n_samples} random parameter samples",
            extra={
                "num_samples": n_samples,
                "parameters": list(param_distributions.keys()),
                "distribution_types": {
                    name: dist.get('type', 'choice')
                    for name, dist in param_distributions.items()
                }
            }
        )
        
        return parameter_sets
    
    def estimate_coverage(
        self,
        param_distributions: Dict[str, Dict[str, Any]],
        n_samples: int
    ) -> Dict[str, float]:
        """
        Estimate parameter space coverage for discrete parameters.
        
        Args:
            param_distributions: Parameter distributions
            n_samples: Number of samples
            
        Returns:
            Dict mapping parameter name to coverage ratio (for discrete params)
        """
        coverage = {}
        
        for param_name, distribution in param_distributions.items():
            if distribution.get('type') == 'choice':
                num_values = len(distribution['values'])
                # Approximate coverage using probability theory
                # P(value not sampled) = (1 - 1/n)^k for k samples
                # Expected coverage ≈ 1 - (1 - 1/n)^k
                expected_coverage = 1 - (1 - 1/num_values) ** n_samples
                coverage[param_name] = expected_coverage
        
        return coverage


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Grid Search and Random Search Optimizer Test")
    print("=" * 80)
    
    # Test Grid Search
    print("\n1. Testing Grid Search")
    print("-" * 80)
    
    grid_optimizer = GridSearchOptimizer()
    
    param_grid = {
        'ma_period': [50, 100, 200],
        'momentum_period': [30, 60, 120],
        'rsi_period': [14, 21]
    }
    
    param_sets = grid_optimizer.generate_parameter_sets(param_grid)
    print(f"Parameter grid: {param_grid}")
    print(f"Generated {len(param_sets)} combinations")
    print("\nFirst 3 combinations:")
    for i, params in enumerate(param_sets[:3], 1):
        print(f"  {i}. {params}")
    
    # Estimate runtime
    num_combos, hours = grid_optimizer.estimate_runtime(param_grid, avg_backtest_time_seconds=10.0)
    print(f"\nEstimated runtime: {num_combos} backtests × 10s = {hours:.2f} hours")
    
    # Test Random Search
    print("\n\n2. Testing Random Search")
    print("-" * 80)
    
    random_optimizer = RandomSearchOptimizer(seed=42)
    
    param_distributions = {
        'ma_period': {'type': 'choice', 'values': [50, 100, 150, 200]},
        'rsi_threshold': {'type': 'uniform', 'min': 20.0, 'max': 40.0},
        'position_size': {'type': 'uniform', 'min': 0.1, 'max': 0.5},
        'stop_loss': {'type': 'loguniform', 'min': 0.01, 'max': 0.1}
    }
    
    random_param_sets = random_optimizer.generate_parameter_sets(param_distributions, n_samples=10)
    print(f"Parameter distributions: {list(param_distributions.keys())}")
    print(f"Generated {len(random_param_sets)} random samples")
    print("\nFirst 3 samples:")
    for i, params in enumerate(random_param_sets[:3], 1):
        print(f"  {i}. {params}")
    
    # Estimate coverage
    coverage = random_optimizer.estimate_coverage(param_distributions, n_samples=100)
    print(f"\nExpected coverage with 100 samples:")
    for param, cov in coverage.items():
        print(f"  {param}: {cov*100:.1f}%")
    
    print("\n" + "=" * 80)
    print("✓ Grid Search and Random Search tests complete")
