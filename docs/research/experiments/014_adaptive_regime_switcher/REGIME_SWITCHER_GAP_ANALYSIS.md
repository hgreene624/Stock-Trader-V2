# AdaptiveRegimeSwitcher Performance Gap Analysis

## Executive Summary

The AdaptiveRegimeSwitcher wrapper underperforms standalone SectorRotationAdaptive_v3 by **6.53% CAGR** (8.58% vs 15.11%). After comprehensive analysis, I've identified the root causes and provide actionable fixes.

## Performance Breakdown by VIX Regime

### 1. Normal Regime (VIX < 30, occurs 89.3% of time)
- **Standalone**: 29.03% annualized
- **Combined**: 22.31% annualized
- **Gap**: -6.72% annualized
- **Impact**: This is where most of the performance gap originates

### 2. Elevated Regime (30 ≤ VIX < 35, occurs 6.4% of time)
- **Standalone**: -37.01% annualized
- **Combined**: -54.88% annualized
- **Gap**: -17.87% annualized
- **Impact**: Blending (70% BearDipBuyer + 30% SectorRotation) performs terribly

### 3. Extreme Regime (VIX ≥ 35, occurs 4.3% of time)
- **Standalone**: -72.67% annualized
- **Combined**: -64.99% annualized
- **Gap**: +7.69% annualized
- **Impact**: BearDipBuyer helps slightly but not enough to offset other losses

## Root Causes Identified

### 1. Entry Price Tracking Desynchronization (PRIMARY ISSUE)

The SectorRotationAdaptive_v3 model maintains internal state for entry price tracking:
- `self.entry_prices[sector]` - tracks when positions were entered
- `self.entry_timestamps[sector]` - tracks holding periods
- `self.entry_atr[sector]` - tracks ATR for stop/profit calculations

**Problem**: When the wrapper switches between regimes or blends weights, this internal tracking gets corrupted:
- During elevated mode (6.4% of time), blended weights don't match what SectorRotation expects
- When returning to normal mode, entry prices may be incorrect
- This causes premature exits or missed profit-taking opportunities

### 2. Universe Mismatch

- **Standalone**: 12 assets (11 sectors + TLT)
- **Combined**: 17 assets (11 sectors + TLT + SPY + QQQ + GLD + UUP + SHY)

The extra 5 assets come from BearDipBuyer and cause:
- Additional data loading overhead
- Different capital allocation dynamics
- Potential confusion in the backtester

### 3. Model Name Change

The wrapper returns `model_name='AdaptiveRegimeSwitcher_v1'` instead of `'SectorRotationAdaptive_v3'`. This could affect:
- Position tracking in the executor
- Commission calculations
- Trade attribution

### 4. Blending Logic Issues

When VIX is between 30-35 (elevated regime), the wrapper blends:
- 70% BearDipBuyer (defensive assets)
- 30% SectorRotation (growth sectors)

This blending:
- Dilutes the momentum strategy's effectiveness
- Creates positions that neither model "owns"
- Causes -17.87% annualized underperformance in this regime

## Recommendations

### Option 1: Remove the Wrapper (RECOMMENDED)
Since the wrapper underperforms in 89.3% of market conditions (normal regime), the simplest solution is to use standalone SectorRotationAdaptive_v3.

**Benefits**:
- Immediately gain 6.53% CAGR
- Simpler system with fewer failure modes
- Proven performance: 15.11% CAGR

### Option 2: Fix the Wrapper

If regime switching is required, implement these fixes:

#### A. Preserve Model State
```python
# In generate_target_weights, preserve bull_model's state
if regime == "normal":
    bull_output = self.bull_model.generate_target_weights(context)
    # Return bull_output directly, don't create new ModelOutput
    return bull_output  # This preserves model_name and all state
```

#### B. Adjust Thresholds
Reduce BearDipBuyer activation to only extreme events:
```python
vix_extreme_panic = 45.0  # Was 35.0
vix_elevated_panic = 40.0  # Was 30.0
vix_normal = 35.0         # Was 25.0
```

#### C. Change Blend Ratios
Favor momentum strategy even during elevated periods:
```python
blend_ratio_panic = 0.3   # Was 0.7 (now 30% panic, 70% bull)
```

#### D. Separate Universes
Don't combine universes. Let each model trade its own assets:
```python
# Don't combine universes
self.all_assets = self.bull_model.all_assets  # Use only bull universe
```

### Option 3: Create a Better Panic Model

BearDipBuyer's defensive approach (TLT, GLD, UUP) doesn't complement SectorRotation well. Consider:
- Creating a panic model that buys oversold growth sectors
- Using the same universe as SectorRotation
- Focusing on mean reversion instead of defensive rotation

## Validation Steps

After implementing fixes:

1. **Backtest both models** on 2020-2024
2. **Compare performance** in each VIX regime
3. **Verify entry/exit tracking** isn't corrupted
4. **Check trade counts** match expectations
5. **Ensure normal mode** performance matches standalone

## Expected Outcome

With proper fixes, the combined model should:
- Match standalone performance in normal regime (89.3% of time)
- Provide downside protection in extreme regimes (4.3% of time)
- Achieve overall CAGR ≥ 15% (matching or beating standalone)

## Conclusion

The AdaptiveRegimeSwitcher's complexity introduces multiple failure modes that degrade performance. The wrapper's attempt to blend two different strategies with different universes and tracking mechanisms creates more problems than it solves.

**Final Recommendation**: Use standalone SectorRotationAdaptive_v3 for its proven 15.11% CAGR performance. If regime adaptation is required, implement Option 2 fixes carefully with thorough testing.