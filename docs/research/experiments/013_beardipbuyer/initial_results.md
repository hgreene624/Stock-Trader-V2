# Experiment 013: BearDipBuyer Initial Test Results

## Model Implementation

**Model**: `BearDipBuyer_v1`
**Date**: 2025-11-25
**Version**: 1.0.0

### Key Features Implemented

1. **Panic Detection System** (NEW)
   - VIX thresholds: 25 (moderate), 30 (high), 35 (extreme)
   - RSI oversold detection: 25 (oversold), 20 (extreme)
   - Price below 200-day MA threshold: 10%
   - Volume spike detection: 2x average

2. **Quality Filters** (from V5)
   - Trend strength calculation
   - Minimum trend strength: -0.3 (allows mild downtrends)
   - Correlation-based sizing

3. **Risk Management** (from V3)
   - Volatility scalar (max daily vol: 5%)
   - Circuit breaker at -8% drawdown
   - NAV tracking for drawdown calculation

4. **Recovery Timing** (from V2)
   - Fast momentum: 10 days
   - Slow momentum: 30 days
   - Rebalance frequency: 5 days

## Initial Test Results

### Test 1: 2020 COVID Crash (Feb-Apr 2020)

```
Period: 2020-02-01 to 2020-04-30
Final NAV: $97,042.58
Total Return: -2.81%
CAGR: -11.28%
Sharpe Ratio: -3.677
Max Drawdown: 5.88%
Win Rate: 50.0%
Total Trades: 20
BPS: -1.410
```

**Market Context**:
- VIX Max: 82.69 (extreme panic)
- VIX Mean: 40.54
- Days with VIX > 30: 45
- Days with VIX > 35: 39

**Analysis**: Model LOST money during extreme panic when it should have been buying aggressively. This is a critical failure.

### Test 2: 2022 Rate Hike Bear Market

```
Period: 2022-01-01 to 2022-12-31
Final NAV: $95,503.27
Total Return: -4.40%
CAGR: -4.40%
Sharpe Ratio: -5.341
Max Drawdown: Unknown
Win Rate: Unknown
Total Trades: 51
BPS: -2.055
```

**Market Context**:
- VIX Max: 36.45
- VIX Mean: 25.62
- Days with VIX > 30: 48
- Days with VIX > 35: 2 (only)

**Analysis**: Model lost money in grinding bear market. This is somewhat expected given only 2 days of extreme panic.

### Test 3: 2018 Q4 Correction

Not tested yet due to initial failures.

## Issues Identified

### 1. Panic Detection Not Triggering Properly
- Despite VIX hitting 82.69 in March 2020, model didn't buy aggressively
- Possible issues:
  - Quality filters too restrictive
  - Volatility scalar reducing positions too much
  - Circuit breaker activating prematurely

### 2. Negative Performance in Target Conditions
- Model specifically designed for panic buying
- Failed during the most extreme panic since 2008
- Suggests fundamental logic error

### 3. Possible Bugs
- Panic level calculation may not be working
- Position sizing might be inverted
- Quality filters might be blocking all trades

## Next Steps

### Immediate Actions Required

1. **Debug Panic Detection**:
   ```python
   # Add logging to calculate_panic_level()
   # Print VIX level, RSI, panic level for each bar
   ```

2. **Verify Position Sizing**:
   ```python
   # Check if volatility scalar is too restrictive
   # Verify panic level → position size mapping
   ```

3. **Test Without Quality Filters**:
   ```python
   # Temporarily disable trend_strength check
   # Test pure panic buying logic
   ```

4. **Analyze Trade Log**:
   - When did model buy/sell?
   - What were VIX levels at trade times?
   - Were positions sized correctly?

### Parameter Adjustments to Test

1. **Lower VIX Thresholds**:
   - Moderate: 20 (was 25)
   - High: 25 (was 30)
   - Extreme: 30 (was 35)

2. **Relax Quality Filters**:
   - min_trend_strength: -0.5 (was -0.3)
   - Disable correlation adjustment

3. **Adjust Risk Management**:
   - max_volatility: 0.10 (was 0.05)
   - circuit_breaker: -0.15 (was -0.08)

## Comparison with Experiment 012 Models

| Model | 2020 COVID | 2022 Bear | Best Use Case |
|-------|------------|-----------|---------------|
| BearDefensiveRotation_v2 | TBD | TBD | Defensive rotation |
| BearDefensiveRotation_v3 | TBD | TBD | With risk management |
| BearDefensiveRotation_v5 | TBD | TBD | Quality filtered |
| **BearDipBuyer_v1** | **-2.81%** | **-4.40%** | **Panic buying (FAILED)** |

## Conclusion

The BearDipBuyer_v1 model failed its initial tests, losing money during both extreme panic (2020) and grinding bear markets (2022). The model needs significant debugging and adjustment before it can be considered viable.

**Status**: ❌ FAILED - Requires major revision

## Files Generated

- Model: `/models/beardipbuyer_v1.py`
- Profiles: Added to `/configs/profiles.yaml`
  - `exp013_beardipbuyer_2020`
  - `exp013_beardipbuyer_2022`
  - `exp013_beardipbuyer_2018`
- Results: `/results/analysis/20251125_090133/` (2020)
- Results: `/results/analysis/20251125_090149/` (2022)