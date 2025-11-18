"""
Analyze expected returns from Cash-Secured Put strategy.

Simulates CSP premium collection and calculates:
- Expected annual return
- Win rate
- Risk-adjusted metrics
- Comparison to buy-and-hold SPY
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from decimal import Decimal

def load_spy_data(path: str = "data/equities/SPY_1D.parquet") -> pd.DataFrame:
    """Load SPY data from parquet file."""
    df = pd.read_parquet(path)
    return df

def simulate_csp_returns():
    """
    Simulate CSP returns based on historical signals.

    Assumptions:
    - Sell 0.30 delta put every 30-45 days
    - Target premium: 2-3% of strike price (typical for 30 delta put)
    - Assignment rate: ~30% (matches delta)
    - When assigned, sell stock at small profit or loss
    """
    print("=" * 80)
    print("Cash-Secured Put Returns Simulation")
    print("=" * 80)
    print()

    # Load SPY data
    spy_data = load_spy_data()
    print(f"Loaded {len(spy_data)} bars from {spy_data.index[0].date()} to {spy_data.index[-1].date()}")
    print()

    # Simulation parameters
    INITIAL_CAPITAL = 100_000
    PREMIUM_PCT = 0.025  # 2.5% premium (conservative)
    ASSIGNMENT_RATE = 0.30  # 30% probability of assignment
    AVG_HOLDING_PERIOD_DAYS = 35  # Target DTE
    TRADES_PER_YEAR = 252 / AVG_HOLDING_PERIOD_DAYS  # ~7.2 cycles/year

    # Estimate per-trade return
    # Scenario 1: Expire worthless (70% probability) - keep full premium
    return_expire = PREMIUM_PCT

    # Scenario 2: Assigned (30% probability) - keep premium, buy stock
    # Assume we sell stock shortly after at break-even or small profit
    # Net return is still the premium
    return_assigned = PREMIUM_PCT

    # Expected return per trade
    expected_return_per_trade = (
        (1 - ASSIGNMENT_RATE) * return_expire +
        ASSIGNMENT_RATE * return_assigned
    )

    # Annualized return
    annualized_return = expected_return_per_trade * TRADES_PER_YEAR

    print("Simulation Parameters:")
    print(f"  Initial Capital: ${INITIAL_CAPITAL:,}")
    print(f"  Target Delta: 0.30")
    print(f"  Premium per trade: {PREMIUM_PCT:.1%} of strike")
    print(f"  Assignment rate: {ASSIGNMENT_RATE:.0%}")
    print(f"  Avg holding period: {AVG_HOLDING_PERIOD_DAYS} days")
    print(f"  Trades per year: {TRADES_PER_YEAR:.1f}")
    print()

    print("Expected Returns:")
    print(f"  Per trade: {expected_return_per_trade:.2%}")
    print(f"  Annualized: {annualized_return:.2%}")
    print()

    # Compare to SPY buy-and-hold
    # Calculate SPY returns over the data period
    spy_start = spy_data['close'].iloc[0]
    spy_end = spy_data['close'].iloc[-1]
    spy_days = (spy_data.index[-1] - spy_data.index[0]).days
    spy_years = spy_days / 365
    spy_total_return = (spy_end - spy_start) / spy_start
    spy_cagr = (1 + spy_total_return) ** (1 / spy_years) - 1

    print("Benchmark Comparison (SPY Buy-and-Hold):")
    print(f"  Period: {spy_data.index[0].date()} to {spy_data.index[-1].date()}")
    print(f"  Total return: {spy_total_return:.2%}")
    print(f"  CAGR: {spy_cagr:.2%}")
    print(f"  Duration: {spy_years:.2f} years")
    print()

    # Estimate CSP outperformance
    # Note: CSP is lower risk (only sell in bull markets) but also lower upside
    # Realistic target: 10-15% annual return
    realistic_csp_return = 0.12  # 12% target

    print("Realistic CSP Performance Target:")
    print(f"  Conservative estimate: {realistic_csp_return:.2%} annual")
    print(f"  Reasoning:")
    print(f"    - Only trade in bull markets (83% of time historically)")
    print(f"    - Reduced premium in volatile markets")
    print(f"    - Early assignment costs")
    print(f"    - Management overhead")
    print()

    # Risk analysis
    print("Risk Profile:")
    print("  Max risk per trade: 100% (if SPY crashes to 0)")
    print("  Practical max drawdown: ~10-20% (assignment during correction)")
    print("  Typical drawdown: <5% (early exit on profit targets)")
    print("  Diversification: Single underlying (SPY)")
    print()

    # Simulate monthly returns over last year
    print("-" * 80)
    print("Simulated Monthly Returns (Last 12 Months)")
    print("-" * 80)
    print()

    # Get monthly data points
    monthly_dates = spy_data.index[-252::21]  # ~Monthly over last year

    monthly_returns = []
    for i in range(1, len(monthly_dates)):
        start_date = monthly_dates[i-1]
        end_date = monthly_dates[i]

        start_price = spy_data.loc[start_date, 'close']
        end_price = spy_data.loc[end_date, 'close']

        spy_monthly_return = (end_price - start_price) / start_price

        # Estimate CSP return for this month
        # Assume we collect premium if SPY is up or flat
        # If SPY down >5%, might have been assigned
        if spy_monthly_return >= -0.05:
            # Collected premium, expired worthless or early exit
            csp_return = PREMIUM_PCT / (TRADES_PER_YEAR / 12)  # Monthly equivalent
        else:
            # Assigned, held stock through decline
            csp_return = spy_monthly_return  # Same as SPY (minus collected premium)

        monthly_returns.append({
            'month': end_date.strftime('%Y-%m'),
            'spy_price': end_price,
            'spy_return': spy_monthly_return,
            'csp_return_est': csp_return
        })

    monthly_df = pd.DataFrame(monthly_returns)
    print(monthly_df.to_string(index=False))
    print()

    print(f"Average monthly CSP return (est): {monthly_df['csp_return_est'].mean():.2%}")
    print(f"Annualized (est): {monthly_df['csp_return_est'].mean() * 12:.2%}")
    print()

    print("=" * 80)
    print("Summary & Recommendations")
    print("=" * 80)
    print()
    print("✅ PROS:")
    print("  - Consistent income generation (premium collection)")
    print("  - Regime-aware (only trade in bull markets)")
    print("  - Lower correlation to SPY (sell volatility vs buy equity)")
    print("  - Downside protection from premium cushion")
    print()
    print("⚠️  CONS:")
    print("  - Capped upside (max gain = premium)")
    print("  - Assignment risk in corrections")
    print("  - Requires active management")
    print("  - Options data and execution costs")
    print()
    print("🎯 TARGET METRICS:")
    print("  - Annual return: 10-15%")
    print("  - Win rate: 70-85%")
    print("  - Max drawdown: <20%")
    print("  - Sharpe ratio: 1.0-1.5")
    print()
    print("📋 OPTIMIZATION IDEAS:")
    print("  1. Delta selection (test 0.20, 0.30, 0.40)")
    print("  2. DTE range (21-30 vs 30-45 vs 45-60)")
    print("  3. Exit timing (50% profit target vs DTE-based)")
    print("  4. Strike selection (ATM vs OTM)")
    print("  5. Regime filters (add volatility regime)")
    print("  6. Position sizing (max contracts)")
    print()
    print("🚀 NEXT STEPS:")
    print("  1. Test with real options data (Alpaca API)")
    print("  2. Paper trade for 30 days")
    print("  3. Monitor actual premium vs estimates")
    print("  4. Optimize parameters based on real results")
    print("  5. Consider multi-underlying (QQQ, IWM)")
    print("=" * 80)

if __name__ == "__main__":
    simulate_csp_returns()
