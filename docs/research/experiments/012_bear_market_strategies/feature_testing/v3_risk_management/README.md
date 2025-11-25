# Variant 3: Risk Management Features

**Status**: Not Started
**Features**: Volatility-based sizing + Drawdown circuit breaker
**Goal**: Fix 2018 catastrophe (-21.70%) without breaking 2020 recovery

## Hypothesis

Dynamically scaling position sizes based on realized volatility and implementing a hard-stop drawdown circuit breaker will reduce catastrophic losses during choppy bear markets while preserving most recovery upside.

## Implementation Details

### Feature 1: Volatility-Based Position Sizing

```python
def calculate_position_scale(returns, target_vol=0.15):
    """Scale positions inversely to realized volatility"""
    # Calculate 20-day realized volatility
    realized_vol = returns[-20:].std() * np.sqrt(252)

    # Scale to target volatility
    position_scale = min(1.0, target_vol / realized_vol)

    return position_scale
```

**Rationale**: When volatility spikes, reduce exposure to avoid whipsaws

### Feature 2: Drawdown Circuit Breaker

```python
def check_circuit_breaker(nav_history, threshold=-0.10):
    """Exit to cash when drawdown exceeds threshold"""
    # Calculate rolling 252-day peak
    rolling_peak = nav_history[-252:].max()

    # Current drawdown
    current_dd = (nav_history[-1] / rolling_peak) - 1

    if current_dd < threshold:
        return True, rolling_peak  # Trigger breaker, remember peak

    return False, rolling_peak
```

**Rationale**: Absolute protection against catastrophic losses

## Parameter Grid

| Parameter | Values | Description |
|-----------|--------|-------------|
| target_vol | [0.10, 0.15, 0.20] | Target annualized volatility |
| dd_threshold | [-0.08, -0.10, -0.12] | Maximum drawdown before cash exit |

**Total combinations**: 3 × 3 = 9

## Expected Outcomes

### Best Case
- 2018 Q4: Improve from -21.70% to -8%
- 2020 COVID: Maintain at least +4%
- 2022 Bear: Keep under -7%

### Likely Case
- 2018 Q4: -10% to -12%
- 2020 COVID: +3% to +4%
- 2022 Bear: -5% to -7%

### Risk Factors
- Circuit breaker might trigger too often
- Volatility scaling might reduce returns too much
- Reset conditions might be too conservative

## Testing Checklist

- [ ] Implement BearDefensiveRotation_v3 model
- [ ] Add to backtest/analyze_cli.py registry
- [ ] Test all 9 parameter combinations
- [ ] Document circuit breaker trigger frequency
- [ ] Analyze volatility scaling impact
- [ ] Compare to V2 baseline
- [ ] Select best parameters
- [ ] Document in results section

## Results

[To be populated after testing]

### Performance Summary

| Parameters | 2018 Q4 | 2020 COVID | 2022 Bear | Avg CAGR | Grade |
|------------|---------|------------|-----------|----------|-------|
| Baseline V2 | -21.70% | +5.74% | -5.23% | -7.06% | - |
| [Best TBD] | TBD | TBD | TBD | TBD | TBD |

### Feature Effectiveness

**Volatility Scaling**:
- Average scale factor: TBD
- Impact on returns: TBD
- Impact on volatility: TBD

**Circuit Breaker**:
- Total triggers: TBD
- Average cash duration: TBD
- Protection effectiveness: TBD

### Recommendation

[To be completed after testing]