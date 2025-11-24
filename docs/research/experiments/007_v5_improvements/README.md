# Experiment 007: V5 Improvements

**Date**: 2025-11-23
**Model**: SectorRotationConsistent_v5
**Status**: ❌ FAILED - All variants underperformed V3 baseline

## Hypothesis

Three improvements to V3 could increase CAGR and/or reduce drawdowns:
1. **Tuned crash thresholds** - Earlier crash detection (VIX 30 vs 35, SPY -5% vs -7%)
2. **Relative strength filter** - Only trade sectors outperforming SPY
3. **Correlation-based sizing** - Reduce weight for highly correlated sectors

## Results

| Variant | CAGR | Sharpe | BPS | vs V3 Baseline |
|---------|------|--------|-----|----------------|
| **V3 Baseline** | **15.19%** | **2.014** | **0.920** | - |
| V5 Tuned Crash | 7.58% | 1.296 | 0.613 | -7.61% |
| V5 + Rel Strength | 10.13% | 1.555 | 0.727 | -5.06% |
| V5 All Improvements | 10.13% | 1.555 | 0.727 | -5.06% |

**Benchmark**: SPY 14.34% CAGR (2020-2024)

## Analysis

### 1. Tuned Crash Thresholds: ❌ HARMFUL

The "improved" crash thresholds severely damaged performance:
- VIX 30 (vs 35) triggers too often - many false positives
- SPY -5% (vs -7%) exits market too early during normal corrections
- crash_exposure 0.40 (vs 0.25) still misses recovery upside

**Key Finding**: Lower thresholds ≠ better protection. The original V3 thresholds were calibrated correctly.

### 2. Relative Strength Filter: ⚠️ MARGINAL HELP

Added +2.55% CAGR on top of tuned crash (7.58% → 10.13%), but:
- Still 5% below V3 baseline
- May be helpful in isolation without the harmful crash changes

### 3. Correlation Sizing: ❌ NO EFFECT

Identical results with and without correlation sizing (10.13% both).
- May need different threshold (0.75 too high?)
- Or sector ETFs not correlated enough to trigger

## Conclusion

**FAILED** - All improvements made performance worse.

### Key Learnings

1. **Don't fix what isn't broken** - V3's crash thresholds (VIX 35, SPY -7%) were optimal
2. **Earlier ≠ Better** for crash detection - causes too many false positives
3. **Relative strength filter** shows promise but needs isolated testing without crash changes
4. **Correlation sizing** had no measurable impact

### Recommendations

1. **Keep V3 crash parameters** - they are correctly calibrated
2. **Test relative strength in isolation** - add to V3 without changing crash thresholds
3. **Investigate correlation sizing** - may need lower threshold or different approach

## Next Steps

1. Create V6 that only adds relative strength to V3 (no crash threshold changes)
2. Test correlation threshold at 0.6 and 0.7 instead of 0.75
3. Consider adaptive crash thresholds based on market regime

## Files

- `v1_tuned_crash/` - Tuned crash thresholds only
- `v2_relative_strength/` - Tuned crash + relative strength
- `v3_correlation_sizing/` - All improvements combined (renamed from v3_all_improvements)

---

*Lesson: Research-based assumptions can be wrong. Always test before deploying.*
