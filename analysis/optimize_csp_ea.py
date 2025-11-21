"""
Evolutionary Algorithm Optimization for Cash-Secured Put Model.

Uses genetic algorithm to find optimal parameters:
- Delta: 0.15 - 0.45 (continuous)
- Min DTE: 14 - 50 (integer)
- Max DTE: min_dte + 10 to 60 (integer)
- Exit %: 0.10 - 0.90 (continuous)

Population: 20
Generations: 30
Mutation rate: 0.2
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from decimal import Decimal
from datetime import datetime, timezone
from models.cash_secured_put_v1 import CashSecuredPutModel_v1
from models.base import Context, RegimeState
import json

def load_spy_data(path: str = "data/equities/SPY_1D.parquet") -> pd.DataFrame:
    """Load SPY data."""
    return pd.read_parquet(path)

def simulate_csp_strategy(
    spy_data: pd.DataFrame,
    target_delta: float,
    min_dte: int,
    max_dte: int,
    profit_target_pct: float,
    initial_capital: float = 100000.0
) -> dict:
    """Simulate CSP strategy and return metrics."""
    # Initialize model
    model = CashSecuredPutModel_v1(
        target_delta=target_delta,
        min_dte=min_dte,
        max_dte=max_dte,
        profit_target_pct=profit_target_pct
    )

    # Simulate trades
    capital = initial_capital
    equity_curve = [capital]
    trades = []

    # Average holding period
    avg_holding_period = (min_dte + max_dte) // 2

    # Test points
    test_dates = spy_data.index[::avg_holding_period]

    for test_date in test_dates:
        if test_date not in spy_data.index:
            continue

        historical = spy_data.loc[:test_date]

        if len(historical) < 200:
            continue

        # Determine regime
        ma_200 = historical['close'].tail(200).mean()
        price = historical['close'].iloc[-1]
        regime = "bull" if price > ma_200 else "bear"

        # Create context
        regime_state = RegimeState(
            timestamp=test_date,
            equity_regime=regime,
            vol_regime="normal",
            crypto_regime="neutral",
            macro_regime="expansion"
        )

        context = Context(
            timestamp=test_date,
            asset_features={"SPY": historical},
            regime=regime_state,
            model_budget_fraction=1.0,
            model_budget_value=Decimal(str(capital)),
            current_exposures={}
        )

        # Check if model would enter
        should_enter = model._should_enter_position(context, historical, regime)

        if should_enter:
            # Estimate premium based on delta
            if target_delta <= 0.25:
                premium_pct = 0.015
            elif target_delta <= 0.35:
                premium_pct = 0.025
            else:
                premium_pct = 0.035

            # Realized premium
            realized_premium_pct = premium_pct * profit_target_pct

            # Assignment
            assignment_prob = target_delta
            assigned = np.random.random() < assignment_prob

            if assigned:
                future_idx = min(len(spy_data) - 1, spy_data.index.get_loc(test_date) + 5)
                future_price = spy_data['close'].iloc[future_idx]
                stock_return = (future_price - price) / price
                trade_return = realized_premium_pct + max(stock_return, -0.05)
            else:
                trade_return = realized_premium_pct

            capital *= (1 + trade_return)
            equity_curve.append(capital)

            trades.append({
                'date': test_date,
                'return': trade_return,
                'capital': capital
            })

    # Calculate metrics
    if len(trades) == 0:
        return {'bps': -999.0, 'sharpe': 0.0, 'cagr': 0.0, 'max_dd': 0.0, 'win_rate': 0.0, 'total_trades': 0}

    trades_df = pd.DataFrame(trades)
    returns = trades_df['return'].values

    mean_return = returns.mean()
    std_return = returns.std()
    sharpe = (mean_return / std_return) * np.sqrt(252 / avg_holding_period) if std_return > 0 else 0

    days = (spy_data.index[-1] - spy_data.index[0]).days
    years = days / 365
    cagr = (capital / initial_capital) ** (1 / years) - 1 if years > 0 else 0

    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.expanding().max()
    drawdowns = (equity_series - rolling_max) / rolling_max
    max_dd = drawdowns.min()

    win_rate = (returns > 0).mean()

    # BPS (Balanced Performance Score)
    bps = 0.4 * sharpe + 0.3 * (cagr * 10) + 0.2 * win_rate - 0.1 * abs(max_dd)

    return {
        'bps': float(bps),
        'sharpe': float(sharpe),
        'cagr': float(cagr),
        'max_dd': float(max_dd),
        'win_rate': float(win_rate),
        'total_trades': len(trades)
    }

class Individual:
    """Represents one parameter set."""

    def __init__(self, delta=None, min_dte=None, max_dte=None, exit_pct=None):
        if delta is None:
            # Random initialization
            self.delta = np.random.uniform(0.15, 0.45)
            self.min_dte = np.random.randint(14, 50)
            self.max_dte = np.random.randint(self.min_dte + 10, 61)
            self.exit_pct = np.random.uniform(0.10, 0.90)
        else:
            self.delta = delta
            self.min_dte = min_dte
            self.max_dte = max_dte
            self.exit_pct = exit_pct

        self.fitness = None
        self.metrics = None

    def evaluate(self, spy_data):
        """Evaluate fitness."""
        self.metrics = simulate_csp_strategy(
            spy_data=spy_data,
            target_delta=self.delta,
            min_dte=self.min_dte,
            max_dte=self.max_dte,
            profit_target_pct=self.exit_pct
        )
        self.fitness = self.metrics['bps']
        return self.fitness

    def mutate(self, mutation_rate=0.2):
        """Mutate parameters."""
        if np.random.random() < mutation_rate:
            self.delta = np.clip(self.delta + np.random.normal(0, 0.05), 0.15, 0.45)

        if np.random.random() < mutation_rate:
            self.min_dte = int(np.clip(self.min_dte + np.random.randint(-5, 6), 14, 50))

        if np.random.random() < mutation_rate:
            self.max_dte = int(np.clip(self.max_dte + np.random.randint(-5, 6), self.min_dte + 10, 60))

        if np.random.random() < mutation_rate:
            self.exit_pct = np.clip(self.exit_pct + np.random.normal(0, 0.1), 0.10, 0.90)

    def crossover(self, other):
        """Crossover with another individual."""
        child = Individual(
            delta=(self.delta + other.delta) / 2,
            min_dte=int((self.min_dte + other.min_dte) / 2),
            max_dte=int((self.max_dte + other.max_dte) / 2),
            exit_pct=(self.exit_pct + other.exit_pct) / 2
        )
        return child

    def __repr__(self):
        return f"Individual(delta={self.delta:.3f}, DTE={self.min_dte}-{self.max_dte}, exit={self.exit_pct:.2f}, fitness={self.fitness:.3f})"

def evolutionary_optimization(
    population_size=20,
    generations=30,
    mutation_rate=0.2,
    elite_size=4
):
    """Run evolutionary algorithm optimization."""
    print("=" * 80)
    print("CSP Model - Evolutionary Algorithm Optimization")
    print("=" * 80)
    print()

    # Load data
    print("Loading SPY data...")
    spy_data = load_spy_data()
    print(f"✅ Loaded {len(spy_data)} bars")
    print()

    print(f"EA Parameters:")
    print(f"  Population size: {population_size}")
    print(f"  Generations: {generations}")
    print(f"  Mutation rate: {mutation_rate}")
    print(f"  Elite size: {elite_size}")
    print()
    print("-" * 80)

    # Initialize population
    print("Initializing random population...")
    population = [Individual() for _ in range(population_size)]

    # Evaluate initial population
    for ind in population:
        ind.evaluate(spy_data)

    best_overall = None
    history = []

    # Evolution loop
    for gen in range(generations):
        # Sort by fitness
        population.sort(key=lambda x: x.fitness, reverse=True)

        # Track best
        best_gen = population[0]
        if best_overall is None or best_gen.fitness > best_overall.fitness:
            best_overall = Individual(
                delta=best_gen.delta,
                min_dte=best_gen.min_dte,
                max_dte=best_gen.max_dte,
                exit_pct=best_gen.exit_pct
            )
            best_overall.fitness = best_gen.fitness
            best_overall.metrics = best_gen.metrics

        avg_fitness = np.mean([ind.fitness for ind in population])

        print(f"Gen {gen+1:2d}/{generations}: Best BPS={best_gen.fitness:.3f}, "
              f"Avg={avg_fitness:.3f} | "
              f"delta={best_gen.delta:.3f}, DTE={best_gen.min_dte}-{best_gen.max_dte}, "
              f"exit={best_gen.exit_pct:.2f}")

        history.append({
            'generation': gen + 1,
            'best_bps': best_gen.fitness,
            'avg_bps': avg_fitness,
            'best_delta': best_gen.delta,
            'best_min_dte': best_gen.min_dte,
            'best_max_dte': best_gen.max_dte,
            'best_exit_pct': best_gen.exit_pct
        })

        # Create next generation
        next_gen = []

        # Elitism - keep top performers
        next_gen.extend(population[:elite_size])

        # Generate offspring
        while len(next_gen) < population_size:
            # Tournament selection
            parent1 = max(np.random.choice(population, 3), key=lambda x: x.fitness)
            parent2 = max(np.random.choice(population, 3), key=lambda x: x.fitness)

            # Crossover
            child = parent1.crossover(parent2)

            # Mutation
            child.mutate(mutation_rate)

            # Evaluate
            child.evaluate(spy_data)

            next_gen.append(child)

        population = next_gen

    print("-" * 80)
    print()

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    history_df = pd.DataFrame(history)

    Path('results').mkdir(exist_ok=True)
    history_file = f'results/csp_ea_history_{timestamp}.csv'
    history_df.to_csv(history_file, index=False)

    print("=" * 80)
    print("🏆 BEST PARAMETERS (Evolutionary Algorithm)")
    print("=" * 80)
    print(f"  Delta: {best_overall.delta:.3f}")
    print(f"  DTE: {best_overall.min_dte}-{best_overall.max_dte} days")
    print(f"  Exit %: {best_overall.exit_pct:.1%}")
    print()
    print(f"  BPS: {best_overall.metrics['bps']:.3f}")
    print(f"  Sharpe: {best_overall.metrics['sharpe']:.2f}")
    print(f"  CAGR: {best_overall.metrics['cagr']:.2%}")
    print(f"  Max DD: {best_overall.metrics['max_dd']:.2%}")
    print(f"  Win Rate: {best_overall.metrics['win_rate']:.1%}")
    print(f"  Total Trades: {best_overall.metrics['total_trades']:.0f}")
    print()
    print(f"Evolution history saved to: {history_file}")
    print("=" * 80)

    return best_overall, history_df

if __name__ == "__main__":
    # Set random seed for reproducibility
    np.random.seed(42)

    best, history = evolutionary_optimization(
        population_size=20,
        generations=30,
        mutation_rate=0.2,
        elite_size=4
    )
