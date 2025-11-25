# Variant 4: Recovery Enhancement Features

**Status**: Not Started
**Features**: VIX-based recovery detection + Faster momentum (15-day)
**Goal**: Improve 2020 recovery from +5.74% to +8-10%

## Hypothesis

Using VIX as a panic/recovery indicator combined with faster momentum signals will enable earlier and more aggressive positioning during market recoveries, particularly V-shaped bounces like 2020 COVID.

## Implementation Details

### Feature 1: VIX-Based Recovery Detection

```python
def detect_vix_recovery(vix_series, panic_threshold=40, recovery_ratio=0.70):
    """Detect market recovery based on VIX behavior"""
    # Find recent VIX peak (30-day window)
    vix_peak_30d = vix_series[-30:].max()

    # Check if we had a panic spike
    if vix_peak_30d > panic_threshold:
        current_vix = vix_series[-1]

        # Check if VIX has calmed down sufficiently
        if current_vix < vix_peak_30d * recovery_ratio:
            return True, "recovery_detected", vix_peak_30d, current_vix

    return False, "normal", None, None
```

**Rationale**: VIX spikes mark panic bottoms; significant VIX declines signal all-clear for risk-on

### Feature 2: Adaptive Momentum Period

```python
def calculate_adaptive_momentum(prices, base_period=20, fast_period=15):
    """Use faster momentum during recovery periods"""
    if recovery_mode:
        momentum_period = fast_period
    else:
        momentum_period = base_period

    momentum = (prices[-1] / prices[-momentum_period-1]) - 1
    return momentum, momentum_period
```

**Rationale**: Faster signals capture sharp V-recoveries better

### Feature 3: Recovery Position Boost

```python
def apply_recovery_boost(base_weights, recovery_mode, boost_factor=1.5):
    """Increase position sizes during confirmed recovery"""
    if recovery_mode:
        # Scale up non-cash positions
        for asset in base_weights:
            if asset != "SHY":
                base_weights[asset] *= boost_factor

        # Renormalize
        total = sum(base_weights.values())
        for asset in base_weights:
            base_weights[asset] /= total

    return base_weights
```

**Rationale**: Be aggressive when recovery is confirmed

## Parameter Grid

| Parameter | Values | Description |
|-----------|--------|-------------|
| vix_panic_threshold | [35, 40, 45] | VIX level indicating panic |
| vix_recovery_ratio | [0.65, 0.70, 0.75] | Fraction of peak = recovery |
| momentum_period | [15, 17, 20] | Days for momentum (fast mode) |

**Total combinations**: 3 × 3 × 3 = 27

## VIX Historical Context

### Key VIX Levels
- Normal market: 12-20
- Elevated concern: 20-30
- High fear: 30-40
- Panic: 40-50
- Extreme panic: 50+

### Historical Spikes
- 2020 COVID: 85 (highest ever)
- 2008 Crisis: 80
- 2018 Q4: 36
- 2022 Bear: 38

## Expected Outcomes

### Best Case
- 2020 COVID: Improve from +5.74% to +10%
- 2018 Q4: Maintain around -12%
- 2022 Bear: Slight improvement to -4%

### Likely Case
- 2020 COVID: +7% to +8%
- 2018 Q4: -12% to -15%
- 2022 Bear: -5% to -6%

### Risk Factors
- False VIX signals in choppy markets
- Too aggressive during fake recoveries
- Momentum whipsaws with faster periods

## Testing Checklist

- [ ] Download VIX data if not available
- [ ] Implement BearDefensiveRotation_v4 model
- [ ] Add VIX recovery detection logic
- [ ] Implement adaptive momentum
- [ ] Test all 27 parameter combinations
- [ ] Log VIX trigger events
- [ ] Analyze recovery timing vs V2
- [ ] Document false positive rate
- [ ] Select optimal parameters

## Results

[To be populated after testing]

### Performance Summary

| Parameters | 2018 Q4 | 2020 COVID | 2022 Bear | Avg CAGR | Grade |
|------------|---------|------------|-----------|----------|-------|
| Baseline V2 | -21.70% | +5.74% | -5.23% | -7.06% | - |
| [Best TBD] | TBD | TBD | TBD | TBD | TBD |

### VIX Signal Analysis

**2020 COVID Signals**:
- First panic signal: TBD
- Recovery signal: TBD
- Days earlier than V2: TBD
- Additional profit: TBD

**False Positives**:
- 2018 Q4: TBD occurrences
- 2022 Bear: TBD occurrences

### Recommendation

[To be completed after testing]