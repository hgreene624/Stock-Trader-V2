# V4 Drawdown Reduction: Failed Experiment

## Date
2024-11-23

## Summary

Attempted to reduce drawdowns from V3 by adding defensive filters. **Experiment failed** - all metrics got worse.

## Results

| Metric | V3 (baseline) | V4 (this experiment) | Change |
|--------|---------------|----------------------|--------|
| CAGR | 17.17% | 10.31% | **-6.86%** |
| Sharpe | 2.013 | 1.424 | **-0.589** |
| Max DD | -23.98% | -32.55% | **+8.57% worse** |
| BPS | 0.921 | 0.668 | **-0.253** |

## What Was Tried

### 1. Trend Confirmation Filter
Only buy sectors above their 20-day SMA.

**Problem**: Filtered out recovery opportunities when sectors were just starting to turn around.

### 2. VIX-Based Position Scaling
Reduce exposure when VIX > 25, minimum 50% exposure at VIX > 35.

**Problem**: Missed the big recovery moves that happen during volatile periods.

### 3. Strict Hold Period Enforcement
Force model to hold positions for minimum period regardless of signals.

**Problem**: Prevented adaptation to changing conditions.

## Why It Failed

The defensive measures caused the model to:
1. **Sit in cash during recovery periods** - Missing the upside
2. **Still experience initial drops** - Before filters kicked in
3. **Miss re-entry opportunities** - Trend filter blocked buys during early recoveries

The worst months identified in V3 (Oct 2023, Aug 2022, etc.) were actually **normal market volatility**. Attempting to filter them out caused more harm than good by missing the subsequent recoveries.

## Key Lesson

**Don't over-optimize for specific losing periods.** The V3 model's losses were part of its natural risk/reward profile. The 23.98% drawdown that produced 17.17% CAGR is preferable to a 32.55% drawdown that only produced 10.31% CAGR.

## Conclusion

**V3 remains the best model** at 17.17% CAGR, Sharpe 2.013, with risk-adjusted momentum and 1.4x leverage.

The drawdown reduction approach doesn't work with simple filters. Alternative approaches to explore:
- Earlier exit signals (not entry filters)
- Trailing stops instead of minimum holds
- Sector correlation analysis to avoid concentrated risk

## Files

- `equity_curve.png` - Equity curve showing underperformance
- `drawdown.png` - Shows worse 32.55% drawdown
- `summary_report.txt` - Full metrics
- `trades.csv` - Trade log (1390 trades)
- `model_source.py` - V4 model code

## Model Location

`models/sector_rotation_consistent_v4.py`
