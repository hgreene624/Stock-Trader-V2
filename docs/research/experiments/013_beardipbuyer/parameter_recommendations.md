# BearDipBuyer Parameter Recommendations

## Initial Parameter Sets

Based on Experiment 012 insights and bear market characteristics, here are recommended starting parameters for different market conditions.

## Primary Configurations

### 1. Panic Bear Configuration (2020-style)
**Use when**: VIX spikes above 35, sharp daily declines, capitulation volume

```yaml
panic_bear_config:
  # Aggressive panic detection
  vix_threshold: 28
  vix_spike_pct: 40
  rsi_oversold: 25
  price_below_ma_pct: 12

  # Looser quality filters (panic creates opportunities)
  min_trend_strength: -0.4
  min_correlation: 0.25

  # Aggressive sizing
  position_scale_max: 1.0
  position_scale_min: 0.5

  # Wider risk tolerance
  circuit_breaker_dd: -10
  max_volatility: 0.06

  # Fast recovery capture
  fast_momentum: 5
  slow_momentum: 20
  profit_target: 12
  max_holding_period: 15
```

**Rationale**:
- Lower VIX threshold (28) to catch early panic
- Allow weaker quality (-0.4 trend) since everything sells in panic
- Large positions (1.0x) to maximize violent rebounds
- Wider stops (-10%) to avoid whipsaws
- Short momentum (5-day) to capture V-bottoms

### 2. Choppy Bear Configuration (2018-style)
**Use when**: Multiple failed rallies, sector rotation, policy uncertainty

```yaml
choppy_bear_config:
  # Moderate panic detection
  vix_threshold: 32
  vix_spike_pct: 60
  rsi_oversold: 22
  price_below_ma_pct: 8

  # Strict quality filters (avoid traps)
  min_trend_strength: -0.25
  min_correlation: 0.35

  # Conservative sizing
  position_scale_max: 0.7
  position_scale_min: 0.3

  # Tight risk controls
  circuit_breaker_dd: -6
  max_volatility: 0.04

  # Balanced timing
  fast_momentum: 10
  slow_momentum: 30
  profit_target: 8
  max_holding_period: 10
```

**Rationale**:
- Higher VIX threshold (32) to avoid false signals
- Strict quality (0.35 correlation) to filter noise
- Moderate positions (0.7x) for flexibility
- Tight stops (-6%) for capital preservation
- Standard momentum (10/30) for reliable signals

### 3. Grinding Bear Configuration (2022-style)
**Use when**: Persistent selling, few bounces, macro headwinds

```yaml
grinding_bear_config:
  # Very selective panic detection
  vix_threshold: 35
  vix_spike_pct: 75
  rsi_oversold: 18
  price_below_ma_pct: 15

  # Ultra-strict quality filters
  min_trend_strength: -0.2
  min_correlation: 0.4

  # Minimal sizing
  position_scale_max: 0.5
  position_scale_min: 0.2

  # Very tight risk controls
  circuit_breaker_dd: -4
  max_volatility: 0.03

  # Defensive timing
  fast_momentum: 15
  slow_momentum: 45
  profit_target: 5
  max_holding_period: 7
```

**Rationale**:
- Very high VIX threshold (35) for true extremes only
- Strict quality (0.4 correlation) to ensure broad participation
- Small positions (0.5x) to minimize damage
- Very tight stops (-4%) for quick exits
- Slower momentum (15/45) to confirm real turns

## Adaptive Parameter Schedule

### VIX-Based Adjustments

```python
def adjust_for_vix(base_params, current_vix):
    params = base_params.copy()

    if current_vix > 40:  # Extreme panic
        params['rsi_oversold'] += 5  # Loosen to 30
        params['position_scale_max'] *= 1.3  # Increase size
        params['profit_target'] *= 1.5  # Bigger targets

    elif current_vix < 25:  # Low fear
        params['rsi_oversold'] -= 5  # Tighten to 20
        params['position_scale_max'] *= 0.7  # Reduce size
        params['circuit_breaker_dd'] *= 0.5  # Tighter stops

    return params
```

### Drawdown-Based Adjustments

```python
def adjust_for_drawdown(params, market_dd_pct):
    if market_dd_pct > 20:  # Deep drawdown
        params['vix_threshold'] -= 3  # More opportunities
        params['price_below_ma_pct'] += 3  # Look deeper

    elif market_dd_pct < 10:  # Shallow pullback
        params['vix_threshold'] += 3  # More selective
        params['min_correlation'] += 0.1  # Higher quality

    return params
```

## Parameter Optimization Priorities

### Phase 1: Core Thresholds
**Test first** (highest impact):
1. `vix_threshold`: [25, 28, 30, 32, 35]
2. `rsi_oversold`: [18, 20, 22, 25, 28, 30]
3. `position_scale_max`: [0.5, 0.7, 1.0, 1.3]

### Phase 2: Risk Controls
**Test second** (capital preservation):
1. `circuit_breaker_dd`: [-4, -6, -8, -10]
2. `max_volatility`: [0.03, 0.04, 0.05, 0.06]
3. `max_holding_period`: [7, 10, 15, 20]

### Phase 3: Quality Filters
**Test third** (fine-tuning):
1. `min_correlation`: [0.2, 0.3, 0.4]
2. `min_trend_strength`: [-0.4, -0.3, -0.2]
3. `momentum_periods`: [(5,20), (10,30), (15,45)]

## Parameter Combinations to Avoid

### Dangerous Combinations
❌ **Low VIX threshold + Large positions**
- Creates too many entries
- Capital depletes quickly
- Example: `vix_threshold=20` + `position_scale_max=1.3`

❌ **Tight stops + High volatility tolerance**
- Contradictory risk management
- Causes immediate stop-outs
- Example: `circuit_breaker_dd=-3` + `max_volatility=0.08`

❌ **Long holding + No momentum filter**
- Holds losing positions too long
- No exit trigger
- Example: `max_holding_period=30` + `momentum_check=false`

### Ineffective Combinations
⚠️ **Ultra-conservative everything**
- Never triggers entries
- Misses all opportunities
- Example: All parameters at most conservative

⚠️ **No quality filters + Aggressive sizing**
- Buys every dip regardless of quality
- Poor win rate
- Example: `min_correlation=0` + `position_scale_max=1.5`

## Recommended Testing Sequence

### Step 1: Baseline Test
Start with `choppy_bear_config` as it's middle-ground:
```bash
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --profile beardipbuyer_baseline \
    --start-date 2020-02-01 \
    --end-date 2020-05-31
```

### Step 2: Stress Test Extremes
Test panic configuration on 2020:
```bash
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --profile beardipbuyer_panic \
    --start-date 2020-02-19 \
    --end-date 2020-04-30
```

### Step 3: Optimize Key Parameters
Focus on VIX and RSI thresholds:
```yaml
optimization_grid:
  vix_threshold: [26, 28, 30, 32]
  rsi_oversold: [20, 23, 25, 28]
  # Keep others fixed at baseline
```

### Step 4: Validate Across Periods
Test optimized parameters on all three bear markets

## Expected Parameter Performance

### By Parameter Sensitivity

**High Sensitivity** (big impact):
- `vix_threshold`: ±3 points changes entry frequency 50%
- `position_scale_max`: ±0.3x changes returns 30%
- `circuit_breaker_dd`: ±2% changes survival rate 40%

**Medium Sensitivity**:
- `rsi_oversold`: ±5 points changes entry quality 20%
- `min_correlation`: ±0.1 changes selection 25%
- `profit_target`: ±3% changes holding period 30%

**Low Sensitivity** (fine-tuning):
- `momentum_periods`: ±5 days changes timing 10%
- `vol_window`: ±5 days changes smoothness 5%
- `reentry_cooldown`: ±2 days changes frequency 10%

## Production Parameter Profile

### Recommended Production Settings

After testing, create production profile:

```yaml
# configs/profiles/beardipbuyer_production.yaml
profile_name: beardipbuyer_production
model: BearDipBuyer_v1

parameters:
  # Core thresholds (optimized)
  vix_threshold: 30
  vix_spike_pct: 50
  rsi_oversold: 25
  price_below_ma_pct: 10

  # Quality filters (balanced)
  min_trend_strength: -0.3
  min_correlation: 0.3
  trend_lookback: 60
  correlation_window: 20

  # Risk management (protective)
  circuit_breaker_dd: -8
  max_volatility: 0.05
  vol_window: 20

  # Position sizing (adaptive)
  position_scale_max: 0.8
  position_scale_min: 0.3

  # Timing (responsive)
  fast_momentum: 10
  slow_momentum: 30
  profit_target: 10
  max_holding_period: 15
  reentry_cooldown: 5

  # Regime (sensitive)
  bear_confidence_threshold: 0.6
  bull_handoff_threshold: 0.3
  transition_period: 10

universe:
  - SPY
  - QQQ

regime_filter: "bear|high_volatility"
```

## Monitoring and Adjustment

### Key Metrics to Track

During live operation, monitor:

1. **Entry Frequency**
   - Target: 1-3 per month in bear markets
   - If > 5/month: Tighten thresholds
   - If < 1/month: Loosen thresholds

2. **Win Rate**
   - Target: > 60%
   - If < 50%: Improve quality filters
   - If > 80%: Might be too conservative

3. **Average Gain/Loss**
   - Target: 2:1 reward/risk
   - If < 1.5:1: Widen profit targets
   - If > 3:1: Tighten stops

### Adjustment Protocol

Monthly review and adjustment:
```python
def monthly_parameter_review(performance_metrics):
    if performance_metrics['win_rate'] < 0.5:
        increase_quality_filters()

    if performance_metrics['avg_drawdown'] > 10:
        tighten_risk_controls()

    if performance_metrics['missed_opportunities'] > 3:
        loosen_entry_thresholds()
```

---

*Document Version*: 1.0
*Last Updated*: 2025-11-25
*Next Review*: After initial testing