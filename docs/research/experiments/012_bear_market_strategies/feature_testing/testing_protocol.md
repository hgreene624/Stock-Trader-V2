# Testing Protocol for Experiment 012b: Feature Testing

## Pre-Test Validation

### 1. Data Verification
```bash
# Ensure all required data is available
python3 -m engines.data.cli validate --symbols XLU,XLP,TLT,GLD,UUP,SHY,SPY --start 2018-01-01 --end 2023-01-01

# Download VIX data if needed for V4
python3 -m engines.data.cli download --symbols ^VIX --start 2018-01-01
```

### 2. Baseline Confirmation
```bash
# Verify V2 baseline performance matches expectations
python3 -m backtest.analyze_cli --model BearDefensiveRotation_v2 --start 2018-10-01 --end 2018-12-31
# Expected: ~-21.70%

python3 -m backtest.analyze_cli --model BearDefensiveRotation_v2 --start 2020-02-01 --end 2020-04-30
# Expected: ~+5.74%

python3 -m backtest.analyze_cli --model BearDefensiveRotation_v2 --start 2022-01-01 --end 2022-12-31
# Expected: ~-5.23%
```

## Variant 3: Risk Management Testing

### Step 1: Create Model File
```python
# Create models/bear_defensive_rotation_v3.py
# Copy V2 and add volatility sizing + drawdown breaker features
```

### Step 2: Configure Parameters
```yaml
# Add to configs/profiles.yaml
bear_defensive_v3_test1:
  model: BearDefensiveRotation_v3
  parameters:
    target_vol: 0.10
    dd_threshold: -0.08
    momentum_period: 20
    rebalance_frequency: "daily"

bear_defensive_v3_test2:
  model: BearDefensiveRotation_v3
  parameters:
    target_vol: 0.15
    dd_threshold: -0.10
    momentum_period: 20
    rebalance_frequency: "daily"
```

### Step 3: Run Test Matrix
```bash
# For each parameter combination (9 total)
for VOL in 0.10 0.15 0.20; do
  for DD in -0.08 -0.10 -0.12; do
    # Test 2018 Q4
    python3 -m backtest.analyze_cli \
      --profile bear_defensive_v3 \
      --param-override "target_vol=$VOL,dd_threshold=$DD" \
      --start 2018-10-01 --end 2018-12-31 \
      --output results_v3_2018_vol${VOL}_dd${DD}.json

    # Test 2020 COVID
    python3 -m backtest.analyze_cli \
      --profile bear_defensive_v3 \
      --param-override "target_vol=$VOL,dd_threshold=$DD" \
      --start 2020-02-01 --end 2020-04-30 \
      --output results_v3_2020_vol${VOL}_dd${DD}.json

    # Test 2022 Bear
    python3 -m backtest.analyze_cli \
      --profile bear_defensive_v3 \
      --param-override "target_vol=$VOL,dd_threshold=$DD" \
      --start 2022-01-01 --end 2022-12-31 \
      --output results_v3_2022_vol${VOL}_dd${DD}.json
  done
done
```

### Step 4: Document Results
```bash
# Create summary in v3_risk_management/README.md
# Include table of all 9 combinations across 3 periods
```

## Variant 4: Recovery Enhancement Testing

### Step 1: Create Model File
```python
# Create models/bear_defensive_rotation_v4.py
# Add VIX recovery detection + faster momentum
```

### Step 2: Extended Parameter Grid
```bash
# 3x3x3 = 27 combinations per period
for VIX_PANIC in 35 40 45; do
  for VIX_RECOVERY in 0.65 0.70 0.75; do
    for MOMENTUM in 15 17 20; do
      # Run tests for each period
      # Document in results_v4_*.json
    done
  done
done
```

### Step 3: VIX Feature Validation
```python
# Verify VIX signals are firing correctly
# Check logs for recovery override triggers
# Count: How many times did VIX override fire in 2020?
```

## Variant 5: Quality Filters Testing

### Step 1: Create Model File
```python
# Create models/bear_defensive_rotation_v5.py
# Add trend strength filter + correlation sizing
```

### Step 2: Correlation Testing
```python
# Pre-compute correlation matrices for test periods
import pandas as pd
import numpy as np

# Load defensive asset returns
symbols = ['XLU', 'XLP', 'TLT', 'GLD', 'UUP', 'SHY']
for period in ['2018-Q4', '2020-COVID', '2022-BEAR']:
    corr_matrix = compute_correlation(symbols, period)
    print(f"{period} avg correlation: {corr_matrix.mean():.3f}")
```

### Step 3: Run Quality Filter Tests
```bash
# Test different filter thresholds
# Document impact on trade frequency
```

## Variant 6: Best of Breed Testing

### Step 1: Analyze V3-V5 Results
```python
# Identify best performing features
best_features = {
    'risk_mgmt': None,  # Best from V3
    'recovery': None,    # Best from V4
    'quality': None      # Best from V5
}
```

### Step 2: Create Combined Model
```python
# Create models/bear_defensive_rotation_v6.py
# Combine successful features with precedence rules
```

### Step 3: Validation Testing
```bash
# Test on all 3 periods
# Also test on 2008 as out-of-sample
python3 -m backtest.analyze_cli \
  --model BearDefensiveRotation_v6 \
  --start 2008-09-01 --end 2009-03-31
```

## Results Collection

### For Each Test Run, Capture:

1. **Core Metrics**
   - CAGR
   - Sharpe Ratio
   - Max Drawdown
   - Recovery time (days to new high)

2. **Trade Analytics**
   - Total trades
   - Win rate
   - Average hold period
   - Asset allocation distribution

3. **Feature-Specific Metrics**
   - V3: Volatility scaling frequency, circuit breaker triggers
   - V4: VIX override count, recovery capture speed
   - V5: Filtered trade %, correlation levels
   - V6: Feature interaction frequency

### Results Storage Structure
```
feature_testing/
├── v3_risk_management/
│   ├── README.md           # Summary and best parameters
│   ├── raw_results/        # JSON output files
│   └── analysis.ipynb      # Detailed analysis
├── v4_recovery_enhancement/
│   ├── README.md
│   ├── raw_results/
│   └── vix_signal_log.csv  # VIX trigger history
├── v5_quality_filters/
│   ├── README.md
│   ├── raw_results/
│   └── correlation_analysis.csv
└── v6_best_of_breed/
    ├── README.md
    ├── final_model.py      # Production-ready code
    └── validation_results/  # Including 2008 OOS
```

## Quality Checks

### After Each Variant:
1. **Sanity Check**: Results should be directionally correct
   - Risk features → Lower volatility
   - Recovery features → Better bounce capture
   - Quality features → Fewer trades

2. **Cross-Period Consistency**:
   - No parameter set should have wildly different ranks across periods
   - Watch for overfitting signs (one period dominance)

3. **Feature Independence**:
   - Features should have incremental effects
   - If adding feature B negates feature A, investigate

## Troubleshooting

### Common Issues:

1. **VIX Data Missing**
   ```bash
   python3 -m engines.data.cli download --symbols ^VIX --start 2018-01-01
   ```

2. **Circuit Breaker Too Aggressive**
   - Check if model is stuck in cash
   - Verify reset conditions

3. **Correlation Calculation Slow**
   - Pre-compute and cache matrices
   - Use rolling window approximation

4. **Results Don't Match Expectations**
   - Verify data alignment
   - Check for look-ahead bias
   - Confirm feature implementation

## Final Checklist

Before declaring experiment complete:

- [ ] All 192 tests completed
- [ ] Results documented in standard format
- [ ] Best parameters identified for each variant
- [ ] V6 created with optimal combination
- [ ] Out-of-sample validation on 2008
- [ ] Production-ready code with no TODOs
- [ ] Risk assessment updated with findings
- [ ] Recommendation document created
- [ ] Git commit with full reproducibility info