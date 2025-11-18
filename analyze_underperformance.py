"""
Analyze where the strategy underperforms SPY.

This script identifies:
1. When the strategy is in cash vs invested
2. What returns we miss by being in cash
3. What drawdowns we avoid by being in cash
4. Optimal parameters to beat SPY
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt


def analyze_underperformance():
    """Analyze strategy underperformance vs SPY."""

    print("=" * 80)
    print("UNDERPERFORMANCE ANALYSIS")
    print("=" * 80)

    # Load results
    nav = pd.read_csv("results/nav_series.csv", index_col=0, parse_dates=True)
    trades = pd.read_csv("results/trade_log.csv")
    trades['timestamp'] = pd.to_datetime(trades['timestamp'])

    # Load SPY data
    spy_data = pd.read_parquet("data/equities/SPY_1D.parquet")
    spy_data['timestamp'] = pd.to_datetime(spy_data['timestamp'], utc=True)
    spy_data = spy_data.set_index('timestamp')

    # Filter to backtest period
    start_date = nav.index[0]
    end_date = nav.index[-1]
    spy_period = spy_data[(spy_data.index >= start_date) & (spy_data.index <= end_date)]

    print(f"\nAnalysis Period: {start_date.date()} to {end_date.date()}")
    print(f"Total Days: {len(spy_period)}")

    # === ANALYSIS 1: Time in Market ===
    print("\n" + "=" * 80)
    print("ANALYSIS 1: TIME IN MARKET")
    print("=" * 80)

    # Reconstruct positions from trades
    # Simplified: check if we have any holdings
    nav_values = nav.iloc[:, 0]
    nav_returns = nav_values.pct_change()

    # Estimate exposure by comparing strategy returns to market returns
    # If strategy return ~= 0 when market moves, we're in cash
    spy_returns = spy_period['close'].pct_change()

    # Align dates
    common_dates = nav.index.intersection(spy_period.index)
    nav_aligned = nav_returns.loc[common_dates]
    spy_aligned = spy_returns.loc[common_dates]

    # Estimate when we're invested (strategy return correlates with SPY)
    # Rough heuristic: if abs(strategy return) > 0.1%, we're invested
    invested_days = (nav_aligned.abs() > 0.001).sum()
    total_days = len(nav_aligned)
    cash_days = total_days - invested_days

    print(f"\nEstimated Market Exposure:")
    print(f"  Days Invested:  {invested_days:4d} ({invested_days/total_days*100:.1f}%)")
    print(f"  Days in Cash:   {cash_days:4d} ({cash_days/total_days*100:.1f}%)")

    # === ANALYSIS 2: Missed Opportunities ===
    print("\n" + "=" * 80)
    print("ANALYSIS 2: MISSED OPPORTUNITIES (Times We Were in Cash)")
    print("=" * 80)

    # Find periods where we were in cash
    cash_periods = nav_aligned[nav_aligned.abs() <= 0.001]

    if len(cash_periods) > 0:
        # SPY returns during our cash periods
        spy_during_cash = spy_aligned.loc[cash_periods.index]

        # Positive days we missed
        missed_gains = spy_during_cash[spy_during_cash > 0]

        # Negative days we avoided
        avoided_losses = spy_during_cash[spy_during_cash < 0]

        print(f"\nWhile in Cash:")
        print(f"  Total cash days: {len(cash_periods)}")
        print(f"  SPY gains missed: {len(missed_gains)} days, avg {missed_gains.mean()*100:.2f}% per day")
        print(f"  SPY losses avoided: {len(avoided_losses)} days, avg {avoided_losses.mean()*100:.2f}% per day")

        # Net effect
        missed_total = missed_gains.sum()
        avoided_total = avoided_losses.sum()
        net_effect = missed_total + avoided_total

        print(f"\nNet Effect of Cash Periods:")
        print(f"  Gains missed:    {missed_total*100:>7.2f}%")
        print(f"  Losses avoided:  {avoided_total*100:>7.2f}%")
        print(f"  Net cost:        {net_effect*100:>7.2f}%")

        if net_effect < 0:
            print(f"  ⚠️  Going to cash COST us {abs(net_effect)*100:.2f}%!")
        else:
            print(f"  ✓ Going to cash SAVED us {net_effect*100:.2f}%")

    # === ANALYSIS 3: Drawdown Protection ===
    print("\n" + "=" * 80)
    print("ANALYSIS 3: DRAWDOWN PROTECTION")
    print("=" * 80)

    # Calculate drawdowns
    def calculate_drawdown(series):
        cumulative = (1 + series).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown

    strategy_dd = calculate_drawdown(nav_aligned.fillna(0))
    spy_dd = calculate_drawdown(spy_aligned.fillna(0))

    print(f"\nDrawdown Comparison:")
    print(f"  Strategy Max DD: {strategy_dd.min()*100:.2f}%")
    print(f"  SPY Max DD:      {spy_dd.min()*100:.2f}%")
    print(f"  DD Reduction:    {(spy_dd.min() - strategy_dd.min())*100:.2f}%")

    # When did max DD occur?
    strategy_max_dd_date = strategy_dd.idxmin()
    spy_max_dd_date = spy_dd.idxmin()

    print(f"\n  Strategy worst DD: {strategy_max_dd_date.date()}")
    print(f"  SPY worst DD:      {spy_max_dd_date.date()}")

    # === ANALYSIS 4: Period-by-Period Analysis ===
    print("\n" + "=" * 80)
    print("ANALYSIS 4: PERFORMANCE BY PERIOD")
    print("=" * 80)

    # Define key market periods
    periods = {
        "COVID Crash": ("2020-02-01", "2020-04-01"),
        "2020 Recovery": ("2020-04-01", "2020-12-31"),
        "2021 Bull": ("2021-01-01", "2021-12-31"),
        "2022 Bear": ("2022-01-01", "2022-12-31"),
        "2023 Bull": ("2023-01-01", "2023-12-31"),
        "2024 Bull": ("2024-01-01", "2024-12-31"),
    }

    print(f"\n{'Period':<20} {'Strategy':<12} {'SPY':<12} {'Difference':<12}")
    print("-" * 60)

    for period_name, (start, end) in periods.items():
        try:
            period_start = pd.Timestamp(start, tz='UTC')
            period_end = pd.Timestamp(end, tz='UTC')

            # Get returns for period
            strategy_period = nav_aligned[(nav_aligned.index >= period_start) &
                                         (nav_aligned.index <= period_end)]
            spy_period_ret = spy_aligned[(spy_aligned.index >= period_start) &
                                         (spy_aligned.index <= period_end)]

            if len(strategy_period) > 0 and len(spy_period_ret) > 0:
                strategy_return = (1 + strategy_period).prod() - 1
                spy_return = (1 + spy_period_ret).prod() - 1
                diff = strategy_return - spy_return

                print(f"{period_name:<20} {strategy_return*100:>10.2f}% {spy_return*100:>10.2f}% "
                      f"{diff*100:>10.2f}%")
        except:
            pass

    # === ANALYSIS 5: Key Metrics for Improvement ===
    print("\n" + "=" * 80)
    print("ANALYSIS 5: IMPROVEMENT OPPORTUNITIES")
    print("=" * 80)

    # Calculate metrics
    total_strategy_return = (1 + nav_aligned).prod() - 1
    total_spy_return = (1 + spy_aligned).prod() - 1
    underperformance = total_spy_return - total_strategy_return

    print(f"\nOverall Performance:")
    print(f"  Strategy Total Return: {total_strategy_return*100:.2f}%")
    print(f"  SPY Total Return:      {total_spy_return*100:.2f}%")
    print(f"  Underperformance:      {underperformance*100:.2f}%")

    print(f"\nKey Findings:")

    if cash_days > total_days * 0.3:
        print(f"  ⚠️  High cash allocation ({cash_days/total_days*100:.1f}%)")
        print(f"     → Consider more aggressive entry/stay-in criteria")

    if net_effect < 0:
        print(f"  ⚠️  Cash periods cost {abs(net_effect)*100:.2f}% in missed gains")
        print(f"     → Exit signals may be too aggressive")

    if strategy_dd.min() > spy_dd.min() * 0.8:
        print(f"  ⚠️  Not much drawdown protection vs SPY")
        print(f"     → Defensive positioning not providing value")

    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)

    print("""
Based on this analysis, here are improvement ideas:

1. REDUCE TIME IN CASH
   - Use shorter MA periods (MA50/MA100 instead of MA200)
   - Allow partial positions (75%, 50%, 25% instead of 100%/0%)
   - Only exit on strong bearish signals (price < MA50 AND momentum < -5%)

2. IMPROVE ENTRY TIMING
   - Enter earlier (when price crosses above MA50, not MA200)
   - Use multiple timeframe confirmation
   - Add momentum strength filter

3. BETTER EXIT STRATEGY
   - Trail stops instead of hard MA exit
   - Partial exits (reduce by 25% at a time)
   - Only full exit on severe signals

4. POSITION SIZING
   - Scale based on trend strength
   - Overweight QQQ in tech bull markets
   - Dynamic allocation based on volatility

5. REGIME ADAPTATION
   - More aggressive in confirmed bull markets
   - More defensive only in confirmed bear markets
   - Use VIX or volatility for regime detection

Next: Let's create an improved model with these enhancements!
""")


if __name__ == "__main__":
    analyze_underperformance()
