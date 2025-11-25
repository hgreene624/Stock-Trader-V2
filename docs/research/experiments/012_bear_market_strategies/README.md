# Experiment 012: Bear Market Defensive Strategies

**Date**: November 24, 2025
**Status**: Phase 1 Complete - BearCorrelationGated_v1 Advances
**Objective**: Design and test bear-market-specific model architectures that can protect capital during market downturns

## Executive Summary

Current sector rotation momentum models fail catastrophically in bear markets (-17.58% in 2025 YTD for SectorRotationAdaptive_v3). This experiment designs three distinct bear market strategies that fundamentally differ from momentum approaches.

**Phase 1 Results**: BearCorrelationGated_v1 successfully limited losses to -5.32% vs SPY's -18% in 2022, achieving 70% downside protection. Two other models failed.

## Problem Statement

From Experiments 010 & 011 and Case Studies:
- **Momentum fails when all sectors fall together** (2022: all sectors -30% to -40%)
- **Removing leverage makes it worse** (232% degradation vs 185% with leverage)
- **Regime detection insufficient** - only changes parameters, not strategy
- **Need fundamentally different approach** for bear markets

## Proposed Architectures

### 1. BearDefensiveRotation_v1
**Strategy**: Rotate to defensive assets by "least bad" momentum
- **Universe**: XLU (Utilities), XLP (Staples), TLT (Bonds), GLD (Gold), UUP (Dollar)
- **Logic**: Find which defensive asset is falling least (or rising)
- **Key Difference**: Different universe, not different parameters

### 2. BearCorrelationGated_v1
**Strategy**: Monitor sector correlation and go to cash when too high
- **Universe**: Standard sectors + TLT/SGOV
- **Logic**:
  - Calculate 20-day rolling correlation matrix
  - If avg correlation > 0.8: 100% cash/SGOV
  - If correlation 0.6-0.8: 50% cash, 50% defensive
  - If correlation < 0.6: Normal rotation
- **Key Difference**: Uses correlation as primary signal

### 3. BearMultiAsset_v1
**Strategy**: True multi-asset rotation beyond just equities
- **Universe**: TLT, GLD, UUP, VXX (short-term), defensive sectors
- **Logic**: Relative strength ranking across asset classes
- **Key Difference**: Escapes equity-only constraint

## Testing Methodology

### Phase 1: Quick Validation (2022 Bear Market) ✅ COMPLETE
- **Period**: Jan 2022 - Dec 2022 (SPY -18.11%)
- **Success Criteria**: Loss < -10% (beat SPY by 8%+)
- **Timeline**: 1 day
- **Results**:
  - BearCorrelationGated_v1: **-5.32% ✅ PASS** (Beat SPY by 12.68%)
  - BearDefensiveRotation_v1: -18.78% ❌ FAIL
  - BearMultiAsset_v1: -22.74% ❌ FAIL

### Phase 2: Historical Bear Markets
- **2020 Crash**: Feb-Mar 2020 (SPY -34% in 33 days)
- **2018 Q4**: Oct-Dec 2018 (SPY -13.52%)
- **Success Criteria**: Drawdown < 50% of SPY's drawdown

### Phase 3: EA Optimization (If Phase 1-2 Pass)
- **Training**: 2008-2020 (includes 2008 crisis, 2011 debt crisis, 2018 selloff, 2020 crash)
- **Validation**: 2022 bear market
- **Parameters to optimize**:
  - Momentum/ranking periods (20-60 days)
  - Correlation thresholds (0.6-0.9)
  - Defensive allocation percentages
  - Rebalance frequency

### Phase 4: Out-of-Sample Test
- **Test Period**: 2025 YTD or 2023-2024 recovery
- **Success Criteria**: No catastrophic losses in non-bear periods

## Success/Failure Criteria

### Success (ALL must be met):
1. **Bear Market Performance**: Loss < -10% when SPY loses -18%+
2. **Crash Protection**: Drawdown < 50% of SPY's worst drawdown
3. **Recovery Participation**: Positive returns in recovery years
4. **Robustness**: Works across multiple bear market types

### Failure Indicators:
1. Loses more than SPY in bear markets
2. Misses recovery rallies (< 50% of SPY's recovery)
3. Excessive whipsawing (> 100 trades/year)
4. Only works in one specific type of bear market

## Risk Factors to Monitor

### 1. False Positives
- Going defensive too early in corrections (not bear markets)
- Missing bull market gains due to high correlation in rallies

### 2. Asset Class Risk
- Bonds may not be safe haven (rising rates environment)
- Gold correlation to equities increasing
- Dollar strength assumptions

### 3. Implementation Risk
- Data availability for alternative assets
- Transaction costs for frequent asset class switches
- Execution delays in crisis conditions

### 4. Overfitting Risk
- 2022 was inflation-driven bear (unique)
- 2020 was pandemic crash (extreme)
- 2008 was financial crisis (systemic)
- Need strategy that works across all types

## Parameter Recommendations

### BearDefensiveRotation_v1
```yaml
momentum_period: [20, 30, 45, 60]  # Shorter for defensive assets
top_n: [2, 3]  # Concentrate in best defensive
rebalance_days: [5, 10, 21]  # More frequent in crisis
min_momentum: [-0.10, -0.05, 0]  # Allow negative momentum
```

### BearCorrelationGated_v1
```yaml
correlation_window: [10, 20, 30]  # Days for correlation calc
correlation_threshold_high: [0.75, 0.80, 0.85]
correlation_threshold_low: [0.50, 0.60, 0.70]
defensive_allocation: [0.3, 0.5, 0.7]  # When partially defensive
```

### BearMultiAsset_v1
```yaml
ranking_period: [20, 30, 45]  # Cross-asset momentum
volatility_scaling: [true, false]  # Risk parity option
max_vxx_allocation: [0.1, 0.15, 0.2]  # Cap on volatility exposure
rebalance_trigger: [0.05, 0.10]  # Drift before rebalance
```

## Comparison with Failed Approaches

This experiment differs from past failures:

1. **Not momentum parameter tuning** (Exp 008, 010, 011 all failed)
2. **Not leverage-based** (Exp 011b proved leverage isn't the issue)
3. **Not single-asset-class** (All equity-only strategies failed in bears)
4. **Not regime-parameter-switching** (Current v3 approach insufficient)
5. **Fundamentally different strategy** per bear regime

## Next Steps

1. ✅ Review past experiments (Completed)
2. ✅ Create experiment structure (Completed)
3. ✅ Document experiment plan (Completed)
4. ✅ Design model architectures (Completed)
5. ✅ Create testing profiles (Completed)
6. ✅ Run Phase 1 tests (2022) (Completed)
7. ✅ Analyze Phase 1 results (Completed - see phase1_analysis.md)
8. ⏳ Run Phase 2 tests with BearCorrelationGated_v1 (Next)
9. ⏳ Consider enhancements (volatility confirmation, parameter tuning)

## Key Insights from Literature Review

From case studies and past experiments:
- **Momentum crashes in bear markets are systematic, not fixable with parameters**
- **Correlation spikes are the key signal** (all sectors move together)
- **Need escape valve to non-equity assets**
- **2022 validation is critical** (only reliable bear market in recent data)
- **Simple strategies beat complex in crisis** (fewer parameters = more robust)

## Documentation Requirements

Each model test will have:
- Full parameter configuration
- Backtest results with metadata.json
- Performance comparison to SPY
- Trade analysis (frequency, timing)
- Regime detection accuracy
- Recovery from prior bear markets

## Commands

```bash
# Phase 1: Quick 2022 test
python3 -m backtest.analyze_cli --profile bear_defensive_2022

# Phase 2: Historical bears
python3 -m backtest.analyze_cli --profile bear_defensive_2020
python3 -m backtest.analyze_cli --profile bear_defensive_2018

# Phase 3: EA optimization (if phases 1-2 pass)
python3 -m engines.optimization.walk_forward_cli \
  --experiment configs/experiments/exp_012_bear_defensive.yaml

# Phase 4: Out-of-sample
python3 -m backtest.analyze_cli --profile bear_defensive_2025_ytd
```

## References

- [Experiment 011](../011_multi_window_validation/README.md) - Proved momentum fails in bears
- [Case Study: Momentum Bear Failure](../../case_studies/CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md)
- [Case Study: EA Overfitting](../../case_studies/001_ea_overfitting_disaster.md)
- [What Failed](../../WHAT_FAILED.md) - Approaches to avoid

---

*Last Updated: November 24, 2025*