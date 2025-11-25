# Experiment 012b: Feature Testing for Bear Market Models

**Date**: 2025-11-25
**Status**: In Progress
**Base Model**: BearDefensiveRotation_v2 (20-day momentum rotation)

## Executive Summary

Testing 6 advanced features to improve BearDefensiveRotation_v2's robustness in choppy bear markets while maintaining recovery capture ability. Focus on fixing catastrophic 2018 failure (-21.70%) without sacrificing 2020 COVID recovery performance (+5.74%).

## Motivation

From Experiment 012 Phase 2 analysis:
- **Core Insight**: Recovery timing > Loss limitation. A "safe" model that misses recoveries underperforms dramatically
- **V2 Strengths**: Excellent recovery capture (2020: +5.74%)
- **V2 Weakness**: Catastrophic in choppy bears (2018: -21.70%)
- **Goal**: Make V2 robust without breaking its recovery mechanism

## Hypotheses

### H1: Risk Management Features (Variant 3)
**Volatility-based sizing + Drawdown circuit breaker** will reduce 2018 losses from -21.70% to < -12% without significantly impacting 2020 gains.

### H2: Recovery Enhancement Features (Variant 4)
**VIX recovery detection + Faster momentum** will improve 2020 gains from +5.74% to +8-10% while maintaining 2022 performance.

### H3: Quality Filter Features (Variant 5)
**Trend strength filter + Correlation-adjusted sizing** will improve consistency across all periods by reducing false signals.

### H4: Combined Best Features (Variant 6)
**Optimal combination** of successful features from V3-V5 will achieve balanced improvement across all bear markets.

## Feature Specifications

### Feature 1: Volatility-Based Position Sizing
```python
# Scale exposure inversely to realized volatility
target_vol = 0.15  # 15% annualized
realized_vol_20d = returns[-20:].std() * sqrt(252)
position_size = base_size * min(1.0, target_vol / realized_vol_20d)
```
**Rationale**: Reduce position size during high volatility to avoid whipsaws

### Feature 2: Drawdown Circuit Breaker
```python
# Exit to cash when model drawdown exceeds threshold
rolling_max_nav = nav_history.rolling(window=252).max()
current_dd = (current_nav / rolling_max_nav) - 1
if current_dd < -0.10:  # 10% drawdown threshold
    return {"SHY": 1.0}  # Full cash position
```
**Rationale**: Hard stop to prevent catastrophic losses like 2018

### Feature 3: VIX-Based Recovery Detection
```python
# Detect panic peaks and subsequent recovery signals
vix_peak_30d = vix[-30:].max()
vix_recovery_threshold = 0.70  # 30% decline from peak
if vix_peak_30d > 40 and vix[-1] < vix_peak_30d * vix_recovery_threshold:
    cash_threshold = 0.0  # Override cash, force rotation
```
**Rationale**: VIX spikes mark panic bottoms; declines signal safe re-entry

### Feature 4: Trend Strength Filter
```python
# Require consistent multi-period trends
momentum_10d = (price[-1] / price[-10]) - 1
momentum_20d = (price[-1] / price[-20]) - 1
min_momentum = -0.03  # -3% threshold

if momentum_10d > min_momentum and momentum_20d > min_momentum:
    eligible_for_rotation = True
```
**Rationale**: Both short and medium trends must agree to avoid false signals

### Feature 5: Correlation-Adjusted Sizing
```python
# Use correlation as continuous sizing input
sector_correlation = compute_correlation_matrix(defensive_assets)
avg_correlation = sector_correlation.mean()
position_size = base_size * (1 - avg_correlation * 0.5)  # Scale factor
```
**Rationale**: Reduce exposure when assets move together (systemic risk)

### Feature 6: Relative Strength Scoring
```python
# Rank by risk-adjusted outperformance vs market
spy_return_20d = (spy[-1] / spy[-20]) - 1
asset_return_20d = (asset[-1] / asset[-20]) - 1
asset_vol_20d = asset_returns[-20:].std()

relative_strength_score = (asset_return_20d - spy_return_20d) / asset_vol_20d
```
**Rationale**: Better asset selection by considering market-relative performance

## Test Variants

### Variant 3: Risk Management Focus
- **Base**: BearDefensiveRotation_v2
- **Features**: Volatility sizing (F1) + Drawdown breaker (F2)
- **Goal**: Fix 2018 catastrophe without breaking 2020 recovery
- **Parameters**:
  - `target_vol`: [0.10, 0.15, 0.20]
  - `dd_threshold`: [-0.08, -0.10, -0.12]

### Variant 4: Recovery Enhancement Focus
- **Base**: BearDefensiveRotation_v2
- **Features**: VIX recovery (F3) + Faster momentum (15-day)
- **Goal**: Improve 2020 gains, maintain 2022 performance
- **Parameters**:
  - `vix_panic_threshold`: [35, 40, 45]
  - `vix_recovery_ratio`: [0.65, 0.70, 0.75]
  - `momentum_period`: [15, 17, 20]

### Variant 5: Quality Filters Focus
- **Base**: BearDefensiveRotation_v2
- **Features**: Trend strength (F4) + Correlation sizing (F5)
- **Goal**: Consistent performance across all periods
- **Parameters**:
  - `min_momentum_10d`: [-0.05, -0.03, -0.01]
  - `min_momentum_20d`: [-0.05, -0.03, -0.01]
  - `correlation_scale`: [0.3, 0.5, 0.7]

### Variant 6: Best of Breed
- **Base**: BearDefensiveRotation_v2
- **Features**: TBD based on V3-V5 results
- **Goal**: Optimal combination
- **Parameters**: Best performing from each variant

## Success Criteria

### Minimum Requirements (Pass/Fail)
1. **2018 Q4**: Loss better than -12% (improve from -21.70%)
2. **2020 COVID**: Profit > +4% (allow degradation from +5.74%)
3. **2022 Bear**: Loss < -7% (allow degradation from -5.23%)

### Grading Scale
- **A**: Improves all 3 periods vs V2
- **B**: Improves 2/3 periods, neutral on third
- **C**: Improves 1/3 periods, others neutral
- **F**: Significantly hurts any period

### Key Metrics
| Metric | Primary | Secondary |
|--------|---------|-----------|
| CAGR | ✓ | |
| Sharpe Ratio | ✓ | |
| Max Drawdown | ✓ | |
| Recovery Speed | | ✓ |
| Trade Count | | ✓ |
| Win Rate | | ✓ |
| Feature-Specific | | ✓ |

## Testing Matrix

| Variant | 2018 Q4 | 2020 COVID | 2022 Bear | Total Tests |
|---------|---------|------------|-----------|-------------|
| V3 Risk Mgmt | 9 combos | 9 combos | 9 combos | 27 |
| V4 Recovery | 27 combos | 27 combos | 27 combos | 81 |
| V5 Quality | 27 combos | 27 combos | 27 combos | 81 |
| V6 Best | 1 combo | 1 combo | 1 combo | 3 |
| **Total** | | | | **192** |

## Risk Assessment

### Overfitting Risks
- **Risk**: Optimizing across 3 periods may create period-specific bias
- **Mitigation**: Test on 2008 crisis as out-of-sample validation

### Feature Interaction Risks
- **Risk**: Features may conflict (e.g., VIX override vs drawdown breaker)
- **Mitigation**: Define clear precedence rules in V6

### Complexity Risks
- **Risk**: Too many features reduce interpretability
- **Mitigation**: Maximum 3 features in final model

### Data Snooping Risks
- **Risk**: We've already seen these periods multiple times
- **Mitigation**: Focus on robustness, not absolute performance

## Expected Outcomes

### Best Case Scenario
- V3 fixes 2018 to -8% loss
- V4 improves 2020 to +8% gain
- V5 provides consistent -5% to +5% range
- V6 combines for balanced improvement

### Likely Scenario
- One variant significantly improves 2018
- Trade-off between recovery and protection
- V6 achieves B grade (2/3 periods improved)

### Worst Case Scenario
- All features hurt recovery more than help protection
- Return to V2 as best option
- Need completely different approach

## Next Steps

1. **Immediate**: Implement V3 (simplest features first)
2. **Day 1**: Complete V3 and V4 testing
3. **Day 2**: Complete V5 testing and initial V6 design
4. **Day 3**: Final V6 testing and documentation
5. **Deliverable**: Recommendation for production model

## Related Documents

- [Testing Protocol](testing_protocol.md) - Step-by-step procedures
- [Parameter Grid](parameter_grid.md) - Detailed parameter specifications
- [Results Template](results_template.md) - Standardized reporting format
- [Phase 1 Analysis](../phase1_v1_vs_v2_analysis.md) - V1 vs V2 comparison
- [Parent Experiment](../README.md) - Experiment 012 overview