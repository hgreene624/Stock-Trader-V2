# Parameter Grid Specifications for Feature Testing

## Base Parameters (All Variants)

```yaml
# Inherited from BearDefensiveRotation_v2
base_parameters:
  universe: ["XLU", "XLP", "TLT", "GLD", "UUP", "SHY"]
  momentum_period: 20  # May be modified in V4
  rebalance_frequency: "daily"
  min_momentum: -0.10  # Assets must be > -10% over period
  cash_asset: "SHY"
  max_positions: 3
```

## Variant 3: Risk Management Parameters

### Grid Definition
```yaml
v3_parameter_grid:
  # Volatility targeting
  target_vol:
    values: [0.10, 0.15, 0.20]
    description: "Target annualized volatility"
    rationale: "Lower = more conservative, Higher = more aggressive"

  # Drawdown circuit breaker
  dd_threshold:
    values: [-0.08, -0.10, -0.12]
    description: "Maximum drawdown before cash exit"
    rationale: "-8% aggressive stop, -12% loose stop"

  # Additional parameters
  vol_lookback:
    fixed: 20
    description: "Days for volatility calculation"

  dd_lookback:
    fixed: 252
    description: "Days for rolling max NAV (1 year)"

  reset_threshold:
    fixed: 0.95
    description: "NAV recovery level to reset from cash (95% of previous peak)"
```

### Total Combinations: 3 × 3 = 9

### Implementation Notes
```python
# Volatility scaling formula
position_scale = min(1.0, target_vol / realized_vol)
final_weight = base_weight * position_scale

# Drawdown calculation
rolling_peak = nav_series.rolling(dd_lookback).max()
current_dd = (current_nav / rolling_peak) - 1

# Circuit breaker logic
if current_dd < dd_threshold:
    in_protection_mode = True
    return {"SHY": 1.0}

# Reset logic
if in_protection_mode and current_nav > rolling_peak * reset_threshold:
    in_protection_mode = False
```

## Variant 4: Recovery Enhancement Parameters

### Grid Definition
```yaml
v4_parameter_grid:
  # VIX-based recovery detection
  vix_panic_threshold:
    values: [35, 40, 45]
    description: "VIX level indicating market panic"
    rationale: "35 = sensitive, 45 = only extreme panic"

  vix_recovery_ratio:
    values: [0.65, 0.70, 0.75]
    description: "Fraction of peak VIX indicating recovery"
    rationale: "0.65 = aggressive re-entry, 0.75 = conservative"

  # Faster momentum
  momentum_period:
    values: [15, 17, 20]
    description: "Days for momentum calculation"
    rationale: "15 = responsive, 20 = stable (baseline)"

  # Additional parameters
  vix_lookback:
    fixed: 30
    description: "Days to find VIX peak"

  recovery_boost:
    fixed: 1.5
    description: "Position size multiplier during recovery"

  recovery_duration:
    fixed: 20
    description: "Days to maintain recovery mode"
```

### Total Combinations: 3 × 3 × 3 = 27

### Implementation Notes
```python
# VIX recovery detection
vix_peak = vix_series[-vix_lookback:].max()
current_vix = vix_series[-1]

if vix_peak > vix_panic_threshold:
    if current_vix < vix_peak * vix_recovery_ratio:
        recovery_mode = True
        recovery_mode_start = current_date

# Position adjustment in recovery mode
if recovery_mode:
    days_in_recovery = (current_date - recovery_mode_start).days
    if days_in_recovery <= recovery_duration:
        position_multiplier = recovery_boost
    else:
        recovery_mode = False
```

## Variant 5: Quality Filters Parameters

### Grid Definition
```yaml
v5_parameter_grid:
  # Trend strength requirements
  min_momentum_10d:
    values: [-0.05, -0.03, -0.01]
    description: "Minimum 10-day momentum for eligibility"
    rationale: "-5% = loose filter, -1% = strict filter"

  min_momentum_20d:
    values: [-0.05, -0.03, -0.01]
    description: "Minimum 20-day momentum for eligibility"
    rationale: "Must align with 10d for consistency"

  # Correlation-based sizing
  correlation_scale:
    values: [0.3, 0.5, 0.7]
    description: "Scaling factor for correlation adjustment"
    rationale: "0.3 = minor adjustment, 0.7 = major adjustment"

  # Additional parameters
  correlation_window:
    fixed: 60
    description: "Days for correlation calculation"

  min_eligible_assets:
    fixed: 2
    description: "Minimum assets passing filters"

  fallback_action:
    fixed: "cash"
    description: "Action when too few assets qualify"
```

### Total Combinations: 3 × 3 × 3 = 27

### Implementation Notes
```python
# Trend strength filtering
eligible_assets = []
for asset in universe:
    momentum_10d = (price[-1] / price[-11]) - 1
    momentum_20d = (price[-1] / price[-21]) - 1

    if momentum_10d > min_momentum_10d and momentum_20d > min_momentum_20d:
        eligible_assets.append(asset)

# Correlation adjustment
if len(eligible_assets) >= min_eligible_assets:
    corr_matrix = compute_correlation(eligible_assets, correlation_window)
    avg_correlation = corr_matrix.mean().mean()

    # Scale positions based on correlation
    position_scale = 1 - (avg_correlation * correlation_scale)
    position_scale = max(0.3, min(1.0, position_scale))  # Bounded
else:
    return {"SHY": 1.0}  # Fallback to cash
```

## Variant 6: Best of Breed Parameters

### Selection Criteria
```yaml
v6_selection_process:
  step1_analyze:
    description: "Identify best parameters from V3-V5"
    metrics: ["2018_improvement", "2020_preservation", "2022_consistency"]

  step2_combine:
    description: "Test feature interactions"
    approach: "Start with best individual, add incrementally"

  step3_optimize:
    description: "Fine-tune combined parameters"
    method: "Grid search on reduced range around best values"
```

### Expected Configuration (TBD)
```yaml
v6_expected_parameters:
  # From V3 (if successful)
  target_vol: TBD  # Likely 0.15
  dd_threshold: TBD  # Likely -0.10

  # From V4 (if successful)
  vix_panic_threshold: TBD  # Likely 40
  vix_recovery_ratio: TBD  # Likely 0.70

  # From V5 (if successful)
  min_momentum_20d: TBD  # Likely -0.03
  correlation_scale: TBD  # Likely 0.5

  # Feature precedence
  precedence_rules:
    1: "Drawdown breaker overrides all"
    2: "VIX recovery overrides correlation"
    3: "Quality filters apply unless overridden"
```

## Testing Period Specifications

### 2018 Q4: Choppy Decline
```yaml
2018_Q4:
  start: "2018-10-01"
  end: "2018-12-31"
  characteristics:
    - "Multiple failed rallies"
    - "High correlation across assets"
    - "VIX spikes to 36"
  baseline_v2_result: -21.70%
  target_improvement: > -12%
```

### 2020 COVID: Sharp V-Recovery
```yaml
2020_COVID:
  start: "2020-02-01"
  end: "2020-04-30"
  characteristics:
    - "Fastest decline in history"
    - "VIX spike to 85"
    - "Dramatic V-shaped recovery"
  baseline_v2_result: +5.74%
  minimum_acceptable: > +4%
  target_improvement: > +8%
```

### 2022 Bear: Persistent Decline
```yaml
2022_BEAR:
  start: "2022-01-01"
  end: "2022-12-31"
  characteristics:
    - "Steady grind lower"
    - "No dramatic VIX spikes"
    - "Few sharp rallies"
  baseline_v2_result: -5.23%
  maximum_acceptable: < -7%
  target_improvement: > -3%
```

## Quick Test Commands

### Single Parameter Test
```bash
# Test specific parameter combination
python3 -m backtest.analyze_cli \
  --model BearDefensiveRotation_v3 \
  --params "target_vol=0.15,dd_threshold=-0.10" \
  --start 2018-10-01 --end 2018-12-31
```

### Batch Testing Script
```bash
#!/bin/bash
# save as run_v3_tests.sh

MODEL="BearDefensiveRotation_v3"
PERIODS=("2018-10-01:2018-12-31" "2020-02-01:2020-04-30" "2022-01-01:2022-12-31")

for VOL in 0.10 0.15 0.20; do
  for DD in 0.08 0.10 0.12; do
    for PERIOD in "${PERIODS[@]}"; do
      START="${PERIOD%:*}"
      END="${PERIOD#*:}"

      echo "Testing VOL=$VOL DD=$DD for $START to $END"

      python3 -m backtest.analyze_cli \
        --model $MODEL \
        --params "target_vol=$VOL,dd_threshold=-$DD" \
        --start $START --end $END \
        --output "results/v3_vol${VOL}_dd${DD}_${START}.json"
    done
  done
done
```

## Parameter Sensitivity Analysis

### Expected Sensitivities

**Target Volatility (V3)**:
- Lower values → More stable returns, lower overall CAGR
- Higher values → Better recovery capture, worse drawdowns
- Sweet spot likely around 0.15

**Drawdown Threshold (V3)**:
- Tighter (-8%) → More cash time, missed opportunities
- Looser (-12%) → Better recovery capture, larger losses
- Balance protection vs opportunity

**VIX Thresholds (V4)**:
- Lower panic level → More frequent signals, possible false positives
- Higher panic level → Only extreme events, might miss smaller recoveries
- Recovery ratio determines re-entry aggressiveness

**Momentum Periods (V4/V5)**:
- Shorter → More responsive, more whipsaws
- Longer → More stable, slower to adapt
- 15-20 days likely optimal range

**Correlation Scale (V5)**:
- Lower → Minor position adjustments
- Higher → Significant exposure changes
- Risk of over-reaction at high values