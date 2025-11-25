# Experiment 014: Adaptive Regime Switcher

**Date**: November 25, 2025
**Status**: 🔄 In Design
**Objective**: Create all-weather model combining SectorRotationAdaptive_v3 (bull) with BearDipBuyer_v1 (panic) via intelligent regime switching

---

## Executive Summary

We have two excellent specialized models:
1. **SectorRotationAdaptive_v3**: 17.64% CAGR (2020-2024) - bull market champion
2. **BearDipBuyer_v1**: +15.71% in 2020 COVID crash - panic specialist

**Problem**: Each underperforms in the other's domain
- SectorRotation: Likely suffers during panic crashes
- BearDipBuyer: Only +2.55% in 2020 full year (vs SPY +16.64%)

**Solution**: **AdaptiveRegimeSwitcher_v1** - intelligently switches between models based on market conditions

**Goal**: Beat both constituent models AND SPY across full market cycle (2020-2024)

---

## Hypothesis

**Regime-based switching will outperform static allocation by:**
1. Capturing bull market gains with SectorRotation (VIX < 25-30)
2. Protecting capital with BearDipBuyer during panic (VIX > 30-35)
3. Avoiding the weaknesses of each model in unfavorable conditions

**Expected Result**: CAGR > 17.64% (current champion) with better drawdown protection

---

## Model Design: AdaptiveRegimeSwitcher_v1

### Core Logic

```python
if VIX > 35.0:
    # EXTREME PANIC - Full BearDipBuyer
    weights = BearDipBuyer_v1.generate_weights(context)

elif VIX > 30.0:
    # ELEVATED PANIC - Blend 70% BearDipBuyer, 30% SectorRotation
    bear_weights = BearDipBuyer_v1.generate_weights(context) * 0.7
    bull_weights = SectorRotation_v3.generate_weights(context) * 0.3
    weights = combine(bear_weights, bull_weights)

else:
    # NORMAL MARKETS - Full SectorRotation
    weights = SectorRotation_v3.generate_weights(context)
```

### Regime Detection Parameters

**VIX Thresholds** (initial):
- **VIX < 25**: Normal markets → 100% SectorRotation
- **VIX 25-30**: Transitional → Consider blending
- **VIX 30-35**: Elevated panic → 70% BearDipBuyer, 30% SectorRotation
- **VIX > 35**: Extreme panic → 100% BearDipBuyer

**Additional Signals** (optional enhancements):
- RSI oversold (< 25)
- SPY distance from 200-day MA
- Market drawdown from recent high
- Trend strength deterioration

### Transition Smoothing

**Problem**: Avoid thrashing between models on VIX 30-35 boundary

**Solutions**:
1. **Hysteresis**: Different thresholds for entering vs exiting panic mode
   - Enter panic at VIX > 32
   - Exit panic at VIX < 28

2. **Minimum Hold Period**: Stay in regime for at least N days (5-10)

3. **Gradual Blending**: Linear interpolation between 25-35 VIX range

---

## Testing Plan

### Phase 1: Full Period Test (2020-2024)
**Objective**: Beat SectorRotation (17.64%) and SPY (14.34%)

**Test Profiles**:
- `exp014_combined_2020_2024` - Full period test
- `exp014_sector_baseline` - SectorRotation alone for comparison
- Benchmark: SPY buy-and-hold

**Success Criteria**:
- CAGR > 17.64%
- Max DD < 30%
- Sharpe > 2.0
- BPS > 1.0

### Phase 2: Regime-Specific Analysis
**Objective**: Confirm proper switching behavior

**Test Periods**:
- **2020 Q1**: COVID crash (should use BearDipBuyer)
- **2020 Q2-Q4**: Recovery (should use SectorRotation)
- **2021**: Bull run (should use SectorRotation)
- **2022**: Bear market (should blend/switch appropriately)

### Phase 3: Sensitivity Analysis
**Objective**: Find optimal VIX thresholds

**Parameters to Test**:
- VIX panic threshold: [30, 32, 35, 38]
- VIX normal threshold: [20, 23, 25, 28]
- Blend ratio during transition: [0.5/0.5, 0.6/0.4, 0.7/0.3]

---

## Implementation Plan

### Step 1: Create Base Model
```python
# models/adaptive_regime_switcher_v1.py

class AdaptiveRegimeSwitcher_v1(BaseModel):
    def __init__(self,
                 bull_model,  # SectorRotationAdaptive_v3
                 panic_model,  # BearDipBuyer_v1
                 vix_panic_threshold=35.0,
                 vix_elevated_threshold=30.0,
                 vix_normal_threshold=25.0):
        ...

    def detect_regime(self, context):
        # Return: 'panic', 'elevated', or 'normal'
        ...

    def generate_weights(self, context):
        regime = self.detect_regime(context)
        if regime == 'panic':
            return self.panic_model.generate_weights(context)
        elif regime == 'elevated':
            return self.blend_models(context, panic_weight=0.7)
        else:
            return self.bull_model.generate_weights(context)
```

### Step 2: Create Test Profiles
- Full period comparison profile
- Regime-specific profiles
- Sensitivity test profiles

### Step 3: Run Tests
1. Full period vs SectorRotation vs SPY
2. Regime-specific periods
3. Parameter sensitivity

### Step 4: Analyze & Document
- Performance metrics
- Regime switching timeline
- Trade analysis
- Comparison charts

---

## Expected Challenges

### Challenge 1: Model Interference
**Issue**: Two models may have conflicting universes/parameters
**Solution**: Normalize and combine weights from different universes

### Challenge 2: Transition Costs
**Issue**: Switching models incurs trades and transaction costs
**Solution**: Hysteresis and minimum hold periods to reduce switches

### Challenge 3: VIX False Signals
**Issue**: VIX can spike temporarily without sustained panic
**Solution**: Require VIX to stay elevated for N days before switching

### Challenge 4: Overfitting Thresholds
**Issue**: Optimizing VIX thresholds on 2020-2024 may not generalize
**Solution**: Keep thresholds simple and intuitive (30/35 are standard levels)

---

## Success Metrics

**Primary**:
- CAGR > 17.64% (beat SectorRotation)
- Max DD < 27.7% (better than SectorRotation)
- Sharpe > 2.238 (better than SectorRotation)

**Secondary**:
- Proper regime detection (switched to BearDipBuyer during 2020 crash)
- Minimal thrashing (< 10 regime switches per year)
- Outperforms both models in their weak periods

---

## Files & Artifacts

**Models**:
- `models/adaptive_regime_switcher_v1.py` - Combined model implementation

**Profiles**:
- `exp014_combined_2020_2024` - Full period test
- `exp014_combined_2020_q1` - COVID crash test
- `exp014_sensitivity_vix30` - VIX threshold tests

**Documentation**:
- This README.md - Experiment design
- `RESULTS.md` - Performance results (TBD)
- `ANALYSIS.md` - Regime switching analysis (TBD)

---

## References

- **Experiment 001**: SectorRotationAdaptive_v3 development (17.64% CAGR)
- **Experiment 013**: BearDipBuyer_v1 validation (+15.71% in COVID crash)
- **BEST_RESULTS.md**: Current champion metrics

---

*Experiment Created: November 25, 2025*
*Status: Design Complete, Ready for Implementation*
*Next: Implement AdaptiveRegimeSwitcher_v1 model*
