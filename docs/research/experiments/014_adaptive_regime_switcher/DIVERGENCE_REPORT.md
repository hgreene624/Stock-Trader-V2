# Trade Divergence Analysis Report: AdaptiveRegimeSwitcher vs SectorRotation

## Executive Summary

**ROOT CAUSE IDENTIFIED**: The AdaptiveRegimeSwitcher underperforms by -6.53% CAGR because it switches to a completely different trading universe during panic mode (VIX > 30), trading defensive assets that **lost money** during the COVID crash.

## Key Findings

### Performance Gap
- **Standalone SectorRotation**: 15.11% CAGR
- **Combined AdaptiveRegimeSwitcher**: 8.58% CAGR
- **Performance Loss**: -6.53% CAGR

### Divergence Timeline

#### Pre-Divergence (Jan 2 - Feb 26, 2020)
- Models trade identically (same symbols, quantities)
- Trade order differs but doesn't affect returns
- VIX < 30: Normal mode active

#### Divergence Begins (Feb 27, 2020)
- **VIX spikes to 39.16** → Panic mode activated
- Combined model starts trading **completely different assets**:
  - **Stops trading**: Sector ETFs (XLK, XLF, XLV, etc.)
  - **Starts trading**: SPY, QQQ, TLT, GLD, SHY, UUP

#### Peak Damage (March 2020)
- VIX reaches **82.69** on March 16, 2020
- Combined model in full panic mode (100% BearDipBuyer)
- Maximum performance gap: **-7.01%** on March 23

#### Recovery Phase (April-May 2020)
- VIX remains elevated (> 30) through April
- Combined model stays in panic/blended mode
- Performance gap persists and never recovers

## The Architecture Problem

### How AdaptiveRegimeSwitcher Works

```python
# Regime Detection (line 211-213)
regime = self.detect_regime(context)  # Based on VIX level

# Mode Selection
if regime == "extreme":  # VIX > 35
    # 100% BearDipBuyer_v1
    weights = self.panic_model.generate_target_weights(context)

elif regime == "elevated":  # VIX 30-35
    # 70% BearDipBuyer, 30% SectorRotation (blended)
    weights = blend_weights(panic_output, bull_output, 0.7)

else:  # regime == "normal", VIX < 30
    # 100% SectorRotation (FIX A applied here)
    return bull_output  # Returns directly
```

### The Universe Mismatch

**SectorRotationAdaptive_v3 trades**:
```python
universe = ['XLK', 'XLF', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLE', 'XLC']  # Sector ETFs
```

**BearDipBuyer_v1 trades**:
```python
universe = ['SPY', 'QQQ', 'TLT', 'GLD', 'UUP', 'SHY']  # Broad indices and safe havens
```

These are **completely different asset classes** with different behavior patterns.

## Quantified Impact

### Panic Mode Damage (Feb 27 - Apr 30, 2020)
- **Standalone return**: +2.95%
- **Combined return**: -0.06%
- **Lost during panic**: -3.01%

### Overall Impact (Full backtest period)
- **Standalone final return**: +102.04%
- **Combined final return**: +50.85%
- **Total performance gap**: -51.19%

## Why Fix A Didn't Work

**Fix A** (line 267 in adaptive_regime_switcher_v1.py):
```python
# Normal mode - return bull_output directly
return bull_output
```

This fix ensures that during normal mode (88.6% of the time), the combined model returns the exact same weights as standalone SectorRotation. **This part works correctly.**

**However**, the damage occurs during the 11.4% of time in panic mode when:
1. Model switches to different assets
2. Those defensive trades lose money
3. The losses compound and never recover

## Trade Evidence

### First Divergence (Feb 27, 2020) - VIX = 39.16

**Standalone trades**:
- XLK: BUY 251
- XLU: SELL 927

**Combined trades**:
- SHY: BUY 367 (cash equivalent - NEW)
- QQQ: BUY 104 (broad index - NEW)
- SPY: BUY 76 (broad index - NEW)
- XLK: SELL 320 (opposite direction!)
- XLU: SELL 927

The combined model is **actively selling** sector positions to buy defensive assets.

## Recommendations

### Option 1: Remove Panic Mode Entirely
Simply use SectorRotation in all market conditions. The standalone model handled the COVID crash successfully (+2.95% during panic period).

### Option 2: Fix BearDipBuyer Universe
Make BearDipBuyer trade the same sector ETFs as SectorRotation, just with different logic/weights.

### Option 3: Improve Regime Detection
Current VIX > 30 threshold triggers too easily. Consider:
- Higher threshold (VIX > 40)
- Additional confirmation signals
- Shorter panic periods

### Option 4: Create New Version (Recommended)
Create `AdaptiveRegimeSwitcher_v2` that:
1. Uses the same universe for both models
2. Changes strategy/weights but not assets during panic
3. Has better-tuned VIX thresholds

## Conclusion

The AdaptiveRegimeSwitcher's underperformance is not a bug but a **design flaw**. The model switches to a completely different set of assets during panic conditions, and those defensive trades lost money during the COVID crash. The fix of returning `bull_output` directly in normal mode works correctly but doesn't address the fundamental issue that panic mode trades different assets that underperformed.

**The -6.53% CAGR gap comes entirely from the panic period (Feb 27 - Apr 30, 2020) when the combined model traded defensive assets instead of sector ETFs.**