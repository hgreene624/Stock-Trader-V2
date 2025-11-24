# Case Study: Momentum Strategies Fail in Bear Markets

## Experiment 011 - Multi-Window Validation

**Date**: 2025-11-24
**Status**: FAILED - Fundamental strategy flaw discovered

## Executive Summary

After implementing proper bear market validation (2022), we discovered that **sector rotation momentum strategies fundamentally cannot survive bear markets**. This is not a parameter tuning problem - it's a core strategy limitation.

## Experiments Conducted

### Experiment 011: 1.5x Leverage
- Training: 2015-2021 (7 years)
- Validation: 2022 (bear market)
- **Result**: 185% degradation (BPS 1.23 → -1.04)

### Experiment 011b: No Leverage (1.0x max)
- Same periods
- **Result**: 232% degradation (BPS 1.19 → -1.57)
- **Worse without leverage!**

## Key Finding

**Removing leverage made performance WORSE**, proving this is not about risk amplification but about the fundamental momentum strategy being wrong for bear markets.

## Root Cause Analysis

### Why Momentum Fails in Bear Markets

1. **Momentum chases past winners**
   - In bull markets: Winners continue winning → Strategy works
   - In bear markets: Everything falls → No safe rotation target

2. **All sectors correlate in crashes**
   - 2022: XLK -33%, XLY -37%, XLC -40%
   - No sector rotation can help when all sectors fall together

3. **Regime detection insufficient**
   - Model uses `XLK > 200 MA` for regime
   - But only changes momentum parameters, not exposure
   - Continues rotating sectors instead of going defensive

4. **Mean reversion needed in bear markets**
   - Momentum = trend following = wrong in reversing markets
   - Should use mean reversion or go to cash/bonds

## Winner Parameters (Both Failed Validation)

### With 1.5x Leverage
```yaml
atr_period: 10
stop_loss_atr_mult: 2.16
take_profit_atr_mult: 3.31
bull_leverage: 1.5
bear_leverage: 1.5
bull_momentum_period: 160
bear_momentum_period: 102
bull_top_n: 5
```

### Without Leverage
```yaml
atr_period: 12
stop_loss_atr_mult: 2.24
take_profit_atr_mult: 1.68
bull_leverage: 1.0
bear_leverage: 0.70
bull_momentum_period: 160
bear_momentum_period: 90
bull_top_n: 5
```

## Comparison with Previous Experiments

| Experiment | Validation Year | Validation Type | Training BPS | Validation BPS | Degradation |
|------------|----------------|-----------------|-------------|----------------|-------------|
| 008 (v3) | None | None | 1.57 | N/A | N/A |
| 010 (v4) | 2024 | Bull market | 1.20 | 1.13 | 6.6% ✅ |
| **011** | **2022** | **Bear market** | **1.23** | **-1.04** | **185%** ❌ |
| **011b** | **2022** | **No leverage** | **1.19** | **-1.57** | **232%** ❌ |

**Critical Insight**: Exp 010 passed validation (2024) but failed 2025 test because 2024 was a bull year. Only bear market validation (2022) reveals the true strategy weakness.

## Lessons Learned

### 1. Bear Market Validation is Essential
Single-year validation on bull years (2024) gives false confidence. Must test against bear markets (2022, 2020, 2018).

### 2. Strategy Architecture > Parameter Optimization
No amount of EA optimization can fix a fundamentally flawed strategy. Momentum cannot work when all assets decline together.

### 3. Leverage is Not the Problem
Removing leverage made results worse (232% vs 185% degradation). The problem is the core rotation logic.

### 4. Regime Detection Must Change Behavior
Current regime detection only changes parameters. Must change strategy entirely:
- Bull: Momentum rotation with leverage
- Bear: Defensive positioning (TLT) or mean reversion

## Recommended Fixes

### Option 1: Defensive Bear Mode (Recommended)
```python
if regime == 'bear':
    # Go 100% defensive
    weights = {'TLT': 1.0}
else:
    # Normal momentum rotation
    weights = momentum_rotation()
```

### Option 2: Inverse Momentum in Bear
```python
if regime == 'bear':
    # Buy weakest performers (mean reversion)
    ranked = sorted(momentum, key=lambda x: x[1])  # Ascending
else:
    # Buy strongest (momentum)
    ranked = sorted(momentum, key=lambda x: x[1], reverse=True)
```

### Option 3: Accept Bear Underperformance
- Only optimize for bull markets
- Accept -20% years in bear markets
- Focus on long-term CAGR across full cycles

## Model Architecture Changes Needed

The SectorRotationAdaptive_v4 model requires fundamental changes:

1. **Add defensive mode**: Go to TLT when XLK < 200 MA
2. **Add volatility scaling**: Reduce exposure when VIX > 25
3. **Add correlation check**: Skip rotation when sector correlations > 0.8
4. **Consider mean reversion**: Buy oversold sectors in bear markets

## Conclusion

**Momentum-based sector rotation cannot survive bear markets through parameter optimization alone.** The strategy needs architectural changes to either:
1. Go defensive (cash/bonds) in bear markets
2. Use mean reversion instead of momentum
3. Significantly reduce exposure

This is a fundamental strategy limitation, not an overfitting problem. Future experiments must modify the model architecture before any EA optimization.

## Next Steps

1. Create SectorRotationAdaptive_v5 with defensive bear mode
2. Test v5 on 2022 before any EA optimization
3. If v5 survives 2022, then run EA optimization
4. Validate on 2020, 2022, 2024 (diverse conditions)
5. Final test on 2025
