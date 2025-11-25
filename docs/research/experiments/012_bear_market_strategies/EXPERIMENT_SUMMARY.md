# Experiment 012: Bear Market Defensive Strategies

**Date**: November 24-25, 2025  
**Status**: ✅ COMPLETED  
**Outcome**: Key insights discovered, BearDefensiveRotation_v2 developed

---

## Executive Summary

**Goal**: Develop bear-market-specific models to complement existing bull market strategies.

**Key Finding**: Recovery timing is MORE important than loss limitation. Models that "safely" lose -5% but miss every 30% recovery underperform dramatically.

**Best Model**: BearDefensiveRotation_v3 (after bug fix)
- 2018: -14.90% (improved from v1: -21.70%)
- 2020: +12.79% profit (captured V-recovery, +123% better than V2)
- 2022: -5.70% (nearly equal to V2's -5.23%)
- **Bug Fixed**: Removed daily volatility adjustments that caused overtrading (548 → 122 trades)

---

## Research Phases

### Phase 1: Initial Model Screening (2022 Only)

Tested 3 architectures on 2022 bear market (SPY -18%):

| Model | Strategy | CAGR | Result |
|-------|----------|------|--------|
| BearDefensiveRotation_v1 | Rotate defensive assets | -18.78% | ❌ FAIL |
| **BearCorrelationGated_v1** | **Correlation-based gating** | **-5.32%** | ✅ **PASS** |
| BearMultiAsset_v1 | Multi-asset rotation | -22.74% | ❌ FAIL |

**Outcome**: Only 1 of 3 passed initial screening.

---

### Phase 1b: Model Improvements

Fixed failing models based on analyst recommendations:

**BearDefensiveRotation_v2**:
- Added SHY (cash) to competitive universe
- Faster momentum (20 days)
- Cash threshold for full defensive mode
- Result: -5.23% (improved by +13.55%!) ✅

**BearMultiAsset_v2**:
- Switched to relative momentum
- Removed absolute threshold
- Result: -14.01% (improved by +8.73%) ⚠️

**Outcome**: V2 improvements dramatically helped Defensive model.

---

### Phase 2: Multi-Year Validation

Tested top 2 models across 3 different bear market types:

| Period | Type | SPY | Defensive V2 | Correlation V1 | Winner |
|--------|------|-----|--------------|----------------|--------|
| **2022** | Grind | -18% | **-5.23%** | -5.32% | Defensive ✅ |
| **2020** | Panic | -34% | **+5.74%** | -5.71% | Defensive ✅ |
| **2018** | Choppy | -14% | -21.70% | **-8.35%** | Correlation ✅ |

**Critical Discovery**: Defensive V2 made PROFIT (+5.74%) in 2020 by capturing the recovery. Correlation V1 stayed defensive too long and missed the +30% rebound.

**Key Insight**: Recovery capture > Loss limitation

---

### Phase 2b (Experiment 012b): Feature Testing

Tested additional features to improve robustness:

#### V3: Risk Management Features
- Volatility-based position sizing
- Drawdown circuit breaker (-10%)
- **BUG FIXED** (Nov 25, 2025): Removed daily volatility adjustments between rebalances
- **Results After Fix**: Best overall performance across all periods!

| Period | V2 | V3 (Fixed) | Improvement | Trades |
|--------|----|----|-------------|--------|
| 2018 | -21.70% | -14.90% | +31% ✅ | 122 |
| 2020 | +5.74% | +12.79% | +123% ✅✅ | 122 |
| 2022 | -5.23% | -5.70% | -9% ⚠️ | 122 |
| **Avg** | **-7.06%** | **-2.60%** | **+63%** | **122/yr** |

**Critical Bug That Was Fixed**:
- **Problem**: V3 was applying volatility scaling DAILY between rebalances
- **Symptom**: 548 trades in 2022 (should be ~36 rebalances)
- **Root Cause**: Lines 220-236 scaled positions every day instead of holding
- **Fix**: Changed to `hold_current=True` - only rebalance every 10 days as intended
- **Impact**: 548 → 122 trades/year (78% reduction), +41% to +48% better performance

#### V5: Quality Filters
- Trend strength filter
- Correlation-adjusted sizing
- **Results**: Excellent 2018, terrible elsewhere

| Period | V2 | V5 | Result |
|--------|----|----|--------|
| 2018 | -21.70% | **+6.21%** | Profit! ✅✅ |
| 2020 | +5.74% | -8.68% | Killed recovery ❌ |
| 2022 | -5.23% | -18.72% | Terrible ❌❌ |

**Conclusion**: After fixing the overtrading bug, V3 is now the best overall performer (+63% better average CAGR than V2). The risk management features (volatility scaling, circuit breaker) provide meaningful value when applied correctly (only at rebalance time, not daily).

---

## Key Learnings

### 1. Bear Markets Are Not Monolithic
- **Panic crashes (2020)**: Need aggression to capture V-recovery
- **Choppy bears (2018)**: Need quality filters to avoid whipsaws
- **Grinding bears (2022)**: Need simplicity, avoid overtrading

### 2. Recovery Timing > Loss Limitation
- Model that loses -5% but misses recoveries = bad long-term
- Model that captures +30% rebounds = valuable even with volatility

### 3. Risk Management Features Work When Applied Correctly
- **Original belief**: V3's risk features hurt performance (548 trades, worse results)
- **Discovery**: Bug was applying features DAILY instead of at rebalance intervals
- **After fix**: V3 outperforms V2 by +63% average CAGR
- **Key insight**: Volatility scaling and circuit breakers are valuable, but timing matters

### 4. Model Specialization Works
- Single "universal" bear model is elusive
- Better approach: Specialized models for different regimes
- Need handoff logic between regime specialists

---

## Models Developed

### Production Ready
1. **BearDefensiveRotation_v3** (RECOMMENDED - Bug Fixed Nov 25, 2025)
   - File: `models/bear_defensive_rotation_v3.py`
   - Profile: `exp012b_v3_2022` (and 2020, 2018 variants)
   - **Best overall**: +63% better average CAGR than V2
   - Features: Volatility scaling, circuit breaker, momentum rotation
   - 2020: +12.79% (captured recovery), 2022: -5.70% (controlled loss), 2018: -14.90%
   - 122 trades/year (proper rebalancing cadence)

2. **BearDefensiveRotation_v2**
   - File: `models/bear_defensive_rotation_v2.py`
   - Profile: `exp012_defensive_v2_2022` (and 2020, 2018 variants)
   - Good for: Simplicity, interpretability
   - Weakness: Catastrophic in choppy markets (-21.70% in 2018)
   - 2020: +5.74%, 2022: -5.23%, 2018: -21.70%

3. **BearCorrelationGated_v1**
   - File: `models/bear_correlation_gated_v1.py`
   - Profile: `exp012_correlation_2022` (and 2020, 2018 variants)
   - Best for: Consistent loss limitation
   - Weakness: Misses recoveries (stayed cash too long in 2020)

### Experimental
4. **BearDefensiveRotation_v5** (Quality Filters - inconsistent across periods)

---

## Recommendations

### For Production
**Deploy**: BearDefensiveRotation_v3 (Bug-Fixed Version)
- **Best average performance**: -2.60% CAGR across all bear types (vs V2: -7.06%)
- **Excellent recovery capture**: +12.79% in 2020 COVID crash
- **Controlled losses**: -5.70% in 2022 grinding bear
- **Proper trade frequency**: 122 trades/year (10-day rebalancing)
- Risk management features (volatility scaling, circuit breaker) now working correctly

**Alternative**: BearDefensiveRotation_v2 for simplicity if interpretability is critical

### For Future Research
**Next Experiment**: Build specialized "buy-the-dip" model (Experiment 013)
- Optimize for PROFIT in bear markets (not just loss limitation)
- Target panic crashes specifically (VIX spikes, oversold conditions)
- See: `docs/research/experiments/013_beardipbuyer/` (in progress)

---

## Files and Artifacts

### Models
- `models/bear_defensive_rotation_v1.py` (original)
- `models/bear_defensive_rotation_v2.py` (improved - BEST)
- `models/bear_defensive_rotation_v3.py` (risk mgmt features)
- `models/bear_defensive_rotation_v5.py` (quality filters)
- `models/bear_correlation_gated_v1.py`
- `models/bear_multi_asset_v1.py`
- `models/bear_multi_asset_v2.py`

### Profiles
- All test profiles: `configs/profiles.yaml` (search "exp012")

### Documentation
- Main README: `docs/research/experiments/012_bear_market_strategies/README.md`
- Feature testing: `docs/research/experiments/012_bear_market_strategies/feature_testing/`
- Case studies referenced:
  - `docs/research/case_studies/001_ea_overfitting_disaster.md`
  - `docs/research/case_studies/CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md`

### Analysis Reports
- `docs/research/reports/2025-11-25_bear_market_recovery_timing_analysis.md`
- `docs/research/reports/2025-11-25_exp012b_feature_testing_analysis.md`

---

## Reproducibility

All results are reproducible via profiles:

```bash
# Phase 1
python3 -m backtest.analyze_cli --profile exp012_defensive_2022
python3 -m backtest.analyze_cli --profile exp012_correlation_2022

# Phase 1b (V2 improvements)
python3 -m backtest.analyze_cli --profile exp012_defensive_v2_2022

# Phase 2 (Multi-year)
python3 -m backtest.analyze_cli --profile exp012_defensive_v2_2020
python3 -m backtest.analyze_cli --profile exp012_defensive_v2_2018

# Phase 2b (Feature testing)
python3 -m backtest.analyze_cli --profile exp012b_v3_2022
python3 -m backtest.analyze_cli --profile exp012b_v5_2018
```

---

## Update Log

### November 25, 2025 (Bug Fix)
**Critical Bug Fixed in BearDefensiveRotation_v3**:
- **Issue**: Daily volatility adjustments between rebalances caused 548 trades/year
- **Location**: Lines 214-227 in `models/bear_defensive_rotation_v3.py`
- **Fix**: Changed `hold_current=False` to `hold_current=True`, removed daily scaling
- **Impact**:
  - Trades: 548 → 122/year (78% reduction)
  - 2020 CAGR: +9.10% → +12.79% (+41% improvement)
  - 2022 CAGR: -11.03% → -5.70% (+48% improvement)
  - Average CAGR: -5.24% → -2.60% (+63% improvement)
- **Status**: V3 now RECOMMENDED for production over V2

---

*Experiment completed: November 24, 2025*
*Bug fix applied: November 25, 2025*
*Next: Experiment 013 - BearDipBuyer (opportunistic bear market profits)*
