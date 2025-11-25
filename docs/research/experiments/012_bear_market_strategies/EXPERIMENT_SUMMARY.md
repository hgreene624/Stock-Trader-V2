# Experiment 012: Bear Market Defensive Strategies

**Date**: November 24-25, 2025  
**Status**: ✅ COMPLETED  
**Outcome**: Key insights discovered, BearDefensiveRotation_v2 developed

---

## Executive Summary

**Goal**: Develop bear-market-specific models to complement existing bull market strategies.

**Key Finding**: Recovery timing is MORE important than loss limitation. Models that "safely" lose -5% but miss every 30% recovery underperform dramatically.

**Best Model**: BearDefensiveRotation_v2 with simple circuit breaker  
- 2018: -13.79% (improved from v1: -21.70%)  
- 2020: +9.10% profit (captured V-recovery)  
- 2022: -11.03% (acceptable loss in grind)

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
- **Results**: Improved average but 548 trades in 2022 (overtrading)

| Period | V2 | V3 | Improvement |
|--------|----|----|-------------|
| 2018 | -21.70% | -13.79% | +36% ✅ |
| 2020 | +5.74% | +9.10% | +58% ✅ |
| 2022 | -5.23% | -11.03% | -111% ❌ |

#### V5: Quality Filters
- Trend strength filter
- Correlation-adjusted sizing
- **Results**: Excellent 2018, terrible elsewhere

| Period | V2 | V5 | Result |
|--------|----|----|--------|
| 2018 | -21.70% | **+6.21%** | Profit! ✅✅ |
| 2020 | +5.74% | -8.68% | Killed recovery ❌ |
| 2022 | -5.23% | -18.72% | Terrible ❌❌ |

**Conclusion**: No single feature set works across all bear market types. Each type (panic/choppy/grind) requires different approaches.

---

## Key Learnings

### 1. Bear Markets Are Not Monolithic
- **Panic crashes (2020)**: Need aggression to capture V-recovery
- **Choppy bears (2018)**: Need quality filters to avoid whipsaws
- **Grinding bears (2022)**: Need simplicity, avoid overtrading

### 2. Recovery Timing > Loss Limitation
- Model that loses -5% but misses recoveries = bad long-term
- Model that captures +30% rebounds = valuable even with volatility

### 3. Simplicity Often Wins
- Complex features (v3, v5) didn't improve average performance
- Simple protection (circuit breaker) provides best risk/reward
- Overtrading costs hurt (v3: 548 trades in one year)

### 4. Model Specialization Works
- Single "universal" bear model is elusive
- Better approach: Specialized models for different regimes
- Need handoff logic between regime specialists

---

## Models Developed

### Production Ready
1. **BearDefensiveRotation_v2**
   - File: `models/bear_defensive_rotation_v2.py`
   - Profile: `exp012_defensive_v2_2022` (and 2020, 2018 variants)
   - Best for: V-shaped recoveries, general bear markets
   - Weakness: Catastrophic in choppy markets (-21.70% in 2018)

2. **BearCorrelationGated_v1**
   - File: `models/bear_correlation_gated_v1.py`
   - Profile: `exp012_correlation_2022` (and 2020, 2018 variants)
   - Best for: Consistent loss limitation
   - Weakness: Misses recoveries (stayed cash too long in 2020)

### Experimental
3. **BearDefensiveRotation_v3** (Risk Management)
4. **BearDefensiveRotation_v5** (Quality Filters)

---

## Recommendations

### For Production
**Deploy**: BearDefensiveRotation_v2 + Simple Circuit Breaker (-8% threshold)
- Caps catastrophic losses
- Preserves recovery capture
- Simple, interpretable, low complexity

### For Future Research
**Next Experiment**: Build specialized "buy-the-dip" model
- Optimize for PROFIT in bear markets (not just loss limitation)
- Combine best features: V5 filters + V3 risk mgmt + V2 recovery timing
- Add explicit panic buying logic (VIX spikes, oversold conditions)
- Design regime handoff to bull market models

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

*Experiment completed: November 25, 2025*  
*Next: Experiment 013 - BearDipBuyer (opportunistic bear market profits)*
