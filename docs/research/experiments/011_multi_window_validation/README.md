# Experiment 011: Multi-Window Validation

## Objective
Fix the single-year validation failure from Experiment 010 by validating on multiple market regimes.

## Hypothesis
Models that pass validation on diverse market conditions (bear, recovery, bull) will generalize better to unseen data than models validated on a single year.

## Approach
- **Training**: 2015-2021 (7 years)
- **Validation Windows**:
  - 2022: Bear market (primary validation in EA)
  - 2023: Recovery market (manual validation)
  - 2024: Bull market (manual validation)
- **Test**: 2025 (final out-of-sample)

## Key Changes from Experiment 010
1. **Constrained leverage**: Max 1.5x (was 2.0x)
2. **Multiple validation windows**: Must pass 2022, 2023, AND 2024
3. **Bear market primary validation**: EA optimizes against 2022 (hardest year)

## Success Criteria
- [ ] Training BPS > 0.8
- [ ] 2022 validation BPS > 0.5 (bear market)
- [ ] 2023 validation BPS > 0.5 (recovery)
- [ ] 2024 validation BPS > 0.5 (bull)
- [ ] Max degradation < 25%
- [ ] 2025 test BPS > 0.5 (final confirmation)

## Status
- [x] EA optimization complete
- [ ] ~~Multi-window validation passed~~ **FAILED - 185-232% degradation**
- [ ] ~~2025 out-of-sample test passed~~ **Not attempted - strategy fundamentally flawed**

## Results

### Experiment 011 (1.5x leverage)
- Training BPS: 1.2266
- Validation BPS: -1.0446
- **Degradation: 185%**

### Experiment 011b (no leverage)
- Training BPS: 1.1856
- Validation BPS: -1.5697
- **Degradation: 232%**

## Conclusion

**CRITICAL FINDING**: Momentum-based sector rotation fundamentally cannot survive bear markets. This is not a parameter problem - it's a strategy architecture problem.

See [CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md](CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md) for full analysis.

## Next Steps

Model requires architectural changes before any further EA optimization:
1. Add defensive mode (100% TLT) in bear markets
2. Add volatility-based exposure reduction
3. Consider mean reversion for bear markets
