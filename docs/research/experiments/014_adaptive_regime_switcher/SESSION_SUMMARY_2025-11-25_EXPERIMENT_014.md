# Session Summary: 2025-11-25 - Experiment 014 Deep Analysis

## What Was Accomplished

### 1. Created AdaptiveRegimeSwitcher_v2
- **Fixed universe mismatch** from v1 (different assets in bull vs panic mode)
- **Unified universe design**: All modes trade same sector ETFs
- **Result**: 13.05% CAGR (52% improvement over v1's 8.58%)

### 2. Comprehensive Performance Analysis
- Analyzed 5-year performance (2020-2024)
- Year-by-year breakdown identifying 2021 as problem year
- v2 wins 3 out of 5 years, loses 2 years

### 3. Root Cause Analysis: False VIX Signals
**The entire 2.06% CAGR gap comes from 2021's -30.71% underperformance**

**Identified specific false signals:**
- Jan 27, 2021: VIX 37.2 (GameStop) → v2 bought TLT, lost -2.65%
- Jan-Mar 2021: v2 held defensive sectors while market rallied
- Impact: -23.77% cumulative gap in just 3 months

**Root cause:** VIX alone measures volatility, not directional risk
- GameStop chaos: High VIX but SPY rallying
- v2 interprets all VIX spikes as crashes → false defensive positioning

### 4. Identified 6 Improvement Opportunities
1. **Add price trend confirmation** (Critical - +3% CAGR)
2. **Raise VIX thresholds + confirmation** (+1-2% CAGR)
3. **Dynamic defensive leverage** (+0.5-1% CAGR)
4. **Optimize defensive sectors** (+0.3-0.5% CAGR)
5. **September 2021 investigation** (+1-2% CAGR, uncertain)
6. **Bull mode defensive leak** (non-issue)

### 5. Projected v3 Performance
- **v2 current**: 13.05% CAGR
- **v3 with price confirmation**: ~16% CAGR (beats standalone!)
- **v4 with all Tier 1+2 fixes**: ~17.5% CAGR
- **v5 fully optimized**: 18-20% CAGR

## Key Files Created/Modified

### New Files
1. `/docs/research/experiments/014_adaptive_regime_switcher/IMPROVEMENT_ANALYSIS.md`
   - Complete analysis of all findings
   - Priority-ranked improvement plan
   - Implementation details for v3

2. `/models/adaptive_regime_switcher_v2.py`
   - Unified universe implementation
   - Bull/defensive/extreme modes
   - Preserves state across regime changes

3. `/configs/profiles.yaml` (added profile)
   - `exp014_v2_unified_universe`

### Modified Files
1. `/CLAUDE.md`
   - Updated "Best Model So Far" section
   - Added reference to Experiment 014 analysis

2. `/backtest/analyze_cli.py`
   - Registered AdaptiveRegimeSwitcher_v2

## What to Do Next

### Immediate Next Session

1. **Create AdaptiveRegimeSwitcher_v3**
   - Implement price trend confirmation logic
   - Add SPY 200 MA and 50 MA tracking
   - Update regime detection function

2. **Run Backtest**
   - Test on 2020-2024 period
   - Verify 2021 improvement (should reduce gap)
   - Compare v2 vs v3 vs standalone

3. **Validate Fix**
   - Jan 27, 2021: Should stay in bull mode (not buy TLT)
   - COVID crash: Should still trigger defensive mode
   - 2021 gap should reduce from -30.71% to ~-15%

### If v3 Successful

4. **Create v4** with Tier 2 improvements
   - Raise VIX thresholds (28/40)
   - Add 3-day confirmation
   - Dynamic defensive leverage

5. **Optimize and validate**
   - Walk-forward validation
   - Out-of-sample testing
   - Paper trading if validated

## Key Insights

1. **VIX alone is insufficient** for regime detection
2. **False signals cost more than missed signals** (2021 proved this)
3. **Small fixes, big impact**: Price confirmation could add 3% CAGR
4. **v2 design is sound**: Problem is incomplete regime logic, not architecture
5. **2021 was an anomaly**: GameStop created unique volatility pattern

## Current Status

- ✅ v2 created and tested (13.05% CAGR)
- ✅ Root cause identified (false VIX signals)
- ✅ Solution designed (price trend confirmation)
- ✅ Full analysis documented
- ⏸️ v3 implementation ready to begin
- ⏸️ Expected to beat standalone (15.11% CAGR)

## Performance Summary

| Model | CAGR | vs SPY | vs Standalone | Status |
|-------|------|--------|---------------|--------|
| SPY Baseline | 14.34% | - | -0.77% | Benchmark |
| Standalone v3 | 15.11% | +0.77% | - | Current best |
| v1 (broken) | 8.58% | -5.76% | -6.53% | ❌ Deprecated |
| **v2 (current)** | **13.05%** | **-1.29%** | **-2.06%** | ✅ Working |
| v3 (projected) | ~16.0% | +1.7% | **+0.9%** | ⏸️ Ready |
| v4 (projected) | ~17.5% | +3.2% | **+2.4%** | ⏸️ Design |

---

**Next Command to Run:**
```bash
# Create v3 model file
cp models/adaptive_regime_switcher_v2.py models/adaptive_regime_switcher_v3.py

# Then implement price trend confirmation in _detect_regime()
```

**Documentation Location:**
- Full analysis: `docs/research/experiments/014_adaptive_regime_switcher/IMPROVEMENT_ANALYSIS.md`
- Updated: `CLAUDE.md` (lines 15-18, 665)
