# Testing Protocol: BearDipBuyer Experiment 013

## Overview

Systematic testing protocol for BearDipBuyer_v1, an opportunistic bear market profit model. This protocol ensures rigorous validation across different bear market types and integration scenarios.

## Test Environment Setup

### Data Requirements
```bash
# Ensure all data is downloaded
python3 -m engines.data.cli download --symbols SPY,QQQ,VIX --start-date 2017-01-01 --timeframe 1D

# Verify VIX data availability
python3 -m engines.data.cli validate --symbols VIX
```

### Model Registration
```python
# In backtest/analyze_cli.py
models_to_test = {
    'BearDipBuyer_v1': 'models.beardipbuyer_v1.BearDipBuyer_v1',
    'BearDipBuyer_v2': 'models.beardipbuyer_v2.BearDipBuyer_v2',  # If refinements needed
}
```

## Phase 1: Individual Bear Market Tests (Days 1-3)

### Test 1A: 2020 COVID Crash - Panic V-Recovery
**Period**: 2020-02-19 to 2020-04-30
**Character**: Sharp panic sell-off, extreme VIX spike, V-shaped recovery

```bash
# Baseline SPY performance
python3 -m backtest.analyze_cli \
    --model SPY \
    --start-date 2020-02-19 \
    --end-date 2020-04-30 \
    --initial-capital 100000

# Test aggressive panic-buying configuration
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --start-date 2020-02-19 \
    --end-date 2020-04-30 \
    --params vix_threshold=30,rsi_oversold=25,position_scale_max=1.0
```

**Success Metrics**:
- Target CAGR: +8% to +12%
- Must capture March 23 bottom (within 3 days)
- Max drawdown: < -12%
- Should make 3-5 aggressive entries

**Key Dates to Monitor**:
- Feb 19: Market peak
- Mar 16: First circuit breaker day
- Mar 23: Absolute bottom
- Apr 30: Recovery checkpoint

### Test 1B: 2018 Q4 Correction - Choppy Decline
**Period**: 2018-10-01 to 2018-12-31
**Character**: Multiple false bottoms, choppy action, Fed policy fears

```bash
# Test quality-filtered approach
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --start-date 2018-10-01 \
    --end-date 2018-12-31 \
    --params min_correlation=0.3,trend_lookback=60,circuit_breaker_dd=-6
```

**Success Metrics**:
- Target CAGR: +5% to +8%
- Win rate: > 60%
- Avoid whipsaws (< 10 trades)
- Better than -8% drawdown

**Key Dates**:
- Oct 3: Initial peak
- Oct 29: First bottom attempt
- Nov 23: Second leg down
- Dec 24: Christmas Eve bottom

### Test 1C: 2022 Rate Hike Bear - Grinding Decline
**Period**: 2022-01-01 to 2022-10-31
**Character**: Persistent selling, few rebounds, inflation/rate fears

```bash
# Test defensive configuration
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --start-date 2022-01-01 \
    --end-date 2022-10-31 \
    --params vix_threshold=35,rsi_oversold=20,position_scale_max=0.5
```

**Success Metrics**:
- Target: Minimize losses (-5% to 0%)
- Few false entries (< 5 trades)
- Quick exits on failed bounces
- Preserve capital for real bottom

## Phase 2: Multi-Year Validation (Days 4-5)

### Test 2A: Transition Periods
**2018-2020**: Correction → Recovery → COVID crash

```bash
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --start-date 2018-01-01 \
    --end-date 2020-12-31 \
    --params vix_threshold=30,adaptive_regime=true
```

**Validation Points**:
- Proper activation during bear regimes
- Dormancy during 2019 bull run
- Quick reactivation for COVID

### Test 2B: Extended Bear Markets
**2000-2003**: Dot-com crash (if data available)
**2007-2009**: Financial crisis

```bash
# Historical validation
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --start-date 2007-01-01 \
    --end-date 2009-12-31
```

### Test 2C: Parameter Optimization Grid

```yaml
# configs/experiments/exp_013_beardipbuyer.yaml
experiment:
  name: beardipbuyer_optimization
  model: BearDipBuyer_v1
  method: grid

  parameter_grid:
    vix_threshold: [25, 30, 35]
    rsi_oversold: [20, 25, 30]
    price_below_ma_pct: [8, 10, 12]
    position_scale_max: [0.5, 0.75, 1.0]
    circuit_breaker_dd: [-6, -8, -10]

  backtest_config:
    start_date: "2020-02-01"
    end_date: "2020-05-31"
    initial_capital: 100000

  optimization_metric: bps
```

```bash
# Run optimization
python3 -m engines.optimization.cli run \
    --experiment configs/experiments/exp_013_beardipbuyer.yaml
```

## Phase 3: Portfolio Integration (Days 6-7)

### Test 3A: Dual Model System
Combine BearDipBuyer with SectorRotationModel

```python
# configs/profiles/integrated_bear_system.yaml
models:
  - name: SectorRotationModel_v1
    weight: 0.7
    regime_filter: "bull|neutral"

  - name: BearDipBuyer_v1
    weight: 0.3
    regime_filter: "bear|high_volatility"
```

### Test 3B: Regime Handoff Mechanics

```python
# Test transition smoothness
def test_regime_transition():
    # 1. Start in bull (SectorRotation active)
    # 2. Transition to bear (BearDipBuyer activates)
    # 3. Measure handoff period performance
    # 4. Return to bull (SectorRotation reactivates)
```

### Test 3C: Full Historical Backtest
**2018-2024**: Complete cycle test

```bash
# Integrated system test
python3 -m backtest.analyze_cli \
    --model IntegratedBearSystem \
    --start-date 2018-01-01 \
    --end-date 2024-11-24 \
    --compare-to SPY,SectorRotationModel_v1
```

## Validation Checkpoints

### After Each Test Phase

1. **Performance Review**
   ```python
   # Generate performance report
   python3 -m backtest.cli show-last --detailed
   ```

2. **Trade Analysis**
   - Entry timing accuracy
   - Exit efficiency
   - Position sizing appropriateness
   - Win/loss distribution

3. **Risk Metrics**
   - Maximum drawdown periods
   - Volatility during positions
   - Correlation with market
   - Tail risk exposure

## Progressive Refinement Protocol

### If Test 1A (COVID) Fails:
1. Lower VIX threshold (try 25)
2. Increase RSI oversold (try 30)
3. Add volume confirmation
4. Reduce position size

### If Test 1B (2018) Fails:
1. Tighten quality filters
2. Increase correlation threshold
3. Add trend strength minimum
4. Shorten momentum windows

### If Test 1C (2022) Fails:
1. Raise all thresholds (more selective)
2. Reduce max position size
3. Tighten circuit breakers
4. Add inflation indicators

## Documentation Requirements

### After Each Test:
1. Update experiment README with results
2. Log parameter configurations that worked/failed
3. Document market condition observations
4. Save best configurations as profiles

### Trade Journal Entry Format:
```markdown
**Date**: YYYY-MM-DD
**Signal**: Panic/Quality/Tactical
**Entry**: Price, RSI, VIX
**Exit**: Reason (target/stop/time)
**Result**: P&L %, lessons learned
```

## Final Validation Checklist

Before declaring model ready:

- [ ] Positive CAGR in 2+ bear markets
- [ ] Better than -15% max drawdown
- [ ] 60%+ win rate on dip buys
- [ ] Successful integration test
- [ ] Documented parameter rationale
- [ ] Code committed with version tag
- [ ] Profile saved for production
- [ ] Handoff mechanics validated
- [ ] Risk controls verified
- [ ] Performance vs baseline documented

## Monitoring During Tests

```bash
# Watch test progress
tail -f logs/backtest_*.log

# Monitor trades in real-time
python3 -c "
import pandas as pd
import time
while True:
    df = pd.read_csv('results/trades_latest.csv')
    print(df.tail())
    time.sleep(5)
"
```

## Emergency Protocols

If model shows extreme behavior:
1. Stop test immediately (Ctrl+C)
2. Review last 10 trades
3. Check for data issues
4. Verify calculation logic
5. Reduce position sizes and retest

## Notes on Expected Behaviors

### Good Signs:
- Aggressive buying after VIX spikes
- Quick profits on violent rebounds
- Sitting out grinding declines
- Clean handoffs to/from bull models

### Warning Signs:
- Buying every small dip
- Holding losing positions too long
- Conflicting with other models
- Excessive turnover

## Test Completion Criteria

Model is ready when:
1. All three bear periods tested
2. Multi-year validation complete
3. Integration successful
4. Documentation complete
5. Best parameters identified
6. Production profile created

---

*Protocol Version*: 1.0
*Last Updated*: 2025-11-25
*Next Review*: After Phase 1 completion