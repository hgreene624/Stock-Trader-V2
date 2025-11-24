"""
Evolutionary Algorithm Optimizer

Genetic algorithm for parameter optimization using:
- Selection: Choose top performers based on BPS
- Crossover: Combine parameters from parent solutions
- Mutation: Random perturbations to explore nearby space
- Elitism: Preserve best solutions across generations

Workflow:
1. Seed initial population from grid/random search results
2. Evaluate fitness (BPS score) for each individual
3. Select parents based on fitness (tournament or roulette selection)
4. Create offspring via crossover and mutation
5. Replace population, preserving elite individuals
6. Repeat for N generations or until convergence
"""

import random
import copy
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path
import sys
from multiprocessing import Pool, cpu_count
import os
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.logging import StructuredLogger


class EvolutionaryOptimizer:
    """
    Evolutionary Algorithm for parameter optimization.
    
    Uses genetic algorithm to refine parameter sets based on
    backtest performance (Balanced Performance Score).
    
    Good for:
    - Refining top performers from grid/random search
    - Exploring local optima
    - Finding robust parameter sets through diversity
    """
    
    def __init__(
        self,
        population_size: int = 20,
        num_generations: int = 10,
        mutation_rate: float = 0.2,
        crossover_rate: float = 0.8,
        elitism_count: int = 2,
        tournament_size: int = 3,
        seed: Optional[int] = None,
        logger: Optional[StructuredLogger] = None,
        n_jobs: Optional[int] = None,
        mutation_strength: float = 0.1
    ):
        """
        Initialize evolutionary optimizer.

        Args:
            population_size: Number of individuals in population
            num_generations: Number of generations to evolve
            mutation_rate: Probability of mutation (0.0-1.0)
            crossover_rate: Probability of crossover (0.0-1.0)
            elitism_count: Number of top individuals to preserve
            tournament_size: Size of tournament for selection
            seed: Random seed for reproducibility
            logger: Optional logger instance
            n_jobs: Number of parallel processes (default: CPU cores - 1, or 1 if <= 2 cores)
            mutation_strength: Fraction of parameter range to use for Gaussian mutation noise
        """
        self.population_size = population_size
        self.num_generations = num_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = elitism_count
        self.tournament_size = tournament_size
        self.logger = logger or StructuredLogger()
        self.rng = random.Random(seed)
        self.mutation_strength = mutation_strength

        # Set n_jobs for parallelization
        if n_jobs is None:
            # Auto-detect: use all cores - 1, but at least 1
            total_cores = cpu_count()
            self.n_jobs = max(1, total_cores - 1) if total_cores > 2 else 1
        else:
            self.n_jobs = max(1, n_jobs)  # Ensure at least 1
        
    def seed_population(
        self,
        top_performers: List[Dict[str, Any]],
        param_ranges: Dict[str, Tuple[Any, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create initial population from top performers.
        
        Uses top performers from grid/random search as seed,
        then adds random individuals to fill population.
        
        Args:
            top_performers: List of parameter dicts (top K from grid/random search)
            param_ranges: Dict mapping parameter to (min, max) range
            
        Returns:
            List of parameter dicts (population)
        """
        population = []
        
        # Add top performers
        for individual in top_performers[:self.population_size]:
            population.append(copy.deepcopy(individual))
        
        # Fill remaining slots with random individuals
        while len(population) < self.population_size:
            individual = {}
            for param_name, (min_val, max_val) in param_ranges.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    individual[param_name] = self.rng.randint(min_val, max_val)
                else:
                    individual[param_name] = self.rng.uniform(min_val, max_val)
            population.append(individual)
        
        self.logger.info(
            f"Seeded population with {len(top_performers)} top performers",
            extra={
                "population_size": self.population_size,
                "num_seeds": min(len(top_performers), self.population_size),
                "num_random": self.population_size - min(len(top_performers), self.population_size)
            }
        )
        
        return population
    
    def tournament_selection(
        self,
        population: List[Dict[str, Any]],
        fitness_scores: List[float]
    ) -> Dict[str, Any]:
        """
        Select individual using tournament selection.
        
        Randomly selects K individuals and returns the best one.
        
        Args:
            population: List of parameter dicts
            fitness_scores: List of fitness values (BPS scores)
            
        Returns:
            Selected individual (parameter dict)
        """
        # Randomly select tournament participants
        tournament_indices = self.rng.sample(
            range(len(population)),
            min(self.tournament_size, len(population))
        )
        
        # Find best individual in tournament
        best_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
        
        return copy.deepcopy(population[best_idx])
    
    def crossover(
        self,
        parent1: Dict[str, Any],
        parent2: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Create two offspring from two parents via crossover.
        
        Uses uniform crossover: each parameter has 50% chance
        of coming from either parent.
        
        Args:
            parent1: First parent parameter dict
            parent2: Second parent parameter dict
            
        Returns:
            Tuple of (offspring1, offspring2)
        """
        if self.rng.random() > self.crossover_rate:
            # No crossover, return copies of parents
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        offspring1 = {}
        offspring2 = {}
        
        for param_name in parent1.keys():
            if self.rng.random() < 0.5:
                offspring1[param_name] = parent1[param_name]
                offspring2[param_name] = parent2[param_name]
            else:
                offspring1[param_name] = parent2[param_name]
                offspring2[param_name] = parent1[param_name]
        
        return offspring1, offspring2
    
    def mutate(
        self,
        individual: Dict[str, Any],
        param_ranges: Dict[str, Tuple[Any, Any]],
        mutation_strength: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Apply mutation to individual.
        
        For each parameter, with probability mutation_rate:
        - Continuous: Add Gaussian noise
        - Discrete: Randomly change to nearby value
        
        Args:
            individual: Parameter dict
            param_ranges: Dict mapping parameter to (min, max) range
            mutation_strength: Strength of mutation (0.0-1.0)
            
        Returns:
            Mutated individual
        """
        mutated = copy.deepcopy(individual)
        
        strength = mutation_strength if mutation_strength is not None else self.mutation_strength

        for param_name, value in mutated.items():
            if self.rng.random() < self.mutation_rate:
                min_val, max_val = param_ranges[param_name]
                
                if isinstance(value, int):
                    # Integer parameter: add random offset
                    param_range = max_val - min_val
                    offset = int(self.rng.gauss(0, param_range * strength))
                    mutated[param_name] = max(min_val, min(max_val, value + offset))
                    
                elif isinstance(value, float):
                    # Float parameter: add Gaussian noise
                    param_range = max_val - min_val
                    noise = self.rng.gauss(0, param_range * strength)
                    mutated[param_name] = max(min_val, min(max_val, value + noise))
        
        return mutated
    
    def evolve_generation(
        self,
        population: List[Dict[str, Any]],
        fitness_scores: List[float],
        param_ranges: Dict[str, Tuple[Any, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evolve population for one generation.
        
        Steps:
        1. Preserve elite individuals
        2. Select parents via tournament selection
        3. Create offspring via crossover
        4. Apply mutation to offspring
        5. Form new population
        
        Args:
            population: Current population
            fitness_scores: Fitness score for each individual
            param_ranges: Parameter ranges for mutation
            
        Returns:
            New population
        """
        # Sort population by fitness (descending)
        sorted_indices = sorted(
            range(len(population)),
            key=lambda i: fitness_scores[i],
            reverse=True
        )
        
        # Elitism: preserve top individuals
        new_population = [
            copy.deepcopy(population[i])
            for i in sorted_indices[:self.elitism_count]
        ]
        
        # Generate offspring to fill population
        while len(new_population) < self.population_size:
            # Select parents
            parent1 = self.tournament_selection(population, fitness_scores)
            parent2 = self.tournament_selection(population, fitness_scores)
            
            # Crossover
            offspring1, offspring2 = self.crossover(parent1, parent2)
            
            # Mutation
            offspring1 = self.mutate(offspring1, param_ranges)
            offspring2 = self.mutate(offspring2, param_ranges)
            
            # Add to new population
            new_population.append(offspring1)
            if len(new_population) < self.population_size:
                new_population.append(offspring2)
        
        return new_population
    
    def optimize(
        self,
        initial_population: List[Dict[str, Any]],
        fitness_function: Callable[[Dict[str, Any]], float],
        param_ranges: Dict[str, Tuple[Any, Any]],
        output_dir: str = None
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Run full evolutionary optimization.

        Args:
            initial_population: Starting population (seeded from grid search)
            fitness_function: Function that evaluates parameter dict → BPS score
            param_ranges: Parameter ranges for mutation
            output_dir: Directory for incremental generation logs (optional)

        Returns:
            Tuple of (final_population, fitness_scores)
        """
        import time
        import json
        from datetime import datetime
        from pathlib import Path

        population = initial_population

        # Set up incremental logging
        generation_log_path = None
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            generation_log_path = output_path / "generation_log.jsonl"

            # Write initial metadata
            with open(generation_log_path, 'w') as f:
                metadata = {
                    "type": "metadata",
                    "timestamp": datetime.now().isoformat(),
                    "seed": self.seed,
                    "population_size": self.population_size,
                    "num_generations": self.num_generations,
                    "mutation_rate": self.mutation_rate,
                    "crossover_rate": self.crossover_rate,
                    "elitism_count": self.elitism_count,
                    "param_ranges": {k: list(v) for k, v in param_ranges.items()}
                }
                f.write(json.dumps(metadata) + "\n")

        # Track progress
        total_backtests = self.num_generations * self.population_size
        completed_backtests = 0
        start_time = time.time()

        print(f"\n{'='*80}", flush=True)
        print(f"EVOLUTIONARY OPTIMIZATION - PROGRESS TRACKING", flush=True)
        print(f"{'='*80}", flush=True)
        print(f"Total backtests to run: {total_backtests}", flush=True)
        print(f"Population size: {self.population_size}", flush=True)
        print(f"Generations: {self.num_generations}", flush=True)
        print(f"Parallel processes: {self.n_jobs}", flush=True)
        if self.n_jobs > 1:
            print(f"⚡ PARALLEL MODE: Using {self.n_jobs} cores (~{self.n_jobs}x speedup)", flush=True)
        print(f"{'='*80}\n", flush=True)

        self.logger.info(
            f"Starting evolutionary optimization",
            extra={
                "population_size": len(population),
                "num_generations": self.num_generations,
                "mutation_rate": self.mutation_rate,
                "crossover_rate": self.crossover_rate,
                "elitism_count": self.elitism_count,
                "mutation_strength": self.mutation_strength
            }
        )

        for generation in range(self.num_generations):
            gen_start_time = time.time()

            # Evaluate fitness for entire population
            if self.n_jobs > 1:
                # PARALLEL MODE: Use multiprocessing
                with Pool(processes=self.n_jobs) as pool:
                    fitness_scores = pool.map(fitness_function, population)

                # Update progress counter
                completed_backtests += self.population_size
                progress_pct = (completed_backtests / total_backtests) * 100
                elapsed_time = time.time() - start_time
                avg_time_per_backtest = elapsed_time / completed_backtests
                remaining_backtests = total_backtests - completed_backtests
                estimated_time_remaining = avg_time_per_backtest * remaining_backtests

                # Print generation progress (parallel mode shows summary after all complete)
                best_in_gen = max(fitness_scores)
                avg_in_gen = sum(fitness_scores) / len(fitness_scores)
                print(f"  Gen {generation+1}/{self.num_generations} | "
                      f"Completed: {self.population_size} individuals | "
                      f"Progress: {progress_pct:.1f}% | "
                      f"Est. remaining: {estimated_time_remaining/60:.1f} min | "
                      f"Best BPS: {best_in_gen:.3f} | Avg BPS: {avg_in_gen:.3f}", flush=True)
            else:
                # SEQUENTIAL MODE: Original behavior with per-individual progress
                fitness_scores = []
                for i, individual in enumerate(population):
                    # Run backtest
                    fitness = fitness_function(individual)
                    fitness_scores.append(fitness)

                    # Update progress
                    completed_backtests += 1
                    progress_pct = (completed_backtests / total_backtests) * 100

                    # Calculate time estimates
                    elapsed_time = time.time() - start_time
                    avg_time_per_backtest = elapsed_time / completed_backtests
                    remaining_backtests = total_backtests - completed_backtests
                    estimated_time_remaining = avg_time_per_backtest * remaining_backtests

                    # Print progress every backtest
                    print(f"  Gen {generation+1}/{self.num_generations} | "
                          f"Individual {i+1}/{self.population_size} | "
                          f"Progress: {progress_pct:.1f}% | "
                          f"Est. remaining: {estimated_time_remaining/60:.1f} min | "
                          f"BPS: {fitness:.3f}", flush=True)

            # Print generation summary
            gen_time = time.time() - gen_start_time
            
            # Get statistics
            best_fitness = max(fitness_scores)
            avg_fitness = sum(fitness_scores) / len(fitness_scores)
            
            # Print generation summary
            print(f"\n{'─'*80}", flush=True)
            print(f"GENERATION {generation+1}/{self.num_generations} COMPLETE", flush=True)
            print(f"{'─'*80}", flush=True)
            print(f"  Time: {gen_time:.1f}s", flush=True)
            print(f"  Best BPS: {best_fitness:.4f}", flush=True)
            print(f"  Avg BPS: {avg_fitness:.4f}", flush=True)
            print(f"  Overall Progress: {progress_pct:.1f}%", flush=True)
            elapsed_min = (time.time() - start_time) / 60
            remaining_min = estimated_time_remaining / 60
            print(f"  Elapsed: {elapsed_min:.1f} min | Remaining: {remaining_min:.1f} min", flush=True)
            print(f"{'─'*80}\n", flush=True)

            self.logger.info(
                f"Generation {generation + 1}/{self.num_generations}",
                extra={
                    "generation": generation + 1,
                    "best_fitness": round(best_fitness, 4),
                    "avg_fitness": round(avg_fitness, 4),
                    "fitness_std": round(_std(fitness_scores), 4)
                }
            )

            # Incremental generation logging
            if generation_log_path:
                # Get top 5 individuals for this generation
                sorted_indices = sorted(range(len(population)), key=lambda i: fitness_scores[i], reverse=True)
                top_5 = []
                for idx in sorted_indices[:5]:
                    top_5.append({
                        "params": population[idx],
                        "fitness": round(fitness_scores[idx], 4)
                    })

                gen_data = {
                    "type": "generation",
                    "timestamp": datetime.now().isoformat(),
                    "generation": generation + 1,
                    "best_fitness": round(best_fitness, 4),
                    "avg_fitness": round(avg_fitness, 4),
                    "fitness_std": round(_std(fitness_scores), 4),
                    "gen_time_seconds": round(gen_time, 1),
                    "top_5": top_5
                }
                with open(generation_log_path, 'a') as f:
                    f.write(json.dumps(gen_data) + "\n")

            # Evolve to next generation
            if generation < self.num_generations - 1:
                population = self.evolve_generation(population, fitness_scores, param_ranges)
        
        # Final evaluation
        final_fitness_scores = [fitness_function(individual) for individual in population]
        
        self.logger.info(
            "Evolutionary optimization complete",
            extra={
                "best_final_fitness": round(max(final_fitness_scores), 4),
                "improvement": round(max(final_fitness_scores) - max([fitness_function(ind) for ind in initial_population[:len(population)]]), 4)
            }
        )
        
        return population, final_fitness_scores


def _std(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Evolutionary Algorithm Optimizer Test")
    print("=" * 80)
    
    # Mock fitness function (higher is better)
    def mock_fitness(params: Dict[str, Any]) -> float:
        """Mock fitness function for testing."""
        # Optimal parameters: ma_period=100, rsi_period=20
        ma_error = abs(params['ma_period'] - 100) / 100
        rsi_error = abs(params['rsi_period'] - 20) / 20
        return 1.0 - (ma_error + rsi_error) / 2
    
    # Define parameter ranges
    param_ranges = {
        'ma_period': (50, 200),
        'rsi_period': (10, 30)
    }
    
    # Create initial population (random)
    ea_optimizer = EvolutionaryOptimizer(
        population_size=10,
        num_generations=5,
        mutation_rate=0.3,
        crossover_rate=0.8,
        elitism_count=2,
        seed=42
    )
    
    initial_population = []
    rng = random.Random(42)
    for _ in range(10):
        individual = {
            'ma_period': rng.randint(50, 200),
            'rsi_period': rng.randint(10, 30)
        }
        initial_population.append(individual)
    
    print("Initial population (random):")
    for i, ind in enumerate(initial_population, 1):
        fitness = mock_fitness(ind)
        print(f"  {i}. {ind} → fitness={fitness:.3f}", flush=True)
    
    # Run optimization
    print("\nRunning evolutionary optimization...")
    final_population, final_fitness = ea_optimizer.optimize(
        initial_population,
        mock_fitness,
        param_ranges
    )
    
    # Show results
    print("\nFinal population:")
    sorted_indices = sorted(range(len(final_population)), key=lambda i: final_fitness[i], reverse=True)
    for i, idx in enumerate(sorted_indices, 1):
        print(f"  {i}. {final_population[idx]} → fitness={final_fitness[idx]:.3f}", flush=True)
    
    best_params = final_population[sorted_indices[0]]
    print(f"\nBest solution: {best_params}", flush=True)
    print(f"Fitness: {final_fitness[sorted_indices[0]]:.3f}", flush=True)
    print(f"Expected optimum: {{'ma_period': 100, 'rsi_period': 20}}", flush=True)
    
    print("\n" + "=" * 80)
    print("✓ Evolutionary Algorithm test complete")
