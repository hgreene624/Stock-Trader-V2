# Experiment 005: Initial Results

**Date**: 2025-11-23
**Status**: In Progress

## Summary of Testing

We've created and tested a new model variant `SectorRotationConsistent_v1` with conservative parameters designed to achieve more consistent yearly outperformance. Initial results show the conservative approach sacrifices too much upside.

## Model Comparison

### EA-Optimized Model (SectorRotationAdaptive_v3)
- **Overall**: 17.64% CAGR, 2.24 Sharpe, 1.02 BPS
- **Leverage**: 2.0x bull / 1.38x bear
- **Years beating SPY**: 3/5 (2020, 2022, 2023)
- **Worst alpha**: -12.6% (2024)
- **Problem**: High leverage causes underperformance in steady bull markets

### Consistent Alpha Baseline (SectorRotationConsistent_v1)
- **Overall**: 11.25% CAGR, 1.76 Sharpe, 0.81 BPS
- **Leverage**: 1.2x bull / 1.0x bear
- **Years beating SPY**: 3/5 (2021, 2022, 2023)
- **Worst alpha**: -21.4% (2020)
- **Problem**: Too conservative, doesn't capture enough upside

## Year-by-Year Breakdown

| Year | SPY   | EA-Optimized | Baseline | Winner |
|------|-------|--------------|----------|---------|
| 2020 | 18.4% | 25.6% ✓      | -3.0% ✗  | EA      |
| 2021 | 28.7% | 23.2% ✗      | 30.2% ✓  | Baseline|
| 2022 | -18.1%| -7.8% ✓      | -8.1% ✓  | Both    |
| 2023 | 26.2% | 48.2% ✓      | 29.5% ✓  | Both    |
| 2024 | 25.0% | 12.4% ✗      | 16.7% ✗  | Neither |

### Key Insights

1. **2020 Performance Divergence**:
   - EA model thrived with higher leverage during volatile COVID recovery
   - Baseline model's conservative approach and longer hold periods hurt during rapid recovery

2. **2021 Success for Baseline**:
   - Lower leverage and longer holds worked well in steady uptrend
   - EA model over-rotated in broad-based rally

3. **2022 Bear Market**:
   - Both models successfully limited downside
   - Defensive positioning worked well

4. **2023 Strong Performance**:
   - Both models captured the rally
   - EA model's higher leverage amplified gains

5. **2024 Underperformance**:
   - Both missed the AI/tech concentration
   - Sector rotation approach doesn't work when single sector dominates

## Hypothesis Validation

### ✗ Original Hypothesis Partially Failed
**Expected**: Lower leverage and longer holds would improve consistency
**Result**: Still only 3/5 years beating SPY, just different years

### What Worked
- Longer hold periods helped in 2021 steady trend
- Conservative leverage reduced 2022 drawdown
- Adaptive parameters showed promise

### What Didn't Work
- Too conservative in 2020 volatile recovery
- Still missed 2024 tech concentration
- Overall CAGR (11.25%) below SPY target (14.34%)

## Next Steps for Optimization

### 1. Parameter Sweet Spot Search
Need to find optimal balance between v1 and v3:

```yaml
leverage_grid:
  bull_leverage: [1.3, 1.4, 1.5, 1.6, 1.7]
  bear_leverage: [1.0, 1.1, 1.2]

hold_period_grid:
  min_hold_days_low_vol: [7, 10, 12]
  min_hold_days_high_vol: [3, 4, 5]

rotation_threshold_grid: [0.03, 0.04, 0.05, 0.06]
```

### 2. Year-Specific Optimization
Create fitness function that specifically targets problem years:

```python
def yearly_consistency_fitness(params, backtest_results):
    yearly_alphas = calculate_yearly_alphas(backtest_results)

    # Penalize large negative alphas more than reward large positive
    consistency_score = 0
    for alpha in yearly_alphas:
        if alpha < -5:  # Heavy penalty for big underperformance
            consistency_score += alpha * 2
        elif alpha < 0:  # Moderate penalty for small underperformance
            consistency_score += alpha * 1.5
        else:  # Normal reward for outperformance
            consistency_score += alpha

    # Bonus for beating SPY in 4+ years
    years_beating = sum(1 for a in yearly_alphas if a > 0)
    if years_beating >= 4:
        consistency_score += 10

    return consistency_score
```

### 3. Tech Concentration Handler
Add special logic for concentrated markets:

```python
def detect_concentration(context):
    """Detect if market is dominated by single sector"""
    sector_returns = calculate_sector_returns(context)
    top_sector_dominance = max(sector_returns.values()) / sum(sector_returns.values())
    return top_sector_dominance > 0.4  # If one sector is >40% of gains

def adjust_for_concentration(weights, concentration_detected):
    if concentration_detected:
        # Increase weight to top performer
        # Reduce rotation threshold
        # Extend hold period
        pass
```

### 4. Regime-Specific Parameters
Instead of one-size-fits-all, use different parameters per regime:

```yaml
regime_parameters:
  volatile_recovery:  # 2020-like
    leverage: 1.8
    min_hold: 3
    rotation_threshold: 0.02

  steady_bull:  # 2021-like
    leverage: 1.3
    min_hold: 10
    rotation_threshold: 0.08

  bear_market:  # 2022-like
    leverage: 1.0
    min_hold: 5
    rotation_threshold: 0.05

  concentrated_rally:  # 2024-like
    leverage: 1.5
    min_hold: 20
    rotation_threshold: 0.10
```

## Recommended Immediate Action

1. **Run Grid Search** with intermediate parameters:
   - Bull leverage: 1.4-1.6x (between v1's 1.2x and v3's 2.0x)
   - Min hold: 7-10 days (between v1's 15 and v3's 2)
   - Focus on maximizing years_beating_spy metric

2. **Test Fast Rotation Variant**:
   - Already configured as `consistent_alpha_fast_rotation` profile
   - May help with 2020 recovery period

3. **Analyze Sector Performance** in 2020 and 2024:
   - Understand which sectors drove SPY outperformance
   - Adjust model logic to better capture these patterns

## Conclusion

The conservative approach didn't solve the consistency problem - it just shifted which years underperform. We need a more adaptive approach that can handle different market regimes:
- Aggressive in volatile recoveries (2020)
- Patient in steady trends (2021)
- Defensive in bear markets (2022)
- Concentrated in narrow rallies (2024)

The path forward is clear: multi-regime optimization with year-specific fitness targeting.