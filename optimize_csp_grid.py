"""
Grid Search Optimization for Cash-Secured Put Model.

Tests all combinations of:
- Delta: 0.20, 0.30, 0.40
- DTE range: (21,30), (30,45), (45,60)
- Exit %: 0.25, 0.50, 0.75

Metrics: Sharpe, CAGR, Max DD, Win Rate, BPS
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from decimal import Decimal
from itertools import product
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
    """
    Simulate CSP strategy over historical period.

    Returns metrics: sharpe, cagr, max_dd, win_rate, total_trades
    """
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

    # Average holding period (mid-point of DTE range)
    avg_holding_period = (min_dte + max_dte) // 2

    # Test points (every avg_holding_period days to simulate trade cycle)
    test_dates = spy_data.index[::avg_holding_period]

    for test_date in test_dates:
        if test_date not in spy_data.index:
            continue

        # Get historical data up to this point
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
        output = model.generate_target_weights(context)
        should_enter = model._should_enter_position(context, historical, regime)

        if should_enter:
            # Estimate premium based on delta
            # Higher delta = higher premium
            if target_delta <= 0.25:
                premium_pct = 0.015  # 1.5%
            elif target_delta <= 0.35:
                premium_pct = 0.025  # 2.5%
            else:
                premium_pct = 0.035  # 3.5%

            # Simulate trade outcome
            # Exit at profit_target_pct of max profit
            realized_premium_pct = premium_pct * profit_target_pct

            # Assignment probability ~= delta
            assignment_prob = target_delta
            assigned = np.random.random() < assignment_prob

            if assigned:
                # Assigned: bought stock, assume sold shortly after
                # Look ahead to see SPY movement (simulate holding stock)
                future_idx = min(len(spy_data) - 1, spy_data.index.get_loc(test_date) + 5)
                future_price = spy_data['close'].iloc[future_idx]
                stock_return = (future_price - price) / price

                # Net return = premium + stock return (if held briefly)
                trade_return = realized_premium_pct + max(stock_return, -0.05)  # Cap loss at -5%
            else:
                # Expired worthless - keep premium
                trade_return = realized_premium_pct

            # Update capital
            capital *= (1 + trade_return)
            equity_curve.append(capital)

            trades.append({
                'date': test_date,
                'entry_price': price,
                'premium_pct': realized_premium_pct,
                'assigned': assigned,
                'return': trade_return,
                'capital': capital
            })

    # Calculate metrics
    if len(trades) == 0:
        return {
            'sharpe': 0.0,
            'cagr': 0.0,
            'max_dd': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'bps': 0.0
        }

    trades_df = pd.DataFrame(trades)
    returns = trades_df['return'].values

    # Sharpe ratio
    mean_return = returns.mean()
    std_return = returns.std()
    sharpe = (mean_return / std_return) * np.sqrt(252 / avg_holding_period) if std_return > 0 else 0

    # CAGR
    days = (spy_data.index[-1] - spy_data.index[0]).days
    years = days / 365
    cagr = (capital / initial_capital) ** (1 / years) - 1 if years > 0 else 0

    # Max drawdown
    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.expanding().max()
    drawdowns = (equity_series - rolling_max) / rolling_max
    max_dd = drawdowns.min()

    # Win rate
    win_rate = (returns > 0).mean()

    # BPS (Balanced Performance Score)
    bps = 0.4 * sharpe + 0.3 * (cagr * 10) + 0.2 * win_rate - 0.1 * abs(max_dd)

    return {
        'sharpe': float(sharpe),
        'cagr': float(cagr),
        'max_dd': float(max_dd),
        'win_rate': float(win_rate),
        'total_trades': len(trades),
        'bps': float(bps),
        'final_capital': float(capital)
    }

def grid_search_optimization():
    """Run grid search over CSP parameters."""
    print("=" * 80)
    print("CSP Model - Grid Search Optimization")
    print("=" * 80)
    print()

    # Load data
    print("Loading SPY data...")
    spy_data = load_spy_data()
    print(f"✅ Loaded {len(spy_data)} bars from {spy_data.index[0].date()} to {spy_data.index[-1].date()}")
    print()

    # Parameter grid
    deltas = [0.20, 0.30, 0.40]
    dte_ranges = [(21, 30), (30, 45), (45, 60)]
    exit_pcts = [0.25, 0.50, 0.75]

    total_combos = len(deltas) * len(dte_ranges) * len(exit_pcts)

    print(f"Parameter Grid:")
    print(f"  Delta: {deltas}")
    print(f"  DTE ranges: {dte_ranges}")
    print(f"  Exit %: {exit_pcts}")
    print(f"  Total combinations: {total_combos}")
    print()
    print("-" * 80)

    # Run grid search
    results = []
    combo_num = 0

    for delta in deltas:
        for (min_dte, max_dte) in dte_ranges:
            for exit_pct in exit_pcts:
                combo_num += 1
                print(f"[{combo_num}/{total_combos}] Testing delta={delta}, DTE={min_dte}-{max_dte}, exit={exit_pct:.0%}...",
                      end=' ', flush=True)

                metrics = simulate_csp_strategy(
                    spy_data=spy_data,
                    target_delta=delta,
                    min_dte=min_dte,
                    max_dte=max_dte,
                    profit_target_pct=exit_pct
                )

                result = {
                    'delta': delta,
                    'min_dte': min_dte,
                    'max_dte': max_dte,
                    'exit_pct': exit_pct,
                    **metrics
                }

                results.append(result)

                print(f"BPS={metrics['bps']:.3f}, Sharpe={metrics['sharpe']:.2f}, CAGR={metrics['cagr']:.1%}")

    print("-" * 80)
    print()

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Sort by BPS
    results_df = results_df.sort_values('bps', ascending=False)

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'results/csp_grid_search_{timestamp}.csv'
    Path('results').mkdir(exist_ok=True)
    results_df.to_csv(output_file, index=False)

    print("=" * 80)
    print("Top 10 Parameter Combinations (by BPS)")
    print("=" * 80)
    print()

    top_10 = results_df.head(10)
    print(top_10.to_string(index=False))
    print()

    # Best combination
    best = results_df.iloc[0]
    print("=" * 80)
    print("🏆 BEST PARAMETERS")
    print("=" * 80)
    print(f"  Delta: {best['delta']}")
    print(f"  DTE: {best['min_dte']}-{best['max_dte']} days")
    print(f"  Exit %: {best['exit_pct']:.0%}")
    print()
    print(f"  BPS: {best['bps']:.3f}")
    print(f"  Sharpe: {best['sharpe']:.2f}")
    print(f"  CAGR: {best['cagr']:.2%}")
    print(f"  Max DD: {best['max_dd']:.2%}")
    print(f"  Win Rate: {best['win_rate']:.1%}")
    print(f"  Total Trades: {best['total_trades']:.0f}")
    print()
    print(f"Results saved to: {output_file}")
    print("=" * 80)

    return results_df

if __name__ == "__main__":
    # Set random seed for reproducibility
    np.random.seed(42)

    results = grid_search_optimization()
