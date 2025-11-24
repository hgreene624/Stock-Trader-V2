# V1: Tuned Crash Thresholds

## Hypothesis
Earlier crash detection (VIX 30 vs 35, SPY -5% vs -7%) and faster recovery (2 weeks vs 4) will reduce drawdowns while maintaining returns.

## Parameters
```yaml
crash_drop_threshold: -0.05  # Was -0.07
vix_crash_threshold: 30      # Was 35
crash_exposure: 0.40         # Was 0.25
dip_buy_weeks: 2             # Was 4
use_relative_strength: false
use_correlation_sizing: false
```

## Results
- **CAGR**: 7.58%
- **Sharpe**: 1.296
- **Max DD**: 31.4%
- **BPS**: 0.613

## Conclusion
**FAILED** - Severely damaged performance (-7.6% vs V3 baseline).

The "earlier" crash thresholds triggered too many false positives, keeping the model out of the market during normal corrections that subsequently recovered.

## Key Learning
**Lower thresholds ≠ better protection.** The original V3 thresholds (VIX 35, SPY -7%) were correctly calibrated. Don't change them.
