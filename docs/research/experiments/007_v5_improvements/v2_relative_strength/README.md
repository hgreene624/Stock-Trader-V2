# V2: Relative Strength Filter

## Hypothesis
Adding relative strength filter (only trade sectors > SPY) on top of tuned crash thresholds will improve win rate and CAGR.

## Parameters
- Tuned crash thresholds (from V1)
- `use_relative_strength: true`
- `relative_strength_period: 63`
- `use_correlation_sizing: false`

## Results
- **CAGR**: 10.13%
- **Sharpe**: 1.555
- **Max DD**: 31.4%
- **BPS**: 0.727

## Conclusion
**PARTIAL** - Relative strength helped (+2.5% vs V1's 7.58%) but still far below V3 baseline (15.33%).

The tuned crash thresholds are the problem, not the relative strength filter. Should test relative strength with original V3 crash params.
