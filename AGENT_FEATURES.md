# Agent-First Features - Complete Guide

This document summarizes all the agent-friendly features added to the trading platform.

---

## 🎯 Overview

The platform is now **fully agent-optimized**. AI agents can autonomously:
- Create and test trading strategies
- Generate models from templates
- Run backtests and analyze results
- Track experiments and learnings
- Iterate towards beating SPY

---

## 📚 Documentation

### 1. AGENT_README.md
**Purpose**: Comprehensive onboarding for new AI agents

**Contains**:
- Agent role and responsibilities
- Project structure explanation
- Complete workflow patterns
- Command reference
- Troubleshooting guide
- Example agent sessions
- Key learnings so far

**When to read**: First thing when starting a new session

### 2. CLAUDE.md (Updated)
**Purpose**: Quick reference for ongoing work

**Contains**:
- Agent-first quick start guide
- Current project status and goals
- Key commands prominently displayed
- When to check in vs. work autonomously

**When to read**: Quick reference during active work

---

## 🛠️ New CLI Commands

All commands designed for agent autonomy - no manual file editing required.

### 1. create-profile
**Create test profiles without editing YAML**

```bash
python3 -m backtest.cli create-profile \
  --name sector_rotation_fast \
  --model SectorRotationModel_v1 \
  --universe "XLK,XLF,XLE,XLV,XLI,XLP,XLU,XLY,XLC,XLB,XLRE,TLT" \
  --params "momentum_period=60,top_n=4,min_momentum=0.01" \
  --lookback-bars 200 \
  --description "Faster 2-month momentum with 4 sectors" \
  --start-date "2020-01-01" \
  --end-date "2024-12-31"
```

**Output**:
- Creates profile in `configs/profiles.yaml`
- Shows profile details
- Provides command to run it

**Use case**: Quickly test parameter variations without manual YAML editing

---

### 2. list-profiles
**See all available test configurations**

```bash
python3 -m backtest.cli list-profiles
```

**Output**:
```
AVAILABLE PROFILES
==========================================
📋 sector_rotation_default
   Model: SectorRotationModel_v1
   Description: Sector rotation momentum
   Universe: XLK, XLF, XLE, XLV, XLI...

📋 equity_trend_daily
   Model: EquityTrendModel_v1_Daily
   Description: Daily bar version
   Universe: SPY, QQQ
...
Total: 15 profiles
```

**Use case**: Discover what's already configured before creating new profiles

---

### 3. create-model
**Generate new models from templates**

```bash
python3 -m backtest.cli create-model \
  --template sector_rotation \
  --name MySectorRotationV2 \
  --params "momentum_period=90,top_n=4,min_momentum=0.02" \
  --description "Modified sector rotation with higher momentum threshold"
```

**Available templates**:
- `sector_rotation` - Momentum-based sector rotation
- `trend_following` - MA + momentum trend following
- `mean_reversion` - RSI + Bollinger Bands mean reversion

**Output**:
- Creates new model file in `models/`
- Replaces template placeholders with your parameters
- Provides registration instructions

**Use case**: Create model variations without copying/pasting code

---

### 4. JSON Output Mode
**Machine-readable results for programmatic analysis**

```bash
python3 -m backtest.cli run --profile sector_rotation_default --format json
```

**Output**:
```json
{
  "status": "success",
  "model": "SectorRotationModel_v1",
  "period": {
    "requested_start": "2020-01-01",
    "requested_end": "2024-12-31",
    "actual_start": "2020-01-02",
    "actual_end": "2024-12-30"
  },
  "metrics": {
    "cagr": 0.1169,
    "sharpe_ratio": 1.98,
    "max_drawdown": 0.3064,
    "total_return": 0.7369,
    "win_rate": 0.50,
    "bps": 0.90
  },
  "vs_spy": {
    "spy_cagr": 0.1463,
    "alpha": -0.0294,
    "outperformance": -0.2386,
    "sharpe_advantage": 1.22,
    "beats_spy": false
  },
  "trade_count": 3521,
  "config": {...}
}
```

**Use case**: Parse results programmatically for analysis, comparisons, or decision-making

---

### 5. Existing Commands (Already Available)

```bash
# Run backtest
python3 -m backtest.cli run --profile <name>

# View last results
python3 -m backtest.cli show-last

# Download data
python3 -m engines.data.cli download --symbols SPY,QQQ --start-date 2020-01-01 --timeframe 1D

# Optimize with EA
python3 -m engines.optimization.cli run --experiment configs/experiments/my_exp.yaml
```

---

## 📊 Experiment Tracking

**Track what you tried, why, and what you learned**

### Log an Experiment

```python
from utils.experiment_tracker import ExperimentTracker

tracker = ExperimentTracker()

tracker.log_experiment(
    name="sector_rotation_fast_momentum",
    hypothesis="Shorter momentum period (60 days) will capture trends faster",
    changes={
        "momentum_period": "126 → 60",
        "top_n": "3 → 4"
    },
    results={
        "cagr": 0.1321,
        "sharpe": 1.45,
        "max_dd": 0.3412
    },
    baseline_results={
        "cagr": 0.1169,
        "sharpe": 1.98,
        "max_dd": 0.3064
    },
    conclusion="Faster momentum improved CAGR but hurt Sharpe. Still below SPY.",
    next_steps="Try 90-day momentum as compromise, or add slight leverage"
)
```

### CLI Usage

```bash
# Log experiment from command line
python3 -m utils.experiment_tracker log \
  --name "my_test" \
  --hypothesis "Testing faster signals" \
  --changes '{"momentum_period":"126->90"}' \
  --results '{"cagr":0.1245,"sharpe":1.75}' \
  --conclusion "Improvement but still below SPY"

# List recent experiments
python3 -m utils.experiment_tracker list --limit 10

# Find best experiment
python3 -m utils.experiment_tracker best --metric cagr
```

**Storage**: `.experiments/experiments.jsonl` (JSONL format)

**Use case**: Learn from past iterations, avoid repeating failed experiments

---

## 📂 Model Templates

Located in `templates/models/`, these are fully-functional model templates with placeholders.

### sector_rotation_template.py
- Ranks sectors by momentum
- Holds top N sectors
- Goes defensive (TLT) when bearish
- **Parameters**: momentum_period, top_n, min_momentum

### trend_following_template.py
- MA + momentum trend following
- Equal or momentum-weighted positions
- **Parameters**: ma_period, momentum_period, momentum_threshold

### mean_reversion_template.py
- RSI + Bollinger Bands
- Buy oversold, sell overbought
- **Parameters**: rsi_period, rsi_oversold, rsi_overbought, bb_period, bb_std

---

## 🔄 Agent Workflow Examples

### Example 1: Test Parameter Variation

```bash
# 1. List available profiles
python3 -m backtest.cli list-profiles

# 2. Create variation
python3 -m backtest.cli create-profile \
  --name sector_test_fast \
  --model SectorRotationModel_v1 \
  --universe "XLK,XLF,XLE,XLV,XLI,XLP,XLU,XLY,XLC,XLB,XLRE,TLT" \
  --params "momentum_period=60,top_n=4" \
  --lookback-bars 200

# 3. Run test
python3 -m backtest.cli run --profile sector_test_fast --format json > results.json

# 4. Analyze (parse JSON)

# 5. Log experiment
python3 -m utils.experiment_tracker log \
  --name "sector_fast" \
  --hypothesis "Faster momentum" \
  --changes '{"momentum_period":"126->60"}' \
  --results '{"cagr":0.XX,"sharpe":X.XX}' \
  --conclusion "Your conclusion"

# 6. Iterate or report to user
```

### Example 2: Create New Model

```bash
# 1. Generate from template
python3 -m backtest.cli create-model \
  --template trend_following \
  --name MyTrendFollower \
  --params "ma_period=150,momentum_period=90"

# 2. Register model (manual step - add to backtest/cli.py)
# Add import and initialization

# 3. Create profile
python3 -m backtest.cli create-profile \
  --name my_trend_test \
  --model MyTrendFollower \
  --universe "SPY,QQQ" \
  --params "ma_period=150"

# 4. Test
python3 -m backtest.cli run --profile my_trend_test

# 5. Iterate
```

---

## 🎓 Agent Best Practices

### ✅ DO:
1. **Use JSON output** for programmatic analysis
   ```bash
   python3 -m backtest.cli run --profile test --format json
   ```

2. **Log experiments** to track learnings
   ```python
   tracker.log_experiment(name, hypothesis, changes, results)
   ```

3. **Create profiles via CLI** instead of editing YAML
   ```bash
   python3 -m backtest.cli create-profile --name test --model X --universe "A,B,C"
   ```

4. **Check existing profiles** before creating new ones
   ```bash
   python3 -m backtest.cli list-profiles
   ```

5. **Use templates** for new models
   ```bash
   python3 -m backtest.cli create-model --template sector_rotation --name MyModel
   ```

### ❌ DON'T:
1. Manually edit YAML files (use CLI commands)
2. Create duplicate profiles (check list-profiles first)
3. Forget to log experiments (you'll lose learning)
4. Skip documenting hypotheses (track why you tried something)

---

## 📈 Success Metrics

### Project Goal
**Beat SPY**: 14.63% CAGR (2020-2024)

### Current Best
**SectorRotationModel_v1**: 11.69% CAGR, 1.98 Sharpe (still below SPY)

### What "Success" Looks Like
```json
{
  "status": "success",
  "vs_spy": {
    "alpha": 0.0150,          // ← Positive alpha (beating SPY)
    "beats_spy": true,         // ← This is the goal!
    "sharpe_advantage": 1.50   // ← Bonus: better risk-adjusted
  }
}
```

---

## 🚀 Quick Reference Card

```bash
# === PROFILE MANAGEMENT ===
list-profiles                 # See all profiles
create-profile --name X ...   # Create new profile

# === MODEL MANAGEMENT ===
create-model --template X ... # Generate model from template
list-models                   # See all models

# === BACKTESTING ===
run --profile X               # Run backtest (text output)
run --profile X --format json # Run backtest (JSON output)
show-last                     # View last run results

# === EXPERIMENT TRACKING ===
python3 -m utils.experiment_tracker list   # Show experiments
python3 -m utils.experiment_tracker best   # Show best result

# === DATA MANAGEMENT ===
python3 -m engines.data.cli download --symbols X,Y,Z --start-date 2020-01-01
python3 -m engines.data.cli update --symbols X,Y,Z

# === OPTIMIZATION ===
python3 -m engines.optimization.cli run --experiment configs/experiments/X.yaml
```

---

## 🎉 Summary

The platform is now **fully agent-optimized**:

✅ **Self-documenting** - AGENT_README.md explains everything
✅ **Scriptable** - All operations via CLI
✅ **Trackable** - Experiment logging system
✅ **Templated** - Generate models easily
✅ **Machine-readable** - JSON output mode
✅ **Discoverable** - list-profiles, list-models commands

**Result**: Agents can now drive research autonomously with minimal human intervention!

---

## 📝 Next Steps for Agents

1. Read `/AGENT_README.md` for full context
2. Run `python3 -m backtest.cli list-profiles` to see what exists
3. Test the current best: `python3 -m backtest.cli run --profile sector_rotation_default`
4. Propose improvements to beat SPY
5. Create profiles and test variations
6. Log experiments to track learning
7. Report findings when hitting milestones or dead ends

**Good luck beating SPY! 🚀📈**
