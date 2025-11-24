# Deep Analysis: SectorRotationConsistent_v3 Performance & Improvement Strategies

**Date**: 2025-11-23
**Model**: SectorRotationConsistent_v3
**Current Performance**: 15.19% CAGR (Beats SPY's 14.34%)

---

## Performance Summary

The SectorRotationConsistent_v3 model successfully beats SPY with 15.19% CAGR, but at the cost of higher drawdowns (31.36% max) and extensive complexity. While it achieves its primary objective, there's significant room for improvement in risk management and implementation efficiency.

## Key Metrics Analysis

| Metric | Value | Assessment | Benchmark |
|--------|-------|------------|-----------|
| CAGR | 15.19% | **Good** - Beats SPY | SPY: 14.34% |
| Sharpe Ratio | 2.014 | **Excellent** - Strong risk-adjusted returns | Target: >1.5 |
| Max Drawdown | -31.36% | **Concerning** - Too deep for most investors | Target: <20% |
| Win Rate | 50.0% | **Adequate** - Room for improvement | Target: >55% |
| Total Trades | 1,356 | **High** - Potentially excessive | Optimal: <500 |
| BPS | 0.920 | **Good** - Solid composite score | Target: >0.80 |

## Strengths

1. **Adaptive Regime Detection**: 5-state regime system (steady_bull, volatile_bull, recovery, bear, concentrated) effectively adjusts to market conditions
2. **Crash Protection**: Fast crash detection (SPY -7% in 5 days OR VIX > 35) successfully reduces exposure during major drawdowns
3. **Risk-Adjusted Momentum**: Uses Sharpe-like scoring that penalizes volatile sectors, avoiding false signals from bouncing sectors
4. **Concentration Management**: Allows up to 50-60% concentration in winning sectors during strong trends

## Concerns

### 1. Excessive Drawdowns (31.36% Max)
**Analysis**: Major drawdown episodes identified:
- **2022-06-13 to 2023-07-17**: -31.36% over 399 days (bear market)
- **2023-09-11 to 2024-05-14**: -28.84% over 246 days (correction)

**Root Cause**: Crash protection triggers too late (VIX > 35 is extreme, SPY -7% in 5 days misses gradual declines)

### 2. Overtrading (1,356 Trades)
**Analysis**: Averaging ~270 trades/year vs optimal ~100 trades/year
**Root Cause**: Frequent rebalancing due to volatility-based rotation thresholds

### 3. Complexity Overhead
**Analysis**: 776 lines of code with 30+ parameters
**Root Cause**: Attempting to handle every market scenario with specific rules

### 4. Win Rate at 50%
**Analysis**: Coin flip probability suggests many trades lack edge
**Root Cause**: Trading noise rather than true momentum shifts

## Recommended Improvements

### 1. **Enhanced Drawdown Protection** - Expected Impact: Reduce max DD to <25%

**Implementation**:
```python
# Earlier crash detection
crash_drop_threshold: -0.05  # From -0.07 (trigger at -5% instead of -7%)
vix_crash_threshold: 30      # From 35 (trigger at VIX 30)
crash_drop_days: 3           # From 5 (faster detection)

# Gradual exposure reduction
if drawdown < -0.05: exposure = 0.75
if drawdown < -0.10: exposure = 0.50
if drawdown < -0.15: exposure = 0.25
```

**Rationale**: Current thresholds are too extreme. Gradual reduction preserves capital while maintaining upside participation.

### 2. **Reduce Trading Frequency** - Expected Impact: 50% fewer trades, lower costs

**Implementation**:
```python
# Increase minimum hold periods
min_hold_days_low_vol: 30    # From 15
min_hold_days_high_vol: 10   # From 5

# Wider rotation thresholds
rotation_threshold: 0.10     # From 0.05 (require 10% score difference)

# Monthly rebalancing only
if days_since_rebalance < 30: skip_rebalance
```

**Rationale**: Most rotation trades are noise. Requiring larger conviction reduces false signals.

### 3. **Simplify to Core Signals** - Expected Impact: Better maintainability, similar returns

**Remove**:
- Drawdown protection rules (redundant with crash protection)
- Concentration boost logic (overcomplicates)
- Multiple volatility regime states (consolidate to 2-3)

**Keep**:
- Core sector momentum ranking
- Crash protection (simplified)
- Basic regime detection (bull/bear)

### 4. **Dynamic Sector Count** - Expected Impact: +2-3% CAGR in trending markets

**Implementation**:
```python
# Scale positions with market strength
market_momentum = spy_126d_return
if market_momentum > 0.15:  # Strong bull
    top_n_sectors = 2  # Concentrate
elif market_momentum > 0.05:  # Normal bull
    top_n_sectors = 3  # Balanced
else:  # Bear or sideways
    top_n_sectors = 4  # Diversify
```

**Rationale**: Concentration works in strong trends, diversification needed in weak markets.

### 5. **Add Relative Strength Filter** - Expected Impact: Win rate >55%

**Implementation**:
```python
# Only trade sectors outperforming SPY
spy_momentum = calculate_momentum('SPY', period=126)
for sector in sectors:
    sector_momentum = calculate_momentum(sector, period=126)
    if sector_momentum < spy_momentum:
        exclude_sector(sector)  # Don't trade underperformers
```

**Rationale**: Why hold sectors weaker than the benchmark?

## Priority Actions

### Immediate (Test This Week):
1. **Run walk-forward optimization on crash thresholds**: Test VIX 25-35 range, SPY drop -3% to -7% range
2. **Backtest simplified V4**: Strip complexity, keep core momentum + basic crash protection

### Next Sprint:
1. **Implement gradual drawdown scaling**: Test linear vs step-function exposure reduction
2. **Add SPY relative strength filter**: Should immediately improve win rate
3. **Test monthly-only rebalancing**: Force 30-day minimum holds

## Expected Outcomes

With recommended improvements:
- **CAGR**: 16-17% (from dynamic positioning in trends)
- **Max Drawdown**: <25% (from earlier protection)
- **Sharpe**: >2.2 (from reduced volatility)
- **Trades**: <700 (from higher thresholds)
- **Win Rate**: >55% (from relative strength filter)

## Implementation Priority

1. **High Priority**: Drawdown protection improvements (biggest risk)
2. **Medium Priority**: Reduce trading frequency (cost savings)
3. **Low Priority**: Code simplification (maintenance benefit)

## Testing Protocol

```bash
# 1. Create V4 with improvements
cp models/sector_rotation_consistent_v3.py models/sector_rotation_consistent_v4.py

# 2. Run walk-forward validation
python3 -m engines.optimization.walk_forward_cli \
  --model SectorRotationConsistent_v4 \
  --param crash_drop_threshold=-0.05 \
  --param vix_crash_threshold=30 \
  --quick

# 3. Compare results
python3 -m backtest.analyze_cli --profile consistent_alpha_v3
python3 -m backtest.analyze_cli --profile consistent_alpha_v4
```

## Risk Assessment

**Risks of Changes**:
- Earlier crash triggers may exit during normal corrections (test on 2021 data)
- Higher rotation thresholds may miss valid momentum shifts (monitor sector dispersion)
- Simplification may remove edge cases that matter (validate on 2020 COVID period)

**Mitigation**: Use walk-forward validation on each change independently before combining.

## Conclusion

SectorRotationConsistent_v3 achieves its goal of beating SPY but with excessive complexity and risk. The recommended improvements focus on three pillars:

1. **Capital Preservation**: Earlier, gradual drawdown protection
2. **Signal Quality**: Higher conviction thresholds, relative strength filters
3. **Simplicity**: Remove redundant logic, focus on core momentum edge

Expected result: 16-17% CAGR with <25% drawdown and half the trades.

---

**Next Steps**:
1. Review and approve improvement plan
2. Implement V4 with priority changes
3. Run comprehensive walk-forward validation
4. Deploy to paper trading for live validation