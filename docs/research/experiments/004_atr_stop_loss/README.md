# Experiment 004: ATR Stop Loss Parameter Optimization

**Date**: 2025-11-22
**Model**: SectorRotationAdaptive_v3
**Status**: Complete - Learning only (not deployed)

## Abstract

Tested ATR-based stop loss and take profit parameters to determine optimal settings for the adaptive sector rotation model. Found that longer ATR periods (21 days) significantly outperform shorter periods, but overall performance still lags SPY benchmark. Wide stops and tight stops both hurt performance.

## Hypothesis

ATR-based stops can improve risk-adjusted returns by:
1. Cutting losses quickly (tight stops)
2. Letting winners run (higher take profit multiples)
3. Using appropriate volatility measurement periods

## Method

Tested 6 parameter combinations on SectorRotationAdaptive_v3:

| Profile | ATR Period | Stop Loss Mult | Take Profit Mult |
|---------|------------|----------------|------------------|
| baseline | 12 | 1.0 | 2.0 |
| tight | 10 | 0.5 | 1.5 |
| loose | 14 | 1.5 | 3.0 |
| quick_profit | 12 | 1.0 | 1.0 |
| wide_stops | 12 | 2.0 | 2.0 |
| long_period | 21 | 1.0 | 2.5 |

**Test Period**: 2020-01-01 to 2024-12-31
**Benchmark**: SPY (14.34% CAGR)

## Results

| Profile | CAGR | Sharpe | BPS | Notes |
|---------|------|--------|-----|-------|
| **long_period** | **10.68%** | **1.726** | **0.798** | Best performer |
| loose | 6.35% | 1.161 | 0.553 | |
| baseline | 6.19% | 1.151 | 0.554 | Current default |
| tight | 4.93% | 0.979 | 0.477 | Too many whipsaws |
| wide_stops | 2.64% | 0.676 | 0.349 | Gave back too much profit |
| quick_profit | FAILED | - | - | Weight limit exceeded |

## Analysis

### Key Findings

1. **Longer ATR period is significantly better**: 21-day ATR outperformed 12-day by +72% CAGR (10.68% vs 6.19%). Smoother volatility measurement reduces false signals.

2. **Tight stops hurt performance**: 0.5x stop loss multiplier caused excessive whipsaws, reducing CAGR by 20% vs baseline. Sector ETFs need room to breathe.

3. **Wide stops are worst**: 2.0x stop loss gave back too much profit on reversals. The asymmetry between stop and take profit matters.

4. **Optimal ratio appears to be 1:2.5**: Stop loss at 1.0x ATR, take profit at 2.5x ATR provides good risk/reward balance.

### Why Still Underperforming SPY?

Even the best configuration (10.68% CAGR) lags SPY (14.34% CAGR) by 3.66%. Possible reasons:

1. **Monthly rebalancing too slow**: ATR exits trigger intra-month but rebalancing waits for 21-day cycle
2. **Sector rotation drag**: Switching between sectors incurs costs and timing gaps
3. **Defensive positioning**: Model goes to TLT during uncertainty, missing rebounds
4. **Leverage not aggressive enough**: 1.5x leverage may need to be higher to compensate for sector rotation drag

### Recommendations for Future Research

1. **Test interaction with rebalancing frequency**: Does ATR exit + immediate reentry help?
2. **Test higher leverage with optimal ATR**: Can 1.8-2.0x leverage with 21-day ATR beat SPY?
3. **Test trailing stops**: ATR-based trailing stops instead of fixed take profit
4. **Remove ATR exits entirely**: Compare performance with pure momentum rebalancing

## Conclusion

ATR stop losses can improve Sharpe ratio (1.726 vs 1.151 baseline) but the overall CAGR improvement is insufficient to beat SPY. The 21-day ATR period with 1.0/2.5 stop/profit ratios is optimal within tested parameters, but fundamental model changes may be needed to close the gap with benchmark.

**Decision**: Do not deploy. Use findings to inform next experiment on combining optimal ATR with higher leverage or different rebalancing strategies.
