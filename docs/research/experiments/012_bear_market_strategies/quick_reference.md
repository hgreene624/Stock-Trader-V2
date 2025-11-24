# Experiment 012: Quick Reference

## Three Models to Test

### 1. BearDefensiveRotation_v1
```python
# Rotate among defensive assets by "least bad" momentum
Universe: XLU, XLP, TLT, GLD, UUP
Logic: Rank by momentum, pick top 2-3 least negative
```

### 2. BearCorrelationGated_v1
```python
# Use correlation as crisis indicator
If avg_correlation > 0.8: 100% SGOV
If avg_correlation > 0.6: 50% SGOV, 50% defensive
If avg_correlation < 0.6: Normal sector rotation
```

### 3. BearMultiAsset_v1
```python
# True multi-asset, not just equities
Universe: TLT, GLD, UUP, VXX, XLU, XLP
Logic: Relative strength across all asset classes
```

## Key Test Periods

| Period | SPY Return | Test Focus |
|--------|------------|------------|
| 2022 Full Year | -18.11% | Primary validation |
| 2020 Feb-Mar | -33.78% | Rapid crash response |
| 2018 Q4 | -13.52% | Normal correction |
| 2025 YTD | +15% (approx) | Non-bear performance |

## Success Metrics

### Must Have
- 2022 loss < -10% (beat SPY by 8%+)
- Works in 2+ historical bears
- Doesn't lose money in bull markets
- < 50 trades per year

### Nice to Have
- Positive return in 2022
- Sharpe > 1.0 full cycle
- Quick crash response (< 5 days)
- Simple enough to explain

## Key Commands

```bash
# Test in 2022
python3 -m backtest.analyze_cli --profile bear_defensive_2022

# Test in 2020 crash
python3 -m backtest.analyze_cli --profile bear_defensive_2020 \
  --start 2020-02-01 --end 2020-04-30

# Test full period
python3 -m backtest.analyze_cli --profile bear_defensive_full \
  --start 2018-01-01 --end 2025-11-24
```

## Parameters to Test

### Quick Grid (Phase 1)
```yaml
momentum_period: [20, 30, 45]
top_n: [2, 3]
correlation_window: [10, 20]
correlation_threshold: [0.7, 0.8]
```

### EA Optimization (Phase 3 - if warranted)
```yaml
momentum_period: 20-60
correlation_threshold: 0.6-0.9
defensive_allocation: 0.3-1.0
rebalance_days: 5-21
```

## Decision Points

1. **After 2022 Test**: Do 2+ models beat SPY? → Continue or stop
2. **After Historical**: Work in other bears? → EA optimize or use as-is
3. **After 2025 Test**: Acceptable in bulls? → Deploy or needs wrapper

## What We're NOT Doing

- NOT tuning momentum parameters (failed in Exp 011)
- NOT using leverage (made it worse)
- NOT complex multi-factor models
- NOT trying to profit from bears (just survive)

## Comparison Baseline

**Current Best Model**: SectorRotationAdaptive_v3
- 2022: Unknown (likely -15% to -20%)
- 2025 YTD: -17.58%
- Problem: Momentum fails when all sectors fall

**Our Goal**: Beat this significantly in bear markets

## Timeline

- Day 1: Code models, test 2022
- Day 2: Test historical bears
- Day 3-4: EA optimization (optional)
- Day 5: Final validation
- Day 6: Documentation

## Files to Create

```
models/
├── bear_defensive_rotation_v1.py
├── bear_correlation_gated_v1.py
└── bear_multi_asset_v1.py

configs/profiles.yaml:
├── bear_defensive_2022
├── bear_correlation_2022
├── bear_multiasset_2022
└── [historical test profiles]
```

## Key Insights from Research

1. **Momentum systematically fails in bears** (Exp 011)
2. **Correlation spikes are the warning signal**
3. **Need escape to non-equity assets**
4. **Simple strategies more robust in crisis**
5. **2022 is the critical test** (recent, severe, different type)

## Risk Factors

1. TLT failed in 2022 (rates rising)
2. Correlation is backward-looking
3. Asset relationships changing
4. Transaction costs spike in crisis
5. May sacrifice too much upside

## If All Models Fail

Consider:
- Simple SPY < 200MA → Cash rule
- Fixed 30% defensive allocation
- Volatility scaling (reduce as VIX rises)
- Tail hedging with options

---

**Remember: Goal is survival, not profit. -10% is success if SPY -18%.**