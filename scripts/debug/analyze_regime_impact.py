#!/usr/bin/env python3
"""
Analyze the performance impact of AdaptiveRegimeSwitcher's regime transitions.
Compare standalone SectorRotation vs combined model during different VIX regimes.
"""

import pandas as pd
import numpy as np
from datetime import datetime

def main():
    print("=" * 80)
    print("ADAPTIVE REGIME SWITCHER PERFORMANCE GAP ANALYSIS")
    print("=" * 80)

    # Load VIX data to map regimes
    vix_df = pd.read_parquet('data/equities/^VIX_1D.parquet')
    vix_df = vix_df[(vix_df.index >= '2020-01-01') & (vix_df.index <= '2024-12-31')]

    # Define regime thresholds (from AdaptiveRegimeSwitcher_v1)
    VIX_NORMAL = 25
    VIX_ELEVATED_PANIC = 30
    VIX_EXTREME_PANIC = 35

    # Classify VIX regimes
    vix_df['date'] = vix_df.index.date
    vix_df['regime'] = 'normal'
    vix_df.loc[vix_df['close'] >= VIX_ELEVATED_PANIC, 'regime'] = 'elevated'
    vix_df.loc[vix_df['close'] >= VIX_EXTREME_PANIC, 'regime'] = 'extreme'

    # Load performance data
    standalone_perf = pd.read_csv('results/analysis/20251125_120208/nav_series.csv')
    combined_perf = pd.read_csv('results/analysis/20251125_122527/nav_series.csv')

    # Convert timestamps
    standalone_perf['timestamp'] = pd.to_datetime(standalone_perf['timestamp'])
    combined_perf['timestamp'] = pd.to_datetime(combined_perf['timestamp'])
    standalone_perf['date'] = standalone_perf['timestamp'].dt.date
    combined_perf['date'] = combined_perf['timestamp'].dt.date

    # Map VIX regime to each date
    def get_vix_regime(date):
        if date in vix_df['date'].values:
            return vix_df[vix_df['date'] == date].iloc[0]['regime']
        return 'unknown'

    standalone_perf['vix_regime'] = standalone_perf['date'].apply(get_vix_regime)
    combined_perf['vix_regime'] = combined_perf['date'].apply(get_vix_regime)

    # Calculate returns
    standalone_perf['return'] = standalone_perf['nav'].pct_change()
    combined_perf['return'] = combined_perf['nav'].pct_change()

    print("\n1. REGIME DISTRIBUTION (2020-2024):")
    print("-" * 50)
    regime_counts = vix_df['regime'].value_counts()
    for regime in ['normal', 'elevated', 'extreme']:
        if regime in regime_counts.index:
            count = regime_counts[regime]
            pct = (count / len(vix_df)) * 100
            vix_range = {
                'normal': 'VIX < 30',
                'elevated': '30 <= VIX < 35',
                'extreme': 'VIX >= 35'
            }[regime]
            print(f"  {regime:10}: {count:4} days ({pct:5.1f}%) - {vix_range}")

    print("\n2. PERFORMANCE BY REGIME:")
    print("-" * 50)

    for regime in ['normal', 'elevated', 'extreme']:
        standalone_regime = standalone_perf[standalone_perf['vix_regime'] == regime]
        combined_regime = combined_perf[combined_perf['vix_regime'] == regime]

        if len(standalone_regime) > 0 and len(combined_regime) > 0:
            # Calculate total return for each regime
            standalone_total = (1 + standalone_regime['return']).prod() - 1
            combined_total = (1 + combined_regime['return']).prod() - 1

            # Annualized return
            days = len(standalone_regime)
            years = days / 252
            standalone_annual = (1 + standalone_total) ** (1/years) - 1 if years > 0 else 0
            combined_annual = (1 + combined_total) ** (1/years) - 1 if years > 0 else 0

            print(f"\n  {regime.upper()} REGIME ({days} days):")
            print(f"    Standalone: {standalone_annual*100:6.2f}% annualized ({standalone_total*100:6.2f}% total)")
            print(f"    Combined:   {combined_annual*100:6.2f}% annualized ({combined_total*100:6.2f}% total)")
            print(f"    Gap:        {(combined_annual - standalone_annual)*100:6.2f}% annualized")

            # What model is active in combined during this regime?
            if regime == 'normal':
                print(f"    Active Model: 100% SectorRotation")
            elif regime == 'elevated':
                print(f"    Active Model: 70% BearDipBuyer + 30% SectorRotation (BLENDED)")
            else:  # extreme
                print(f"    Active Model: 100% BearDipBuyer")

    print("\n3. CRITICAL PERIODS ANALYSIS:")
    print("-" * 50)

    # March 2020 COVID crash
    march_2020_start = pd.Timestamp('2020-03-01')
    march_2020_end = pd.Timestamp('2020-03-31')

    standalone_march = standalone_perf[(standalone_perf['timestamp'] >= march_2020_start) &
                                        (standalone_perf['timestamp'] <= march_2020_end)]
    combined_march = combined_perf[(combined_perf['timestamp'] >= march_2020_start) &
                                    (combined_perf['timestamp'] <= march_2020_end)]

    if len(standalone_march) > 0 and len(combined_march) > 0:
        standalone_march_ret = (1 + standalone_march['return']).prod() - 1
        combined_march_ret = (1 + combined_march['return']).prod() - 1

        march_vix = vix_df[(vix_df.index >= march_2020_start) & (vix_df.index <= march_2020_end)]

        print(f"\n  MARCH 2020 COVID CRASH:")
        print(f"    VIX: Mean={march_vix['close'].mean():.1f}, Max={march_vix['close'].max():.1f}")
        print(f"    Standalone return: {standalone_march_ret*100:6.2f}%")
        print(f"    Combined return:   {combined_march_ret*100:6.2f}%")
        print(f"    Difference:        {(combined_march_ret - standalone_march_ret)*100:6.2f}%")

    # Recovery period (April-May 2020)
    recovery_start = pd.Timestamp('2020-04-01')
    recovery_end = pd.Timestamp('2020-05-31')

    standalone_recovery = standalone_perf[(standalone_perf['timestamp'] >= recovery_start) &
                                           (standalone_perf['timestamp'] <= recovery_end)]
    combined_recovery = combined_perf[(combined_perf['timestamp'] >= recovery_start) &
                                       (combined_perf['timestamp'] <= recovery_end)]

    if len(standalone_recovery) > 0 and len(combined_recovery) > 0:
        standalone_recovery_ret = (1 + standalone_recovery['return']).prod() - 1
        combined_recovery_ret = (1 + combined_recovery['return']).prod() - 1

        recovery_vix = vix_df[(vix_df.index >= recovery_start) & (vix_df.index <= recovery_end)]

        print(f"\n  APRIL-MAY 2020 RECOVERY:")
        print(f"    VIX: Mean={recovery_vix['close'].mean():.1f}, Max={recovery_vix['close'].max():.1f}")
        print(f"    Standalone return: {standalone_recovery_ret*100:6.2f}%")
        print(f"    Combined return:   {combined_recovery_ret*100:6.2f}%")
        print(f"    Difference:        {(combined_recovery_ret - standalone_recovery_ret)*100:6.2f}%")

    print("\n4. HYPOTHESIS:")
    print("-" * 50)
    print("""
    The 6.53% CAGR gap appears to be caused by:

    1. BearDipBuyer underperformance during extreme panic (VIX > 35)
       - Combined model switches to 100% BearDipBuyer when VIX > 35
       - BearDipBuyer buys defensive assets (TLT, GLD, UUP, SHY)
       - These may underperform vs SectorRotation's momentum approach

    2. Blending dilution during elevated regime (30 <= VIX < 35)
       - 70% BearDipBuyer dilutes SectorRotation's returns
       - Happens 6.4% of the time (81 days)

    3. Possible entry/exit tracking desync
       - When switching between regimes, entry prices may reset
       - This could trigger unnecessary trades
    """)

    print("\n5. RECOMMENDATIONS:")
    print("-" * 50)
    print("""
    To close the performance gap:

    1. ADJUST THRESHOLDS:
       - Raise VIX thresholds to reduce BearDipBuyer activation
       - Current: extreme=35, elevated=30
       - Suggested: extreme=45, elevated=40

    2. CHANGE BLEND RATIOS:
       - Current elevated: 70% bear / 30% bull
       - Suggested: 30% bear / 70% bull (favor momentum)

    3. IMPROVE BEARDIPBUYER:
       - Focus on growth assets during panics, not defensives
       - Or create a better panic-buying model

    4. REMOVE WRAPPER:
       - If regime switching isn't adding value, use standalone
    """)

if __name__ == "__main__":
    main()