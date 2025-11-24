# Testing Sequence for Experiment 012

## Overview
Systematic testing plan for three bear market strategies, with clear go/no-go decision points.

## Pre-Flight Checklist

- [ ] Commit all changes before testing
- [ ] Verify data availability for TLT, GLD, UUP, VXX
- [ ] Create profiles in configs/profiles.yaml
- [ ] Set up result tracking spreadsheet

## Phase 1: 2022 Bear Market Validation (Day 1)

### Test 1.1: BearDefensiveRotation_v1
```bash
# Create model file
vim models/bear_defensive_rotation_v1.py

# Add profile
vim configs/profiles.yaml  # Add bear_defensive_2022

# Run test
python3 -m backtest.analyze_cli --profile bear_defensive_2022

# Save results
mv results/analysis/[latest]/* docs/research/experiments/012_bear_market_strategies/defensive_rotation/analysis/
```

**Success Criteria**:
- Loss < -10% (SPY was -18.11%)
- Max drawdown < -15%
- Trade count < 50

**Decision Point**: If fails, redesign universe or logic before proceeding

### Test 1.2: BearCorrelationGated_v1
```bash
# Same process with correlation-based model
python3 -m backtest.analyze_cli --profile bear_correlation_2022
```

**Success Criteria**:
- Correctly identifies high correlation periods
- Moves to cash/defensive before major drawdowns
- Loss < -8%

### Test 1.3: BearMultiAsset_v1
```bash
python3 -m backtest.analyze_cli --profile bear_multiasset_2022
```

**Success Criteria**:
- Successfully rotates to non-equity assets
- Positive or small negative return
- Captures flight-to-quality moves

### Phase 1 Go/No-Go Decision

**Proceed to Phase 2 if**:
- At least 2 models beat SPY by 5%+
- No model loses more than SPY
- Execution is reasonable (< 100 trades)

**Stop and redesign if**:
- All models lose more than -15%
- Models fail to identify bear market
- Excessive trading or whipsaws

## Phase 2: Historical Validation (Day 2)

### Test 2.1: 2020 COVID Crash (Feb-Mar)
```bash
# Test each winning model from Phase 1
python3 -m backtest.analyze_cli --profile bear_[model]_2020 \
  --start 2020-02-01 --end 2020-04-30
```

**Focus**: Speed of reaction to sudden crash
- Did model go defensive by Feb 25?
- Max drawdown vs SPY's -34%?
- Recovery participation in April?

### Test 2.2: 2018 Q4 Correction
```bash
python3 -m backtest.analyze_cli --profile bear_[model]_2018 \
  --start 2018-10-01 --end 2018-12-31
```

**Focus**: Handling "normal" correction vs crash
- Avoid overreacting to -13% drop
- Maintain some equity exposure
- Reasonable performance

### Test 2.3: 2008 Financial Crisis (if data available)
```bash
python3 -m backtest.analyze_cli --profile bear_[model]_2008 \
  --start 2008-01-01 --end 2009-03-31
```

**Focus**: Extended bear market performance
- Sustained defensive positioning
- Avoid attempts to catch falling knife
- Capital preservation priority

### Phase 2 Go/No-Go Decision

**Proceed to Phase 3 if**:
- Model beats SPY in 2+ historical bears
- No catastrophic failure in any period
- Consistent bear market identification

**Stop if**:
- Only works in 2022 (overfitted)
- Fails in rapid crashes (2020)
- Can't distinguish correction from bear

## Phase 3: EA Optimization (Days 3-4)

### Only for models that passed Phases 1-2

### Step 3.1: Create EA experiment config
```yaml
# configs/experiments/exp_012_bear_defensive.yaml
model: BearDefensiveRotation_v1  # Or winning model
optimization_method: evolutionary
population_size: 20
generations: 10  # Start small
training_period: 2008-2020
validation_period: 2022
```

### Step 3.2: Run walk-forward optimization
```bash
python3 -m engines.optimization.walk_forward_cli \
  --experiment configs/experiments/exp_012_bear_defensive.yaml \
  --quick
```

### Step 3.3: Validate best parameters
Test top 3 parameter sets on:
- 2022 (validation year)
- 2023 (recovery year)
- 2024 (bull year)

**Critical**: Must not lose money in bull years!

### Phase 3 Success Criteria
- Validation degradation < 30%
- Positive returns in recovery years
- Parameter stability (not wildly different values)

## Phase 4: Final Validation (Day 5)

### Test 4.1: 2025 YTD Performance
```bash
python3 -m backtest.analyze_cli --profile bear_[optimized] \
  --start 2025-01-01 --end 2025-11-24
```

**Critical Test**: Can it handle non-bear period?
- Should not be heavily defensive in bull
- Reasonable positive return
- Low trading frequency

### Test 4.2: Full Period Backtest
```bash
python3 -m backtest.analyze_cli --profile bear_[optimized] \
  --start 2018-01-01 --end 2025-11-24
```

**Holistic View**:
- Overall CAGR vs SPY
- Sharpe ratio > 0.8
- Max drawdown < -20%
- Regime detection accuracy

## Decision Tree

```
Phase 1 (2022)
  ├─ 2+ models beat SPY → Continue to Phase 2
  └─ All fail → STOP, fundamental redesign needed

Phase 2 (Historical)
  ├─ Works in 2+ bears → Continue to Phase 3
  └─ Only works in 2022 → STOP, overfitted to one bear type

Phase 3 (EA Optimization)
  ├─ Stable parameters → Continue to Phase 4
  └─ Unstable/degraded → Use Phase 1 parameters instead

Phase 4 (Final)
  ├─ Passes all periods → READY FOR DEPLOYMENT
  └─ Fails non-bear → Need regime-switching wrapper
```

## Result Documentation

For each test, capture:
1. Full command used
2. CAGR, Sharpe, Max Drawdown
3. Trade count and turnover
4. Best/worst months
5. Regime detection accuracy
6. metadata.json location

## Failure Recovery

If all models fail:
1. Document why in experiment folder
2. Consider hybrid approach (combine with momentum)
3. Research academic literature on bear strategies
4. Consider options-based hedging instead

## Timeline

- **Day 1**: Phase 1 (2022 validation)
- **Day 2**: Phase 2 (historical bears)
- **Day 3-4**: Phase 3 (EA optimization) - if warranted
- **Day 5**: Phase 4 (final validation)
- **Day 6**: Documentation and recommendations

Total: 5-6 days maximum before go/no-go decision

---

*Remember: The goal is capital preservation in bear markets, not maximizing returns!*