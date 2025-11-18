# Quick Iteration Workflow Guide

This guide shows you how to rapidly test and iterate on trading models using the new profile-based workflow.

## Overview

The improved workflow eliminates repetitive commands and makes model testing as simple as:
1. Edit a profile in `configs/profiles.yaml`
2. Run: `python -m backtest.cli run --profile <name>`
3. Review results
4. Iterate

## Quick Start

### 1. List Available Profiles

```bash
# View all available test profiles
cat configs/profiles.yaml | grep "^  [a-z]" | sed 's/:$//'
```

Available profiles include:
- `equity_trend_default` - Default equity trend strategy
- `equity_trend_aggressive` - Faster MA periods
- `equity_trend_conservative` - Slower MA periods
- `mean_rev_default` - Mean reversion strategy
- `crypto_momentum_default` - Crypto momentum
- `my_test_1`, `my_test_2` - Custom test slots (edit these!)

### 2. Run Your First Test

```bash
# Run a pre-configured test
python -m backtest.cli run --profile equity_trend_default

# The system will:
# ✓ Load the profile configuration
# ✓ Check if data exists for SPY, QQQ
# ✓ Auto-download missing data (if needed)
# ✓ Run the backtest
# ✓ Display results
# ✓ Save results for later viewing
```

### 3. View Results Anytime

```bash
# View the last backtest run
python -m backtest.cli show-last
```

## Iteration Workflow

### Simple Iteration (Edit Profile)

1. **Edit the profile**:
   ```bash
   vim configs/profiles.yaml  # or your preferred editor
   ```

2. **Find a profile to customize** (e.g., `my_test_1`):
   ```yaml
   my_test_1:
     description: "Testing different MA periods"
     model: EquityTrendModel_v1
     universe: [SPY, QQQ]
     start_date: "2020-01-01"
     end_date: "2024-12-31"
     parameters:
       slow_ma_period: 200      # <-- Change this
       momentum_lookback_days: 60
       exit_ma_period: 50
       equal_weight: true
       max_positions: 2
   ```

3. **Run the test**:
   ```bash
   python -m backtest.cli run --profile my_test_1
   ```

4. **Review results** - they're shown immediately after the run completes

5. **Iterate**: Change `slow_ma_period` to 250, re-run, compare results

### Testing Different Universes

Create a custom universe in `profiles.yaml`:

```yaml
universes:
  my_tech_stocks:
    - AAPL
    - MSFT
    - GOOGL
    - AMZN

profiles:
  my_tech_test:
    model: EquityTrendModel_v1
    universe: [AAPL, MSFT, GOOGL, AMZN]  # Use your custom universe
    start_date: "2020-01-01"
    end_date: "2024-12-31"
    parameters:
      slow_ma_period: 200
      momentum_lookback_days: 60
      exit_ma_period: 50
```

Run with: `python -m backtest.cli run --profile my_tech_test`

### Testing Different Time Periods

Override dates without editing the profile:

```bash
# Test on 2023 only
python -m backtest.cli run --profile equity_trend_default --start 2023-01-01 --end 2023-12-31

# Test on recent 6 months
python -m backtest.cli run --profile equity_trend_default --start 2024-06-01
```

## Features

### Auto-Download

Data is automatically checked and downloaded if missing:

```bash
# This will auto-download SPY and QQQ data if not present
python -m backtest.cli run --profile equity_trend_default
```

Skip auto-download if you want to control it manually:
```bash
python -m backtest.cli run --profile equity_trend_default --no-download
```

### Smart Defaults

If you don't specify dates, sensible defaults are used:
- Start date: 5 years ago
- End date: Today

```bash
# Uses last 5 years of data
python -m backtest.cli run --profile equity_trend_default
```

### Last Run Tracking

Every backtest is automatically saved. View it anytime:

```bash
python -m backtest.cli show-last
```

Output:
```
================================================================================
LAST BACKTEST RUN
================================================================================

Run Time:    2024-11-17T15:30:22
Model:       EquityTrendModel_v1
Period:      2020-01-01 to 2024-12-31

Configuration:
  Profile:   equity_trend_default

--------------------------------------------------------------------------------
PERFORMANCE SUMMARY
--------------------------------------------------------------------------------

Returns:
  Total Return:         +67.8%
  CAGR:                  11.2%

Risk Metrics:
  Max Drawdown:         -21.3%
  Sharpe Ratio:           1.15

Trading Metrics:
  Total Trades:             28
  Win Rate:              61.2%

Balanced Performance Score:
  BPS:                  0.8200

NAV:
  Initial NAV:      $100,000.00
  Final NAV:        $167,800.00
```

## Example Workflows

### Workflow 1: Parameter Sweep

Test different MA periods quickly:

```yaml
# In configs/profiles.yaml
my_test_1:
  # ... configuration
  parameters:
    slow_ma_period: 150  # Start with 150
```

```bash
# Run 1
python -m backtest.cli run --profile my_test_1
# Note the BPS score

# Edit: Change slow_ma_period to 200
# Run 2
python -m backtest.cli run --profile my_test_1
# Compare BPS

# Edit: Change slow_ma_period to 250
# Run 3
python -m backtest.cli run --profile my_test_1
# Compare BPS
```

Keep a notebook of results:
```
MA=150: BPS=0.78, Sharpe=1.05, MaxDD=-22%
MA=200: BPS=0.82, Sharpe=1.15, MaxDD=-21%
MA=250: BPS=0.91, Sharpe=1.38, MaxDD=-18%  ← Best!
```

### Workflow 2: Bull vs Bear Market Testing

```bash
# Test in bull market (2019-2021)
python -m backtest.cli run --profile equity_trend_default \
    --start 2019-01-01 --end 2021-12-31

# Test in bear/volatile market (2022)
python -m backtest.cli run --profile equity_trend_default \
    --start 2022-01-01 --end 2022-12-31

# Test in recovery (2023-2024)
python -m backtest.cli run --profile equity_trend_default \
    --start 2023-01-01 --end 2024-12-31
```

### Workflow 3: Model Comparison

Create profiles for different models:

```bash
# Test trend following
python -m backtest.cli run --profile equity_trend_default

# Test mean reversion
python -m backtest.cli run --profile mean_rev_default

# Compare results side-by-side
```

## Tips

### 1. Use Descriptive Profile Names

```yaml
profiles:
  equity_trend_ma200_mom60:  # Descriptive name
    description: "200D MA with 60D momentum"
    # ...
```

### 2. Keep a Test Journal

Track your iterations in a simple text file:

```
Test Journal - EquityTrendModel_v1
===================================

2024-11-17:
- Baseline: MA=200, Mom=60 → BPS=0.82
- Test 1: MA=250, Mom=60 → BPS=0.91 ← Improvement!
- Test 2: MA=250, Mom=90 → BPS=0.89 (worse)
- Conclusion: MA=250, Mom=60 is optimal

Next: Test exit_ma_period variations
```

### 3. Create Profile Templates

Copy and modify existing profiles:

```yaml
# Template for testing MA variations
equity_trend_template:
  model: EquityTrendModel_v1
  universe: [SPY, QQQ]
  start_date: "2020-01-01"
  end_date: "2024-12-31"
  parameters:
    slow_ma_period: 200      # CHANGE THIS
    momentum_lookback_days: 60
    exit_ma_period: 50
    equal_weight: true
    max_positions: 2
```

### 4. Use Shorter Test Periods for Speed

When testing many parameter combinations, use shorter periods:

```yaml
my_quick_test:
  start_date: "2023-01-01"  # Just 2 years
  end_date: "2024-12-31"
  # ... rest of config
```

Then validate winners on full 5-year period.

### 5. Document Your Best Results

When you find a promising configuration, document it:

```yaml
equity_trend_optimized_v1:
  description: "Optimized params - BPS=0.91, Sharpe=1.38 (2020-2024)"
  model: EquityTrendModel_v1
  universe: [SPY, QQQ]
  start_date: "2020-01-01"
  end_date: "2024-12-31"
  parameters:
    slow_ma_period: 250
    momentum_lookback_days: 120
    exit_ma_period: 70
    equal_weight: true
    max_positions: 2
```

## Advanced: Traditional Config-Based Workflow

If you prefer the traditional approach, it still works:

```bash
# Old way (still supported)
python -m backtest.cli run \
    --config configs/base/system.yaml \
    --model EquityTrendModel_v1 \
    --start 2020-01-01 \
    --end 2024-12-31
```

But profiles are **much faster** for iteration!

## Troubleshooting

### "Profile not found"
```bash
# List available profiles
grep "^  [a-z_].*:" configs/profiles.yaml
```

### "Data download failed"
Download manually:
```bash
python -m engines.data.cli download \
    --symbols SPY QQQ \
    --asset-class equity \
    --timeframes 1D 4H \
    --start 2020-01-01
```

### "No previous backtest run found"
Run a backtest first:
```bash
python -m backtest.cli run --profile equity_trend_default
```

## Next Steps

1. **Try the default profiles**: Run `equity_trend_default`, `mean_rev_default`
2. **Customize `my_test_1`**: Edit it for your experiments
3. **Create your own profiles**: Add new test scenarios
4. **Iterate rapidly**: Edit parameters, re-run, compare
5. **Document winners**: Keep track of your best configurations

Happy testing! 🚀
