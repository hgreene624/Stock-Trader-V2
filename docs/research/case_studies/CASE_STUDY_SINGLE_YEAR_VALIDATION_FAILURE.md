# Case Study: Single-Year Validation Failure

## Experiment 010 - SectorRotationAdaptive_v4

**Date**: 2025-11-23
**Status**: FAILED - Model passed validation but failed out-of-sample test

## Summary

Despite implementing proper train/validate split with overfitting detection, the EA-optimized model passed validation (6.6% degradation) but catastrophically failed on the 2025 out-of-sample test (-0.8494 BPS).

## Configuration

- **Training period**: 2015-01-01 to 2023-12-31 (9 years)
- **Validation period**: 2024-01-01 to 2024-12-31 (1 year)
- **Test period**: 2025-01-01 to 2025-11-23 (held out)
- **Parameters**: 8 free parameters
- **Population**: 30, Generations: 20
- **Overfitting threshold**: 30% degradation

## Results

| Period | BPS | Degradation |
|--------|-----|-------------|
| Training (2015-2023) | 1.2047 | - |
| Validation (2024) | 1.1254 | 6.6% |
| **Test (2025)** | **-0.8494** | **170.5%** |

### Winner Parameters
```yaml
atr_period: 14
stop_loss_atr_mult: 2.91
take_profit_atr_mult: 3.51
bull_leverage: 1.77
bear_leverage: 1.96
bull_momentum_period: 160
bear_momentum_period: 180
bull_top_n: 2
```

## Root Cause Analysis

### Why Validation Passed But Test Failed

1. **Similar Market Regimes**: 2024 was a strong bull market year, similar to most of 2015-2023. The validation year didn't represent different market conditions.

2. **2025 Regime Shift**: 2025 YTD has seen different market dynamics (tariff uncertainty, rotation patterns) that the model wasn't exposed to during training/validation.

3. **Single Year Insufficient**: One validation year can't capture the diversity of market conditions needed to test generalization.

4. **Bull Market Optimization**: The model optimized for bull market conditions across the entire training set, leading to high leverage (1.77x/1.96x) that fails in volatile conditions.

## Key Learnings

### 1. Single-Year Validation is Insufficient
Even with proper train/validate split, using a single year for validation can fail if that year is similar to training data.

### 2. Market Regime Matters
The validation period must include diverse market conditions:
- Bull markets (2017, 2019, 2021, 2024)
- Bear markets (2022)
- Crisis/recovery (2020)

### 3. High Leverage = Fragility
Parameters with leverage > 1.5x may work in training but amplify losses in adverse conditions.

### 4. Overfitting Can Be Subtle
6.6% degradation looked acceptable but masked regime-specific overfitting.

## Recommendations

### Immediate Fixes

1. **Multi-Window Validation**
   - Train on 2015-2021
   - Validate on 2022 (bear), 2023 (recovery), 2024 (bull)
   - Must pass ALL validation windows

2. **Crisis Period Testing**
   - Mandatory testing on 2020 (COVID crash)
   - Mandatory testing on 2022 (bear market)
   - Model must have positive returns in crisis periods

3. **Parameter Constraints**
   - Cap leverage at 1.5x to reduce fragility
   - Require conservative defaults that work across regimes

### Validation Framework Improvements

```python
# Required validation windows
validation_windows = [
    ('2022-01-01', '2022-12-31'),  # Bear market
    ('2023-01-01', '2023-12-31'),  # Recovery
    ('2024-01-01', '2024-12-31'),  # Bull market
]

# Must pass ALL windows with:
# - BPS > 0.5
# - Max degradation < 20% from training
# - Positive returns in 2022 (crisis test)
```

## Comparison to Previous Failures

| Experiment | Training | Validation | Test | Cause |
|------------|----------|------------|------|-------|
| 008 (v3 28% CAGR) | 1.57 BPS | N/A | -17.58% CAGR | No validation at all |
| **010 (v4 validated)** | **1.20 BPS** | **1.13 BPS** | **-0.85 BPS** | **Single-year validation insufficient** |

## Conclusion

Single-year validation is necessary but not sufficient. The validation period must be diverse enough to represent future market conditions. Multi-window validation across different market regimes (bull, bear, crisis) is required for robust model development.

## Next Steps

Implement Experiment 011 with:
1. Multi-window validation (2022, 2023, 2024)
2. Constrained parameter ranges (max leverage 1.5x)
3. Crisis period stress testing
4. 2025 final out-of-sample test
