# Experiment 005: Consistent Yearly Alpha

**Date Started**: 2025-11-23
**Status**: In Progress
**Primary Researcher**: Research Director (Claude)

## Executive Summary

The EA-optimized ATR model achieves strong overall performance (17.64% CAGR) but only beats SPY in 3 out of 5 years. This experiment aims to develop a model variant that consistently outperforms SPY in at least 4 out of 5 years while maintaining competitive overall returns.

## Problem Statement

### Current Performance (EA-Optimized Model)
- **Overall**: 17.64% CAGR vs SPY 14.34% ✓
- **Year-by-Year**:
  - 2020: +25.6% vs +18.4% (Alpha: +7.2%) ✓
  - 2021: +23.2% vs +28.7% (Alpha: -5.5%) ✗
  - 2022: -7.8% vs -18.1% (Alpha: +10.3%) ✓
  - 2023: +48.2% vs +26.2% (Alpha: +22.0%) ✓
  - 2024: +12.4% vs +25.0% (Alpha: -12.6%) ✗

**Success Rate**: 3/5 years (60%)
**Problem**: Underperforms in strong, low-volatility bull markets (2021, 2024)

### Root Causes Identified

1. **Rotation Penalty in Trending Markets**
   - Frequent sector rotation (every ~2 days) creates friction
   - In steady uptrends, buy-and-hold outperforms active rotation

2. **Leverage Amplifies Costs**
   - 2.0x leverage doubles transaction costs
   - 1286 trades over 5 years = high cumulative friction

3. **Stop Losses Cut Winners Short**
   - 1.6x ATR stops work in volatile markets
   - In steady bulls, they prevent full upside capture

4. **Equal-Weight Sectors Miss Leadership**
   - 2024 driven by Magnificent 7 concentration
   - Sector rotation missed mega-cap dominance

## Hypothesis

**Primary**: A model with adaptive parameters based on market regime will achieve more consistent yearly outperformance by:
1. Reducing rotation frequency in trending markets
2. Using lower leverage (1.0-1.25x) to minimize friction
3. Employing wider stops in bull markets
4. Allowing concentration in winning sectors

**Expected Outcome**:
- Beat SPY in ≥4 out of 5 years
- Minimum yearly alpha > -5%
- Overall CAGR > 14.34%

## Experimental Design

### Multi-Objective Optimization Framework

```python
def fitness_function(params, backtest_results):
    """
    Multi-objective fitness for consistent yearly alpha
    """
    yearly_returns = calculate_yearly_returns(backtest_results)
    spy_returns = {2020: 18.4, 2021: 28.7, 2022: -18.1, 2023: 26.2, 2024: 25.0}

    # Calculate yearly alphas
    alphas = []
    for year, model_return in yearly_returns.items():
        alpha = model_return - spy_returns[year]
        alphas.append(alpha)

    # Multi-objective components
    years_beating_spy = sum(1 for a in alphas if a > 0)
    worst_alpha = min(alphas)
    overall_cagr = backtest_results['cagr']

    # Weighted fitness
    fitness = (
        0.40 * (years_beating_spy / 5.0) * 100  # Primary: maximize years beating
        + 0.30 * max(0, (worst_alpha + 20) / 20) * 100  # Secondary: minimize worst year
        + 0.30 * (overall_cagr / 20.0) * 100  # Tertiary: maximize CAGR
    )

    return fitness
```

### Parameter Search Space

```yaml
# Adaptive parameters to test
adaptive_params:
  # Rotation frequency controls
  min_hold_days: [5, 10, 15, 20]
  rotation_threshold: [0.02, 0.05, 0.10]  # Min difference to trigger rotation

  # Leverage controls (constrained for small account)
  bull_leverage: [1.0, 1.1, 1.2, 1.25]
  bear_leverage: [1.0]  # Fixed at 1.0 for safety

  # Stop loss adaptation
  bull_stop_mult: [2.0, 2.5, 3.0]  # Wider in bulls
  bear_stop_mult: [1.0, 1.5]  # Tighter in bears

  # Concentration controls
  max_sector_weight: [0.4, 0.5, 0.6]  # Allow concentration
  rebalance_threshold: [0.10, 0.15, 0.20]  # Deviation before rebalance

  # Trend persistence
  trend_lookback: [20, 40, 60]  # Days to measure trend
  momentum_decay: [0.90, 0.95, 0.98]  # Decay factor for momentum
```

### Testing Methodology

1. **Phase 1: Parameter Exploration** (Grid Search)
   - Test parameter combinations on 2020-2023 data
   - Optimize for years_beating_spy metric
   - Select top 10 configurations

2. **Phase 2: Validation** (Walk-Forward)
   - Test top 10 on 2024 out-of-sample
   - Verify consistency holds

3. **Phase 3: Robustness Testing**
   - Monte Carlo simulation with parameter noise
   - Verify stability across market conditions

## Model Implementation Strategy

### New Model: `SectorRotationConsistent_v1`

Key differences from v3:
1. **Adaptive Min Hold Period**
   ```python
   def calculate_min_hold_days(self, volatility_regime):
       if volatility_regime == 'low':
           return self.params['min_hold_days_low']  # 10-20 days
       else:
           return self.params['min_hold_days_high']  # 2-5 days
   ```

2. **Rotation Threshold**
   ```python
   def should_rotate(self, current_sector, best_sector, scores):
       score_diff = scores[best_sector] - scores[current_sector]
       return score_diff > self.params['rotation_threshold']
   ```

3. **Regime-Adaptive Leverage**
   ```python
   def get_leverage(self, regime, volatility):
       if regime == 'bull' and volatility < 0.15:
           return self.params['bull_leverage']  # 1.0-1.25x
       else:
           return 1.0  # No leverage in uncertain conditions
   ```

4. **Concentration Allowance**
   ```python
   def apply_concentration_boost(self, weights, momentum_scores):
       # Allow up to max_sector_weight for strong winners
       top_sector = max(momentum_scores, key=momentum_scores.get)
       if momentum_scores[top_sector] > 0.8:
           weights[top_sector] = min(weights[top_sector] * 1.5,
                                     self.params['max_sector_weight'])
   ```

## Success Criteria

### Primary Metrics
- **Years Beating SPY**: ≥ 4 out of 5 (80%)
- **Worst Year Alpha**: > -5%
- **Consistency Score**: std(yearly_alphas) < 10%

### Secondary Metrics
- **Overall CAGR**: > 14.34% (SPY benchmark)
- **Sharpe Ratio**: > 1.5
- **Max Drawdown**: < 20%
- **Win Rate**: > 55%

### Constraint Validation
- **Leverage**: Never exceeds 1.25x (Alpaca small account limit)
- **Trade Frequency**: < 100 trades/year (reduce friction)
- **Concentration**: No single position > 60% NAV

## Test Execution Plan

### Step 1: Create Model Variant
```bash
cp models/sector_rotation_v3.py models/sector_rotation_consistent_v1.py
# Implement adaptive features
```

### Step 2: Configure Grid Search
```yaml
# configs/experiments/exp_005_consistent_alpha.yaml
experiment:
  name: "consistent_yearly_alpha"
  model: "SectorRotationConsistent_v1"
  method: "grid"
  objective: "yearly_consistency"  # Custom metric
  parameters:
    # Parameter ranges defined above
```

### Step 3: Run Optimization
```bash
# Initial grid search
python3 -m engines.optimization.yearly_consistency_cli \
  --experiment configs/experiments/exp_005_consistent_alpha.yaml \
  --years 2020-2023

# Validation on 2024
python3 -m engines.optimization.walk_forward_cli \
  --model SectorRotationConsistent_v1 \
  --params best_params.yaml \
  --test-year 2024
```

### Step 4: Analyze Results
```python
# Generate yearly breakdown for all tested configurations
python3 -m analysis.yearly_breakdown \
  --results results/exp_005_consistent_alpha.db \
  --output results/exp_005_yearly_analysis.csv
```

## Risk Analysis

### Potential Failure Modes
1. **Over-optimization**: Parameters too specific to 2020-2024 period
2. **Reduced Returns**: Lower leverage may not beat SPY overall
3. **Complexity**: Adaptive rules may be unstable

### Mitigation Strategies
1. **Simple Rules**: Keep adaptations rule-based, not ML
2. **Conservative Defaults**: When uncertain, use safer parameters
3. **Gradual Changes**: Smooth parameter transitions, no jumps

## Timeline

- **Day 1** (Today): Problem analysis, experiment design ✓
- **Day 2**: Implement SectorRotationConsistent_v1 model
- **Day 3**: Run grid search optimization
- **Day 4**: Validation and robustness testing
- **Day 5**: Final analysis and recommendations

## Next Steps

1. [ ] Create `SectorRotationConsistent_v1` model with adaptive features
2. [ ] Implement custom yearly consistency optimizer
3. [ ] Run grid search on 2020-2023 data
4. [ ] Validate on 2024 out-of-sample
5. [ ] Document winning configuration
6. [ ] Prepare production deployment if successful

## References

- [EXPERIMENT_PROTOCOL.md](../EXPERIMENT_PROTOCOL.md) - Experiment structure guidelines
- [004_atr_stop_loss/EA_Results.md](../004_atr_stop_loss/EA_Results.md) - Previous best model
- [Walk-Forward Guide](../../../guides/walk_forward.md) - Validation methodology
- [SESSION_SUMMARY_2025-11-18.md](../../../../SESSION_SUMMARY_2025-11-18.md) - Recent optimizations

## Appendix A: Market Regime Analysis

### 2021 Underperformance (-5.5% alpha)
- **Market**: Post-COVID recovery, broad rally
- **Issue**: Over-rotation in trending market
- **Solution**: Longer hold periods, lower leverage

### 2024 Underperformance (-12.6% alpha)
- **Market**: AI boom, Magnificent 7 concentration
- **Issue**: Sector rotation missed tech dominance
- **Solution**: Allow concentration, reduce rotation threshold

## Appendix B: Implementation Notes

### Key Code Changes Needed

1. **Volatility Regime Detection**
```python
def detect_volatility_regime(self, returns, lookback=20):
    vol = returns.rolling(lookback).std()
    current_vol = vol.iloc[-1]
    vol_percentile = (vol < current_vol).mean()
    return 'low' if vol_percentile < 0.3 else 'high'
```

2. **Adaptive Parameter Selection**
```python
def get_adaptive_params(self, market_state):
    params = self.base_params.copy()
    if market_state['volatility_regime'] == 'low':
        params['min_hold_days'] *= 2
        params['rotation_threshold'] *= 2
        params['stop_loss_mult'] *= 1.5
    return params
```

3. **Yearly Performance Tracking**
```python
def track_yearly_performance(self, nav_series):
    yearly_perfs = {}
    for year in nav_series.index.year.unique():
        year_nav = nav_series[nav_series.index.year == year]
        yearly_return = (year_nav.iloc[-1] / year_nav.iloc[0] - 1) * 100
        yearly_perfs[year] = yearly_return
    return yearly_perfs
```

---

*This experiment aims to solve the critical business problem: achieving consistent outperformance that clients can rely on year after year, not just over multi-year periods.*