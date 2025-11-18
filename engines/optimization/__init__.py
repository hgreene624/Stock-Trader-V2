"""
Optimization Module

Parameter optimization for trading strategies using:
1. Grid Search - Exhaustive search over parameter grid
2. Random Search - Random sampling from parameter space
3. Evolutionary Algorithm - Genetic optimization using top performers

Workflow:
1. Define parameter grid in YAML experiment file
2. Run grid/random search to explore parameter space
3. Use EA to refine top performers
4. Rank results by Balanced Performance Score (BPS)
5. Store results in DuckDB for analysis
"""

from engines.optimization.grid_search import GridSearchOptimizer, RandomSearchOptimizer
from engines.optimization.evolutionary import EvolutionaryOptimizer

__all__ = [
    'GridSearchOptimizer',
    'RandomSearchOptimizer',
    'EvolutionaryOptimizer'
]
