# BearDipBuyer Implementation Plan

## Quick Start Commands

```bash
# 1. Create model file
cp models/base.py models/beardipbuyer_v1.py

# 2. Register in CLI
# Edit backtest/analyze_cli.py to add BearDipBuyer_v1

# 3. Create test profile
# Add to configs/profiles.yaml

# 4. Run first test
python3 -m backtest.analyze_cli --profile beardipbuyer_2020

# 5. View results
python3 -m backtest.cli show-last
```

## Day 1: Model Implementation (4-6 hours)

### Task 1.1: Create Base Model Structure
```python
# models/beardipbuyer_v1.py
from models.base import BaseModel, Context
import numpy as np
import pandas as pd

class BearDipBuyer_v1(BaseModel):
    def __init__(self, config: dict):
        super().__init__(config)
        # Load parameters
        self.vix_threshold = config['parameters'].get('vix_threshold', 30)
        self.rsi_oversold = config['parameters'].get('rsi_oversold', 25)
        # ... all parameters

    def generate_weights(self, context: Context) -> Dict[str, float]:
        # Implementation here
        pass
```

### Task 1.2: Implement Panic Detection
```python
def detect_panic_level(self, context: Context) -> int:
    """
    Returns panic level 0-3 based on VIX and market conditions
    """
    # Get VIX from context
    vix = context.asset_features.get('VIX', {}).get('close', 0)

    # Calculate VIX spike
    vix_history = context.get_historical('VIX', 'close', 5)
    vix_spike = (vix - vix_history.mean()) / vix_history.mean() * 100

    # Determine panic level
    if vix > 35 or vix_spike > 75:
        return 3  # EXTREME
    elif vix > 30 or vix_spike > 50:
        return 2  # HIGH
    elif vix > 25 or vix_spike > 30:
        return 1  # MODERATE
    else:
        return 0  # NONE
```

### Task 1.3: Implement Quality Filters
```python
def assess_quality(self, symbol: str, context: Context) -> float:
    """
    Returns quality score 0-1 for a symbol
    """
    features = context.asset_features[symbol]

    # Trend strength
    prices = context.get_historical(symbol, 'close', 60)
    trend = np.polyfit(range(len(prices)), prices, 1)[0]

    # Correlation with SPY
    spy_prices = context.get_historical('SPY', 'close', 20)
    correlation = np.corrcoef(prices[-20:], spy_prices)[0, 1]

    # Relative strength
    symbol_return = (prices[-1] / prices[-20] - 1)
    spy_return = (spy_prices[-1] / spy_prices[-20] - 1)
    rel_strength = symbol_return - spy_return

    # Combine scores
    quality = (
        max(0, min(1, trend + 0.5)) * 0.3 +
        correlation * 0.4 +
        max(0, min(1, rel_strength + 0.5)) * 0.3
    )

    return quality
```

### Task 1.4: Register Model in CLI
```python
# backtest/analyze_cli.py
# Add to MODEL_CLASSES dict
'BearDipBuyer_v1': 'models.beardipbuyer_v1.BearDipBuyer_v1',
```

## Day 2: VIX Integration & Testing Setup (3-4 hours)

### Task 2.1: Add VIX Data Download
```bash
# Download VIX data
python3 -m engines.data.cli download \
    --symbols VIX \
    --asset-class equity \
    --start 2017-01-01 \
    --timeframe 1D
```

### Task 2.2: Create Test Profiles
```yaml
# Add to configs/profiles.yaml

beardipbuyer_2020:
  model: BearDipBuyer_v1
  start_date: "2020-02-19"
  end_date: "2020-04-30"
  initial_capital: 100000
  universe: [SPY, QQQ]
  parameters:
    vix_threshold: 28
    rsi_oversold: 25
    position_scale_max: 1.0
    circuit_breaker_dd: -10

beardipbuyer_2018:
  model: BearDipBuyer_v1
  start_date: "2018-10-01"
  end_date: "2018-12-31"
  initial_capital: 100000
  universe: [SPY, QQQ]
  parameters:
    vix_threshold: 32
    rsi_oversold: 22
    position_scale_max: 0.7
    circuit_breaker_dd: -6

beardipbuyer_2022:
  model: BearDipBuyer_v1
  start_date: "2022-01-01"
  end_date: "2022-10-31"
  initial_capital: 100000
  universe: [SPY, QQQ]
  parameters:
    vix_threshold: 35
    rsi_oversold: 18
    position_scale_max: 0.5
    circuit_breaker_dd: -4
```

### Task 2.3: Run Initial Tests
```bash
# Test 2020 COVID
python3 -m backtest.analyze_cli --profile beardipbuyer_2020

# Check results
python3 -m backtest.cli show-last

# If successful, test 2018
python3 -m backtest.analyze_cli --profile beardipbuyer_2018
```

## Day 3: Refinement & Optimization (4-5 hours)

### Task 3.1: Analyze Initial Results
```python
# Script to analyze trades
import pandas as pd
import json

# Load results
with open('results/last_run/metadata.json', 'r') as f:
    metadata = json.load(f)

trades = pd.read_csv('results/last_run/trades.csv')

# Analyze entry timing
print("Entry dates vs market bottoms:")
print(trades[['entry_date', 'exit_date', 'pnl_pct']].head(10))

# Check panic detection accuracy
print("Panic level distribution:")
print(trades['entry_reason'].value_counts())
```

### Task 3.2: Create Optimization Config
```yaml
# configs/experiments/exp_013_beardipbuyer.yaml
experiment:
  name: beardipbuyer_optimization
  model: BearDipBuyer_v1
  method: grid
  n_jobs: 4

  parameter_grid:
    vix_threshold: [26, 28, 30, 32]
    rsi_oversold: [20, 23, 25, 28]
    position_scale_max: [0.7, 0.85, 1.0]
    circuit_breaker_dd: [-6, -8, -10]

  backtest_config:
    start_date: "2020-02-19"
    end_date: "2020-04-30"
    initial_capital: 100000
    universe: [SPY, QQQ]

  optimization_metric: bps
  top_n_results: 10
```

### Task 3.3: Run Optimization
```bash
# Run parameter optimization
python3 -m engines.optimization.cli run \
    --experiment configs/experiments/exp_013_beardipbuyer.yaml

# Query results
duckdb results/exp_013_beardipbuyer.db
> SELECT * FROM results ORDER BY bps DESC LIMIT 10;
```

## Day 4-5: Multi-Period Validation (6-8 hours)

### Task 4.1: Extended Period Testing
```bash
# Test 2018-2020 full period
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --start-date 2018-01-01 \
    --end-date 2020-12-31 \
    --params "vix_threshold=30,rsi_oversold=25"

# Test 2020-2024 full period
python3 -m backtest.analyze_cli \
    --model BearDipBuyer_v1 \
    --start-date 2020-01-01 \
    --end-date 2024-11-24 \
    --params "vix_threshold=30,rsi_oversold=25"
```

### Task 4.2: Walk-Forward Validation
```bash
# Use walk-forward to prevent overfitting
python3 -m engines.optimization.walk_forward_cli \
    --model BearDipBuyer_v1 \
    --train-start 2018-01-01 \
    --train-end 2020-12-31 \
    --test-start 2021-01-01 \
    --test-end 2024-11-24 \
    --params "vix_threshold=30,rsi_oversold=25"
```

### Task 4.3: Document Best Parameters
```python
# Save best configuration
best_params = {
    'vix_threshold': 30,
    'rsi_oversold': 25,
    'position_scale_max': 0.85,
    'circuit_breaker_dd': -8,
    # ... all optimized parameters
}

# Create production profile
with open('configs/profiles/beardipbuyer_production.yaml', 'w') as f:
    yaml.dump(best_config, f)
```

## Day 6-7: Integration Testing (6-8 hours)

### Task 6.1: Create Integrated Model System
```python
# models/integrated_bear_system.py
class IntegratedBearSystem(BaseModel):
    def __init__(self, config):
        self.sector_rotation = SectorRotationModel_v1(config)
        self.bear_dip_buyer = BearDipBuyer_v1(config)

    def generate_weights(self, context):
        # Get regime confidence
        bear_confidence = self.calculate_bear_confidence(context)

        if bear_confidence > 0.7:
            # Bear market - use dip buyer
            return self.bear_dip_buyer.generate_weights(context)
        elif bear_confidence > 0.3:
            # Transition - blend models
            bear_weights = self.bear_dip_buyer.generate_weights(context)
            bull_weights = self.sector_rotation.generate_weights(context)
            return self.blend_weights(bear_weights, bull_weights, bear_confidence)
        else:
            # Bull market - use sector rotation
            return self.sector_rotation.generate_weights(context)
```

### Task 6.2: Test Regime Transitions
```bash
# Test transition period (2020 recovery)
python3 -m backtest.analyze_cli \
    --model IntegratedBearSystem \
    --start-date 2020-03-01 \
    --end-date 2020-08-31

# Test full cycle (2019-2021)
python3 -m backtest.analyze_cli \
    --model IntegratedBearSystem \
    --start-date 2019-01-01 \
    --end-date 2021-12-31
```

### Task 6.3: Compare Performance
```python
# Compare standalone vs integrated
results_standalone = run_backtest('BearDipBuyer_v1')
results_integrated = run_backtest('IntegratedBearSystem')
results_baseline = run_backtest('SectorRotationModel_v1')

print("Performance Comparison:")
print(f"BearDipBuyer alone: {results_standalone['cagr']:.2%}")
print(f"Integrated System: {results_integrated['cagr']:.2%}")
print(f"SectorRotation alone: {results_baseline['cagr']:.2%}")
```

## Day 8: Final Report & Production Prep (3-4 hours)

### Task 8.1: Generate Final Report
```markdown
# docs/research/experiments/013_beardipbuyer/FINAL_REPORT.md

## Results Summary
- 2020 COVID: +X.X% CAGR (Target: +8-12%)
- 2018 Q4: +X.X% CAGR (Target: +5-8%)
- 2022 Bear: -X.X% CAGR (Target: -5-0%)

## Best Parameters
[Document optimized parameters]

## Integration Benefits
[Show portfolio improvements]

## Production Readiness
[Checklist of requirements met]
```

### Task 8.2: Create Production Deployment
```bash
# Export model for production
python3 -m deploy.export \
    --models BearDipBuyer_v1 \
    --stage candidate \
    --config configs/profiles/beardipbuyer_production.yaml

# Test locally
./production/run_local.sh

# Prepare for live deployment
./production/deploy/build.sh
```

### Task 8.3: Update Documentation
```bash
# Update experiments index
echo "013_beardipbuyer: Opportunistic bear market profit model" >> docs/research/experiments/INDEX.md

# Update best results if applicable
vim docs/research/BEST_RESULTS.md

# Commit all changes
git add .
git commit -m "Complete Experiment 013: BearDipBuyer implementation"
```

## Testing Checkpoints

### After Each Major Step:
- [ ] Code runs without errors
- [ ] Results are reasonable (not extreme)
- [ ] Trades align with expected behavior
- [ ] Risk controls are working
- [ ] Documentation is updated

### Before Moving to Next Phase:
- [ ] Current phase goals met
- [ ] Results documented
- [ ] Parameters saved
- [ ] Any issues resolved

## Troubleshooting Guide

### Common Issues and Solutions:

**Issue**: No trades generated
- Check VIX data is loaded
- Verify thresholds aren't too strict
- Ensure market data covers bear period

**Issue**: Too many trades
- Increase VIX threshold
- Tighten RSI requirement
- Add cooldown period

**Issue**: Large drawdowns
- Reduce position size
- Tighten circuit breaker
- Add volatility filter

**Issue**: Missing rebounds
- Lower VIX threshold slightly
- Check momentum calculation
- Verify exit logic isn't too tight

## Success Criteria Checklist

### Minimum Requirements:
- [ ] Positive CAGR in 2+ bear markets
- [ ] Max drawdown < -15%
- [ ] Win rate > 50%
- [ ] Successful integration test
- [ ] Documentation complete

### Stretch Goals:
- [ ] Beat Exp 012 best results
- [ ] CAGR > 10% in panic bears
- [ ] Sharpe > 1.0 in bear periods
- [ ] < 5 trades per period (selective)

---

*Plan Version*: 1.0
*Timeline*: 8 days
*Last Updated*: 2025-11-25