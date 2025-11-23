# Experiment 006: Consistent Stacking Alpha

## Objective
Beat SPY consistently each year with gains that **stack** (no year-over-year give-back).

## Success Criteria
- Beat SPY 5/5 years
- Each year-end NAV > previous year-end NAV
- Max drawdown < 30%
- Leverage: 1.0-1.25x (small account compatible)

---

## Version Summary

| Version | Model | CAGR | Max DD | Sharpe | Status |
|---------|-------|------|--------|--------|--------|
| V1 | SectorRotationConsistent_v1 | 17.78% | -36.1% | 2.170 | Baseline - too much DD |
| V2 | SectorRotationConsistent_v2 | 17.78% | -36.1% | 2.170 | Same as V1 |
| V3 | SectorRotationConsistent_v3 | **15.33%** | **-23.98%** | 1.904 | **Best** - crash protection works |

**Current Best**: V3 - beats SPY (14.34%) with acceptable drawdown (<30%)

---

## Version Details

### [V1: Baseline with Regime Detection](v1_baseline/README.md)
- 4-state regime detection
- Result: -36% max DD (too high)

### [V2: Recovery Regime Detection](v2_recovery_regime/README.md)
- Added recovery regime
- Result: No improvement (MA crossovers too slow)

### [V3: Crash Protection + Dip Buying](v3_crash_protection/README.md)
- Fast crash detection via SPY/VIX
- Result: **12% reduction in max DD** while still beating SPY

---

## Infrastructure Improvements

**Reference Data Provider** (implemented for V3):
- Models can now access SPY/VIX for crash detection without trading them
- Added `reference_assets` config to system.yaml
- Added `load_reference_data()` to pipeline.py

---

## Next Steps
1. Tune V3 crash parameters (crash_exposure, dip_buy_weeks, VIX thresholds)
2. Consider combining with ATR-based stop losses from Experiment 004
3. Test on different market periods

---

## Key Learnings

1. **Don't optimize for black swans** - COVID was a once-in-decade event
2. **Regime detection has limits** - MA crossovers lag during V-shaped recoveries
3. **Capital preservation > alpha** during crashes
4. **Gradual re-entry** is safer than trying to time the bottom
5. **Infrastructure matters** - reference data provider was essential for crash detection
