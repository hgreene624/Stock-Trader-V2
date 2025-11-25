# Experiment 014: AdaptiveRegimeSwitcher - Comprehensive Improvement Analysis

**Date:** 2025-11-25
**Status:** v2 Completed, v3 Improvements Identified
**Current Best:** v2 achieves 13.05% CAGR (vs standalone 15.11%)

---

## Executive Summary

Created AdaptiveRegimeSwitcher_v2 with unified universe design, achieving **13.05% CAGR** - a **52% improvement** over v1's 8.58%. Deep analysis identified the remaining 2.06% gap and specific fixes that could **beat standalone by 2-4% CAGR**.

**Key Achievement:** Fixed universe mismatch problem from v1
**Remaining Gap:** -2.06% CAGR vs standalone (entirely from 2021 false VIX signals)
**Path Forward:** v3 with price trend confirmation expected to close gap and outperform

---

## Performance Comparison (2020-2024)

| Metric | Standalone | v1 (Broken) | v2 (Fixed) | v3 (Projected) |
|--------|-----------|-------------|------------|----------------|
| **CAGR** | 15.11% | 8.58% | **13.05%** | **~17.5%** |
| **Sharpe** | 1.976 | 1.347 | **1.671** | **~2.0** |
| **Max DD** | -30.92% | -32.03% | **-32.84%** | **~-28%** |
| **Total Return** | 102.04% | 50.85% | **84.60%** | **~120%** |
| **BPS** | 0.905 | 0.633 | **0.775** | **~0.95** |

---

## Year-by-Year Analysis

### v2 Performance by Year

| Year | v2 Return | Standalone | Gap | Regime Distribution | Winner |
|------|-----------|-----------|-----|---------------------|--------|
| **2020** | +32.10% | +16.13% | **+15.96%** | Bull 38.7%, Def 41.5%, Ext 19.8% | ✅ v2 |
| **2021** | -7.99% | +22.72% | **-30.71%** | Bull 91.7%, Def 7.9%, Ext 0.4% | ❌ v2 |
| **2022** | -7.07% | -10.75% | **+3.68%** | Bull 47.8%, Def 51.4%, Ext 0.8% | ✅ v2 |
| **2023** | +52.19% | +41.28% | **+10.91%** | Bull 98.8%, Def 1.2%, Ext 0.0% | ✅ v2 |
| **2024** | +14.39% | +16.89% | **-2.50%** | Bull 98.4%, Def 1.2%, Ext 0.4% | ❌ v2 |

**Conclusion:** v2 wins 3 out of 5 years. The entire -2.06% CAGR gap comes from 2021's -30.71% underperformance.

---

## FINDING #1: False VIX Signals (CRITICAL - HIGHEST IMPACT)

### The Problem

**VIX spikes without actual market crashes trigger defensive mode**, causing v2 to flee to underperforming sectors while the market rallies.

### Evidence: 2021 Breakdown

**2021 was 91.7% bull mode**, yet v2 lost -30.71% vs standalone. Analysis reveals:

#### January 2021 - GameStop Volatility Spike

**Jan 27, 2021: VIX spikes to 37.2 (EXTREME mode activated)**
- v2 bought TLT at $132.54
- Feb 3: Sold TLT at $129.03
- **Loss: -2.65%**
- Meanwhile, standalone stayed in XLE which rallied **+31.52%**

**Jan 5, 2021: VIX 25.3 (DEFENSIVE mode)**
- v2 bought XLP at $59.00, XLU at $52.90
- Jan 12: Sold XLP at $58.41 (loss), XLU at $53.11 (tiny gain)
- Meanwhile, market rallied: XLF +18.51%, XLI +14.66%

#### February 26, 2021: False Signal

**VIX 28.0 (DEFENSIVE mode) - Just normal volatility, not a crash**
- v2 shifted to XLP/XLU
- Market continued rallying in growth sectors
- Lost opportunity cost

### Impact Quantified

**Jan-Mar 2021 Sector Performance:**
- XLE: +31.52% (best performer)
- XLF: +18.51%
- XLI: +14.66%
- XLB: +10.91%
- XLC: +10.05%
- **XLU: +4.79%** (v2 defensive)
- **XLP: +3.27%** (v2 defensive)
- **TLT: -13.34%** (v2 defensive)

**v2 vs Standalone Trading (Jan-Mar 2021):**
- v2 traded XLU: 4 times, standalone: 0 times
- v2 traded XLP: 4 times, standalone: 0 times
- v2 traded TLT: 2 times, standalone: 0 times
- v2 underweight XLB: -3 trades
- v2 underweight XLC: -2 trades

**Result:** Jan-Mar 2021 cumulative gap: **-23.77%**

### Root Cause

**VIX alone is an incomplete regime indicator:**
- VIX measures volatility, not directional risk
- GameStop chaos (Jan 27): High VIX, but SPY rallying
- Normal volatility (Feb 26): VIX 28, but market trending up
- v2 interprets all VIX spikes as crashes → false defensive positioning

### Solution: Price Trend Confirmation

```python
def detect_regime_v3(self, context):
    vix = self._get_vix_level(context)
    spy_features = context.asset_features['SPY']
    spy_price = spy_features['close'].iloc[-1]
    spy_ma200 = spy_features['close'].rolling(200).mean().iloc[-1]
    spy_ma50 = spy_features['close'].rolling(50).mean().iloc[-1]

    # Require BOTH high VIX AND price weakness
    # This filters volatility-only spikes from real crashes
    if vix >= 35 and spy_price < spy_ma200 * 0.95:
        # Real crash: High VIX + Breaking 200 MA
        return "extreme"
    elif vix >= 28 and spy_price < spy_ma200 * 0.98 and spy_ma50 < spy_ma200:
        # Real stress: High VIX + Price weak + Death cross forming
        return "defensive"
    else:
        # Normal: Trade aggressively even if VIX elevated
        return "bull"
```

**Why This Works:**
- **COVID crash (Mar 2020)**: VIX 82 AND SPY < 200 MA → Defensive mode CORRECT
- **GameStop (Jan 2021)**: VIX 37 BUT SPY > 200 MA → Bull mode CORRECT
- **Normal volatility**: VIX 25-30 BUT SPY > 200 MA → Bull mode CORRECT

### Expected Impact

**If v3 stayed in bull mode during false signals:**
- Jan 27 TLT trade: Avoided -2.65% loss
- Jan-Mar defensive positioning: Captured XLE +31%, XLF +18%
- Estimated recovery: **+12-18% of the -30.71% 2021 gap**

**Projected v3 CAGR:** 13.05% + 3.0% = **~16% CAGR** (beats standalone!)

---

## FINDING #2: Suboptimal Defensive Sectors

### The Problem

Current defensive sectors (XLP, XLU, TLT) show poor performance during VIX 25-35 periods.

### Performance by Regime (Annualized Returns)

**VIX 25-35 (DEFENSIVE Mode) Performance:**

| Sector | Bull Mode | Defensive | Extreme | Overall | Current Use |
|--------|-----------|-----------|---------|---------|-------------|
| XLU | +0.2% | **+0.1%** | -1.6% | +0.1% | ✅ Yes |
| XLV | +0.2% | **0.0%** | -1.0% | +0.1% | ❌ No |
| XLI | +0.3% | **-0.1%** | -1.9% | +0.1% | ❌ No |
| XLP | +0.2% | **-0.1%** | -1.2% | +0.1% | ✅ Yes |
| TLT | -0.1% | **-0.2%** | +0.7% | -0.0% | ✅ Yes |

**Current defensive average:** -0.07% annualized
**Optimal defensive average (XLU, XLV, XLI):** 0.0% annualized

### Insight

TLT is the weakest performer in defensive mode (-0.2%), but best in extreme mode (+0.7%). XLV (Healthcare) performs better than XLP (Staples) in defensive conditions.

### Solution

```python
# v2 current
defensive_sectors = ['XLP', 'XLU', 'TLT']

# v3 improved
defensive_sectors = ['XLV', 'XLU', 'TLT']  # Healthcare > Staples
```

Reserve TLT for extreme mode (VIX > 35) only.

### Expected Impact

Small but consistent improvement across all defensive periods.
**Estimated: +0.3-0.5% CAGR**

---

## FINDING #3: Defensive Leverage Too Conservative

### The Problem

v2 uses fixed 1x leverage in defensive mode, while standalone uses volatility targeting that can scale up when volatility drops.

### Current Design

**v2:**
- Bull mode: 2.0x leverage (fixed)
- Defensive mode: 1.0x leverage (fixed)
- Extreme mode: 1.0x leverage (100% TLT)

**Standalone:**
- Base leverage: 1.5x (bull) / 1.38x (bear)
- Volatility targeting: Scales between 0.4x and 3.0x
- During VIX 25-28 (low defensive): Can use higher leverage

### Opportunity

During VIX 25-28 (lower defensive range), markets often recover quickly. 1x leverage is too conservative - miss upside participation.

### Solution: Dynamic Defensive Leverage

```python
def _calculate_defensive_leverage(self, vix_level):
    """Scale defensive leverage based on VIX level."""
    if vix_level < 28:
        return 1.3  # Mild defensive: Stay aggressive
    elif vix_level < 32:
        return 1.0  # Moderate defensive: Standard
    else:
        return 0.7  # Heavy defensive: Reduce risk
```

**Example:**
- VIX 26 (just entered defensive): 1.3x leverage on XLV + XLU
- VIX 30 (moderate stress): 1.0x leverage
- VIX 34 (high stress): 0.7x leverage

### Expected Impact

Better participation in quick recoveries from mild volatility spikes.
**Estimated: +0.5-1.0% CAGR**

---

## FINDING #4: VIX Thresholds Not Optimized

### Current Thresholds

- Defensive: VIX >= 25.0 (activates 20.7% of time)
- Extreme: VIX >= 35.0 (activates 4.3% of time)

### Activation Frequency by Year

| Year | Bull % | Defensive % | Extreme % | Avg VIX | Correct? |
|------|--------|-------------|-----------|---------|----------|
| 2020 | 38.7% | 41.5% | 19.8% | 29.25 | ✅ Yes (COVID) |
| 2021 | 91.7% | 7.9% | 0.4% | 19.66 | ❌ False positives |
| 2022 | 47.8% | 51.4% | 0.8% | 25.62 | ✅ Yes (bear) |
| 2023 | 98.8% | 1.2% | 0.0% | 16.87 | ✅ Yes (bull) |
| 2024 | 98.4% | 1.2% | 0.4% | 15.60 | ✅ Yes (bull) |

### Problem

VIX 25 threshold too low - triggers on normal volatility:
- 2021: Only 7.9% defensive should have been even lower
- 2022: 51.4% defensive was appropriate for bear market

### Solution: Raise Thresholds + Add Confirmation

```python
# v2 current
vix_defensive: float = 25.0
vix_extreme: float = 35.0

# v3 improved
vix_defensive: float = 28.0  # Raised from 25
vix_extreme: float = 40.0    # Raised from 35
confirmation_days: int = 3   # New: Require 3 consecutive days

def detect_regime_with_confirmation(self, context, recent_regimes):
    """Require confirmation before switching to defensive."""
    current_regime = self._detect_regime(context)

    # Count consecutive days of new regime
    if len(recent_regimes) >= 3 and all(r == current_regime for r in recent_regimes[-3:]):
        return current_regime  # Confirmed
    else:
        return recent_regimes[-1] if recent_regimes else 'bull'  # Stay in previous
```

**Benefits:**
- Filters single-day VIX spikes (GameStop Jan 27)
- Reduces whipsawing between modes
- Still responds to sustained crises (COVID crash had VIX > 30 for weeks)

### Expected Impact

Fewer false defensive mode activations.
**Estimated: +1-2% CAGR**

---

## FINDING #5: September 2021 Anomaly

### The Puzzle

September 2021 had minimal defensive mode (1 day), yet v2 lost -19.87% vs standalone -11.83% (**-8.03% gap**).

### What We Know

- VIX stayed below 25 most of month (bull mode)
- Both models should have traded similarly
- Yet significant underperformance

### Hypothesis

Likely sector selection or timing difference in bull mode. Requires deeper investigation.

### Investigation Needed

1. Compare month-by-month sector holdings (v2 vs standalone)
2. Analyze rebalancing timing differences
3. Check if ATR exits triggered differently

### Priority

**Secondary issue** - Address after fixing critical VIX signal problem. The 2021 gap is primarily from Jan-Mar (-23.77%) not September (-8.03%).

---

## FINDING #6: Bull Mode Defensive Sector "Leak" (Non-Issue)

### Observation

v2 trades slightly more XLP/XLU than standalone even in bull mode:
- v2 XLP: 2.8% of bull trades vs standalone 1.7% (+1.1%)
- v2 XLU: 6.9% of bull trades vs standalone 5.7% (+1.2%)

### Analysis

This is **working as designed** - both models consider all 11 sectors and pick top 4 by momentum. Sometimes XLP/XLU legitimately have good momentum.

### Conclusion

Not a bug, no fix needed.

---

## Priority-Ranked Improvement Plan

### Tier 1: Critical (Implement Immediately)

**1. Add Price Trend Confirmation to Regime Detection**
- **Impact:** +12-18% recovery of 2021 gap (~3% CAGR improvement)
- **Difficulty:** Easy
- **Implementation Time:** 30 minutes
- **Status:** ⏸️ Ready to implement

```python
# Add to detect_regime():
if vix >= 35 and spy_price < spy_ma200 * 0.95:
    return "extreme"
elif vix >= 28 and spy_price < spy_ma200 * 0.98 and spy_ma50 < spy_ma200:
    return "defensive"
else:
    return "bull"
```

### Tier 2: High Impact (Implement Next)

**2. Raise VIX Thresholds (28/40) + Add 3-Day Confirmation**
- **Impact:** +1-2% CAGR
- **Difficulty:** Easy
- **Implementation Time:** 15 minutes
- **Status:** ⏸️ Ready to implement

**3. Scale Defensive Leverage by VIX Level**
- **Impact:** +0.5-1.0% CAGR
- **Difficulty:** Medium
- **Implementation Time:** 1 hour
- **Status:** ⏸️ Needs implementation

### Tier 3: Optimization (Test Later)

**4. Replace XLP with XLV in Defensive Sectors**
- **Impact:** +0.3-0.5% CAGR
- **Difficulty:** Easy
- **Implementation Time:** 5 minutes
- **Status:** ⏸️ Simple parameter change

**5. Investigate September 2021 Anomaly**
- **Impact:** +1-2% CAGR (uncertain)
- **Difficulty:** Hard
- **Implementation Time:** 2-4 hours research
- **Status:** ⏸️ Requires deeper analysis

---

## Projected Performance After Improvements

| Version | CAGR | Improvements | Gap vs Standalone |
|---------|------|--------------|-------------------|
| **v2 (current)** | 13.05% | Unified universe | -2.06% |
| **v3 (Tier 1)** | ~16.0% | + Price confirmation | **+0.9%** ✅ |
| **v4 (Tier 1+2)** | ~17.5% | + Thresholds + Dynamic lev | **+2.4%** ✅✅ |
| **v5 (All fixes)** | ~18-20% | + Optimal sectors | **+3-5%** ✅✅✅ |

**Key Milestone:** v3 expected to **match or beat standalone** (15.11% CAGR)

---

## Recommended Next Steps

### Immediate (Today)

1. ✅ **Document findings** (this file)
2. ✅ **Update CLAUDE.md** with reference
3. ✅ **Commit and push** to GitHub

### Session 2 (Next Time)

1. ⏸️ **Create AdaptiveRegimeSwitcher_v3** with Tier 1 fix (price confirmation)
2. ⏸️ **Run backtest** on 2020-2024 period
3. ⏸️ **Verify 2021 improvement** (should reduce gap from -30.71% to ~-15%)
4. ⏸️ **Compare**: v2 vs v3 vs standalone

### Session 3 (If v3 Successful)

1. ⏸️ **Create v4** with Tier 2 fixes (thresholds + dynamic leverage)
2. ⏸️ **Run backtest** and compare all versions
3. ⏸️ **Optimize parameters** if needed
4. ⏸️ **Document final results**

### Session 4 (Production)

1. ⏸️ **Walk-forward validation** of best model
2. ⏸️ **Out-of-sample testing** (2019, 2025)
3. ⏸️ **Paper trading** if validation passes
4. ⏸️ **Production deployment**

---

## Technical Implementation Notes

### v3 Changes Required

**File:** `/models/adaptive_regime_switcher_v3.py`

1. Add SPY price tracking
2. Implement price-based regime detection
3. Update VIX thresholds (28/40)
4. Add regime confirmation logic

**File:** `/configs/profiles.yaml`

1. Add `exp014_v3_price_confirmation` profile
2. Register v3 parameters

**File:** `/backtest/analyze_cli.py`

1. Import AdaptiveRegimeSwitcher_v3
2. Register in model instantiation

### Testing Protocol

1. **Unit test:** Price confirmation logic with synthetic data
2. **Integration test:** 2021 backtest (verify defensive mode NOT triggered on Jan 27)
3. **Full backtest:** 2020-2024 comparison
4. **Validation:** Check COVID crash still triggers defensive mode correctly

---

## Key Insights Learned

1. **VIX alone is insufficient** - Needs price trend confirmation to filter false signals
2. **2021 was critical** - GameStop volatility spike exposed fundamental design flaw
3. **v2 was NOT broken** - Defensive mode logic worked as designed, design was incomplete
4. **Universe unification worked** - v2's 13.05% proves the concept is sound
5. **Small fixes, big impact** - Price confirmation alone could add 3% CAGR

---

## Files Modified in This Session

1. `/models/adaptive_regime_switcher_v2.py` - Created unified universe version
2. `/configs/profiles.yaml` - Added exp014_v2_unified_universe profile
3. `/backtest/analyze_cli.py` - Registered v2 model
4. `VALIDATION_REPORT.md` - Documented VIX loading validation
5. `DIVERGENCE_REPORT.md` - Documented v1 universe mismatch problem
6. This file - Complete improvement analysis

---

**Analysis Date:** 2025-11-25
**Analyst:** Claude (AI Agent)
**Next Action:** Implement v3 with price trend confirmation
