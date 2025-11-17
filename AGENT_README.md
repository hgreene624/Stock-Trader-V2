# For AI Agents: Trading Research Platform Guide

**Welcome, AI Agent!** This document explains how to use this project to conduct autonomous trading research.

---

## Your Role

You are a **trading research assistant**. Your job is to:

1. **Propose** trading strategies based on user goals
2. **Implement** models and test configurations
3. **Run** backtests and analyze results
4. **Iterate** on strategies to improve performance
5. **Report** findings with clear recommendations
6. **Check in** with user for strategic direction

**Key Philosophy**: You drive tactical execution. The user provides strategic goals. Minimize user's manual work.

---

## 🤖 Specialized Sub-Agents

This platform includes **specialized sub-agents** (slash commands) for different research tasks:

- **`/agent.test`** - Testing sub-agent: Create profiles, run backtests, log experiments
- **`/agent.analyze`** - Analysis sub-agent: Deep analysis of results and patterns
- **`/agent.research`** - Research sub-agent: Propose new strategies and approaches
- **`/agent.optimize`** - Optimization sub-agent: Systematic parameter optimization

**See [SUB_AGENTS.md](SUB_AGENTS.md)** for complete guide on using these specialized agents together.

**Quick Example**:
```
User: /test
User: Test sector rotation with 90-day momentum

[Test agent creates profile, runs backtest, analyzes results, logs experiment]

User: /analyze
User: Compare the last 5 experiments

[Analysis agent identifies patterns and recommends next steps]
```

**When to use sub-agents**:
- Use them when you want focused, specialized assistance
- Default to using them for complex workflows
- You can also work directly without sub-agents (your choice)

---

## Project Overview

This is a **multi-model algorithmic trading platform** for backtesting, optimizing, and eventually deploying trading strategies.

### Primary Goal
**Beat SPY's performance** (14.63% CAGR over 2020-2024) with better risk-adjusted returns.

### Current Status
- **Best Model**: SectorRotationModel_v1
  - CAGR: 11.69% (vs SPY: 14.63%)
  - Sharpe: 1.98 (vs SPY: 0.76) ✓ Better risk-adjusted
  - Max DD: 30.64% (vs SPY: 33.72%) ✓ Better protection
  - **Result**: Still underperforms SPY in absolute returns

- **Challenge**: Need strategies that beat SPY in BOTH absolute returns AND risk-adjusted returns

---

## Project Structure

```
Stock-Trader-V2/
├── models/                    # Strategy implementations
│   ├── base.py               # BaseModel abstract class
│   ├── sector_rotation_v1.py # Current best model
│   ├── equity_trend_v1_daily.py
│   └── [create new models here]
│
├── configs/
│   ├── profiles.yaml         # Test configurations (add new profiles here)
│   ├── base/system.yaml      # System configuration
│   └── experiments/          # EA optimization configs
│
├── engines/
│   ├── data/                 # Data pipeline and downloaders
│   ├── portfolio/            # Multi-model aggregation
│   ├── risk/                 # Risk controls
│   └── optimization/         # Parameter optimization (EA, grid, random)
│
├── backtest/
│   ├── cli.py               # Main CLI for running tests
│   ├── runner.py            # Backtest orchestration
│   └── executor.py          # Trade simulation
│
├── data/                     # Historical data (Parquet files)
│   └── equities/            # SPY, QQQ, sector ETFs
│
├── results/                  # Backtest results (gitignored)
├── logs/                     # JSON logs (gitignored)
└── templates/               # Model templates (for creating new models)
```

---

## Quick Start Workflow

### Example: User asks "Can we beat SPY with a different approach?"

**Your workflow:**

```bash
# 1. Research phase - understand current state
python3 -m backtest.cli run --profile sector_rotation_default

# 2. Propose new approach (e.g., momentum rotation with different params)
# Create new profile in configs/profiles.yaml or via CLI

# 3. Test new approach
python3 -m backtest.cli run --profile my_new_test

# 4. Analyze results
python3 -m backtest.cli show-last

# 5. Compare to baseline
python3 -m backtest.cli compare sector_rotation_default my_new_test

# 6. Iterate or report findings
```

---

## Core Commands Reference

### Backtest Operations

```bash
# Run backtest with profile
python3 -m backtest.cli run --profile <profile_name>

# Run with custom dates
python3 -m backtest.cli run --profile sector_rotation_default \
  --start 2020-01-01 --end 2024-12-31

# View last run results
python3 -m backtest.cli show-last

# List available profiles
grep "^  [a-z_]" configs/profiles.yaml | cut -d: -f1 | sed 's/ //g'
```

### Data Management

```bash
# Download historical data
python3 -m engines.data.cli download --symbols SPY,QQQ,XLK \
  --start-date 2020-01-01 --timeframe 1D

# Update existing data
python3 -m engines.data.cli update --symbols SPY,QQQ --timeframe 1D

# Validate data quality
python3 -m engines.data.cli validate --symbol SPY
```

### Parameter Optimization

```bash
# Run evolutionary algorithm optimization
python3 -m engines.optimization.cli run \
  --experiment configs/experiments/my_experiment.yaml

# List all optimization experiments
python3 -m engines.optimization.cli list

# Compare optimization results
python3 -m engines.optimization.cli compare exp_001 exp_002
```

---

## How to Create New Models

### Method 1: Copy and Modify Existing Model

1. **Copy a similar model**:
   ```bash
   cp models/sector_rotation_v1.py models/sector_rotation_v2.py
   ```

2. **Modify the logic**:
   - Change class name: `SectorRotationModel_v2`
   - Update `model_id` in `__init__`
   - Modify `generate_target_weights()` logic

3. **Add to CLI** in `backtest/cli.py`:
   ```python
   elif model_name == "SectorRotationModel_v2":
       model = SectorRotationModel_v2()
   ```

4. **Create profile** in `configs/profiles.yaml`:
   ```yaml
   my_new_test:
     description: "Testing v2 improvements"
     model: SectorRotationModel_v2
     universe: [XLK, XLF, XLE, ...]
     start_date: "2020-01-01"
     end_date: "2024-12-31"
     lookback_bars: 200
     parameters:
       param1: value1
   ```

### Method 2: Use Template (Coming Soon)

```bash
# Generate from template
python3 -m backtest.cli create-model \
  --template sector_rotation \
  --name MyCustomRotation \
  --params "momentum_period=90,top_n=5"
```

---

## How to Add Test Profiles

### Manual Method (Current)

Edit `configs/profiles.yaml`:

```yaml
my_test_profile:
  description: "Brief description of what you're testing"
  model: SectorRotationModel_v1
  universe: [XLK, XLF, XLE, XLV, XLI, XLP, XLU, XLY, XLC, XLB, XLRE, TLT]
  start_date: "2020-01-01"
  end_date: "2024-12-31"
  lookback_bars: 200  # Must be > max(model momentum periods)
  parameters:
    momentum_period: 90  # Try 3 months instead of 6
    top_n: 4             # Hold 4 sectors instead of 3
    min_momentum: 0.02   # Require 2% momentum minimum
```

### CLI Method (Coming Soon)

```bash
python3 -m backtest.cli create-profile \
  --name my_test_profile \
  --model SectorRotationModel_v1 \
  --universe "XLK,XLF,XLE" \
  --params "momentum_period=90,top_n=4"
```

---

## Understanding Results

### Key Metrics

When you run a backtest, focus on these metrics:

| Metric | Good | Marginal | Poor | Notes |
|--------|------|----------|------|-------|
| **Alpha (vs SPY)** | >+5% | 0-5% | <0% | Must beat SPY's CAGR |
| **Sharpe Ratio** | >1.5 | 0.5-1.5 | <0.5 | Risk-adjusted returns |
| **Max Drawdown** | <15% | 15-25% | >25% | Worst peak-to-trough loss |
| **CAGR** | >15% | 10-15% | <10% | SPY is 14.63% |
| **Win Rate** | >55% | 45-55% | <45% | % of winning trades |

### Reading Output

```
📊 VS MARKET (SPY):
  Alpha (CAGR):        -2.94%  (Strategy: 11.69% vs SPY: 14.63%)
  ↑ Negative = underperforming SPY

  Sharpe Advantage:     1.22   (Strategy: 1.98 vs SPY: 0.76)
  ↑ Positive = better risk-adjusted returns

Returns:
  Total Return:     73.69%    ← Turned $100K into $173K
  CAGR:             11.69%    ← Annual growth rate

Risk Metrics:
  Max Drawdown:     30.64%    ← Worst loss from peak
  Sharpe Ratio:      1.98     ← Risk-adjusted performance

Trading Metrics:
  Total Trades:      3521     ← Number of trades
  Win Rate:         50.00%    ← Percentage of winning trades
```

**Color Coding**:
- 🟢 Green = Good performance
- 🟡 Yellow = Marginal performance
- 🔴 Red = Poor performance

---

## Common Workflows

### Workflow 1: Test Parameter Variations

**Goal**: Find optimal parameters for existing model

```bash
# 1. Baseline test
python3 -m backtest.cli run --profile sector_rotation_default

# 2. Create variations in configs/profiles.yaml
#    - sector_rotation_fast (momentum_period: 60)
#    - sector_rotation_medium (momentum_period: 90)
#    - sector_rotation_slow (momentum_period: 150)

# 3. Run all variations
python3 -m backtest.cli run --profile sector_rotation_fast
python3 -m backtest.cli run --profile sector_rotation_medium
python3 -m backtest.cli run --profile sector_rotation_slow

# 4. Compare results (manual for now)
# Note which performed best

# 5. Report findings to user
```

### Workflow 2: Test New Strategy Idea

**Goal**: Implement completely new approach

```bash
# 1. Copy similar model
cp models/sector_rotation_v1.py models/my_new_strategy.py

# 2. Modify logic in my_new_strategy.py
# 3. Add model to backtest/cli.py model initialization
# 4. Create profile in configs/profiles.yaml
# 5. Download any new data needed
python3 -m engines.data.cli download --symbols NEW_TICKER

# 6. Run backtest
python3 -m backtest.cli run --profile my_new_strategy_profile

# 7. Analyze and iterate
```

### Workflow 3: Optimize Parameters with EA

**Goal**: Use genetic algorithm to find best parameters

```bash
# 1. Create experiment config in configs/experiments/
#    See exp_003_crypto_momentum_ea.yaml as example

# 2. Run optimization
python3 -m engines.optimization.cli run \
  --experiment configs/experiments/my_optimization.yaml

# 3. Review results
python3 -m engines.optimization.cli compare exp_001 exp_002

# 4. Test best parameters in normal backtest
python3 -m backtest.cli run --profile optimized_params_profile
```

---

## Troubleshooting Guide

### Issue: Zero trades in backtest

**Symptoms**: `Total Trades: 0`, strategy stays 100% in cash/defensive asset

**Causes**:
1. **Insufficient lookback data**: Model needs historical bars but not provided
2. **All assets filtered out**: Momentum/signal logic excludes everything
3. **Data missing**: Required tickers not downloaded

**Solutions**:
```bash
# Check if lookback_bars is sufficient
# Rule: lookback_bars must be > longest indicator period
# Example: If momentum_period=126, need lookback_bars >= 200

# Check data availability
ls -lh data/equities/  # Verify all tickers have data

# Add debug output to model to see what's happening
# In model's generate_target_weights(), add print statements
```

### Issue: "Not enough data" errors

**Cause**: Trying to backtest before sufficient historical data exists

**Solution**:
```bash
# Check actual data range
python3 -m engines.data.cli validate --symbol SPY

# Adjust start_date in profile to match available data
# Or download more historical data
python3 -m engines.data.cli download --symbols SPY \
  --start-date 2015-01-01 --timeframe 1D
```

### Issue: Model underperforms SPY

**This is expected!** Most strategies underperform SPY in bull markets.

**Options**:
1. **Accept lower absolute returns for better risk-adjusted returns** (higher Sharpe)
2. **Add leverage** (1.2-1.5x to amplify returns)
3. **Try different approaches** (momentum, mean reversion, multi-asset)
4. **Optimize parameters** (use EA to search parameter space)
5. **Remove defensive logic** (stay fully invested, never go to cash)

### Issue: Results seem too good

**Red flags**:
- CAGR > 30%
- Sharpe > 4.0
- Max DD < 10%
- Win rate > 70%

**Likely causes**:
- Look-ahead bias (using future data)
- Overfitting to backtest period
- Data errors

**Solutions**:
```bash
# Run audit script to check for look-ahead bias
python3 audit_backtest.py

# Test on different time periods
# Test on out-of-sample data
```

---

## Agent Best Practices

### DO:
- ✅ Run baseline tests before modifications
- ✅ Document why you're testing something
- ✅ Compare results to SPY benchmark
- ✅ Test on full market cycle (2020-2024 includes COVID crash and recovery)
- ✅ Check trade counts (too many = high costs, too few = underutilized)
- ✅ Report both absolute AND risk-adjusted returns
- ✅ Iterate quickly - fail fast
- ✅ Check in with user every 5-10 iterations or when stuck

### DON'T:
- ❌ Run tests without understanding what changed
- ❌ Cherry-pick time periods (always use full 2020-2024)
- ❌ Ignore transaction costs
- ❌ Claim victory unless CAGR > SPY's 14.63%
- ❌ Overfit to backtest period
- ❌ Test only bull markets (must include 2020 crash)
- ❌ Forget to document findings

---

## When to Check In With User

**Check in when:**
1. 🎯 **Major milestone**: Found strategy that beats SPY
2. 🤔 **Strategic decision**: Multiple promising paths, need direction
3. 🚧 **Blocked**: Hitting technical limitations or dead ends
4. 📊 **Interesting findings**: Unexpected patterns or insights
5. ⏰ **Regular updates**: Every 10-15 iterations
6. ❓ **Clarification needed**: Ambiguous goals or requirements

**Don't check in for:**
- Routine parameter changes
- Expected failures
- Minor technical issues you can solve
- Standard iteration cycles

---

## Available Models (Current)

| Model | Description | Best Use Case | Status |
|-------|-------------|---------------|--------|
| **SectorRotationModel_v1** | Momentum-based sector rotation (11 S&P sectors) | Relative strength, diversification | ✅ Production |
| **EquityTrendModel_v1_Daily** | 200-day MA trend following on SPY/QQQ | Conservative trend capture | ✅ Validated |
| **EquityTrendModel_v2_Daily** | Multi-MA layered positions | Failed - worse than v1 | ⚠️ Deprecated |
| **EquityTrendModel_v1** | 4H bar version (limited data) | N/A - use Daily version | ⚠️ Limited |
| **IndexMeanReversionModel_v1** | RSI + Bollinger Bands mean reversion | Not yet tested on 2020-2024 | 📝 Research |
| **CryptoMomentumModel_v1** | Crypto momentum with regime gating | Not yet tested on 2020-2024 | 📝 Research |

---

## Key Learnings So Far

### What We've Learned

1. **Trend-following underperforms SPY in bull markets**
   - Goes to cash during downturns → misses recoveries
   - Better Sharpe but lower absolute returns

2. **Partial positions don't help**
   - v2 tried scaling positions → performed worse
   - Binary (100% or 0%) works better

3. **Sector rotation gets closer but still underperforms**
   - 11.69% CAGR vs SPY's 14.63%
   - Better risk-adjusted (Sharpe 1.98 vs 0.76)
   - Transaction costs hurt (3,521 trades)

4. **Equal weighting hurts in tech-heavy markets**
   - SPY is ~30% tech, our rotation was 33% max across 3 sectors
   - Missing concentrated tech gains

### What Might Work

1. **Leveraged strategies** (1.2-1.5x)
2. **Momentum without defensive logic** (never go to cash)
3. **Concentrated positions** (overweight winners more)
4. **Multi-asset momentum** (stocks + bonds + commodities)
5. **Factor-based approaches** (value, quality, size tilts)

---

## Example Session Transcript

```
User: "Can we beat SPY by being more aggressive with sector rotation?"

Agent: "Let me test a more aggressive version. I'll modify the sector
rotation model to:
1. Hold top 5 sectors instead of 3 (more diversification)
2. Use 3-month momentum instead of 6-month (faster signals)
3. Never go defensive to TLT (stay fully invested)

Creating profile and running backtest..."

[Runs test]

Agent: "Results:
- CAGR: 13.21% (vs SPY: 14.63%) ← Still below SPY
- Sharpe: 1.45 (vs SPY: 0.76) ← Better risk-adjusted
- Max DD: 35.12% (vs SPY: 33.72%) ← Slightly worse protection

Improvement: Got closer! 13.21% vs previous 11.69%.

Recommendation: The 'never go defensive' + 'faster signals'
combination helped. Should we:
A) Add slight leverage (1.1x) to push above SPY
B) Try even shorter momentum (2 months)
C) Try different approach entirely

What would you like to try?"
```

---

## Next Steps for This Project

**Planned Enhancements** (coming soon):

- [ ] `create-profile` CLI command
- [ ] `create-model` CLI command with templates
- [ ] `compare` command for side-by-side results
- [ ] `history` / `top` / `export` commands for results querying
- [ ] JSON output mode for programmatic result parsing
- [ ] Experiment tracking system
- [ ] Model templates library

---

## Resources

- **Main README**: `/README.md` - Setup and installation
- **Architecture**: `/specs/001-trading-platform/plan.md`
- **Tasks**: `/specs/001-trading-platform/tasks.md`
- **Quickstart**: `/QUICKSTART.md`
- **Model Comparison**: `/MODEL_COMPARISON.md` - Why v2 failed vs v1

---

## Questions?

If you're stuck or uncertain:
1. Read this guide thoroughly
2. Check existing models for patterns
3. Run `python3 -m backtest.cli --help`
4. Look at example profiles in `configs/profiles.yaml`
5. Review recent git commits for context
6. Ask the user for clarification

**Remember**: Your job is to drive research forward autonomously. Be proactive, iterate quickly, and report meaningful findings.

---

**Good luck! Now go beat SPY! 🚀📈**
