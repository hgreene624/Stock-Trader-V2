# Optimization Results Tracking System

## Overview

The optimization tracking system provides a centralized way to save, query, and compare optimization experiment results across multiple runs.

---

## What It Saves

For each optimization experiment, the system tracks:

✅ **Experiment Metadata:**
- Name & method (grid/random/evolutionary)
- Model & backtest period
- Total runs & best metric achieved
- Timestamp

✅ **Parameter Sets & Full Metrics:**
- Parameters tested (momentum_period, top_n, etc.)
- Complete performance metrics:
  - CAGR, Sharpe Ratio, Max Drawdown
  - Total Return, Win Rate, BPS
  - Trade count, Final NAV
- Validation period (in-sample/out-of-sample/full)
- Notes

---

## Quick Start

### 1. View Leaderboard (All-Time Best Results)

```bash
# Top 20 results by BPS
python3 -m utils.optimization_tracker_cli leaderboard

# Top 10 by CAGR
python3 -m utils.optimization_tracker_cli leaderboard --limit 10 --metric cagr

# Top 5 by Sharpe
python3 -m utils.optimization_tracker_cli leaderboard --limit 5 --metric sharpe_ratio
```

### 2. View Results for Specific Experiment

```bash
python3 -m utils.optimization_tracker_cli experiment --experiment my_experiment_name
```

### 3. Compare Multiple Experiments

```bash
python3 -m utils.optimization_tracker_cli compare --experiments exp1 exp2 exp3
```

### 4. Export Best Parameters to JSON

```bash
python3 -m utils.optimization_tracker_cli export \
  --experiment my_experiment \
  --output results/best_params.json
```

---

## Manual Logging Example

You can manually log results (useful for ad-hoc tests):

```python
from utils.optimization_tracker import OptimizationTracker

# Initialize
tracker = OptimizationTracker()

# Log experiment
exp_id = tracker.log_experiment(
    name="sector_rotation_leverage_test",
    method="manual",
    model="SectorRotationModel_v1",
    backtest_period="2020-2024",
    total_runs=3,
    best_metric=0.87,
    metric_name="bps"
)

# Log a result
tracker.log_result(
    experiment_id=exp_id,
    parameters={
        'momentum_period': 126,
        'top_n': 3,
        'min_momentum': 0.0,
        'target_leverage': 1.25
    },
    metrics={
        'cagr': 0.1487,
        'sharpe_ratio': 1.91,
        'max_drawdown': -0.3593,
        'total_return': 1.0190,
        'win_rate': 0.50,
        'bps': 0.87,
        'total_trades': 3325,
        'final_nav': 201548
    },
    validation_period="full",
    notes="With 1.25x leverage - BEATS SPY!"
)

# Clean up
tracker.close()
```

---

## Database Location

Results are stored in: `results/optimization_tracker.db` (DuckDB format)

You can query directly with DuckDB:

```bash
duckdb results/optimization_tracker.db

# Example queries:
SELECT * FROM leaderboard LIMIT 10;
SELECT * FROM experiments ORDER BY timestamp DESC;
SELECT * FROM results WHERE cagr > 0.15;
```

---

## Integration with Optimization CLI

✅ **AUTO-SAVING IS NOW ENABLED!**

Every optimization run automatically saves to the tracker:
- Full experiment metadata
- All parameter sets tested
- Complete performance metrics (CAGR, Sharpe, Max DD, etc.)
- Automatically added to leaderboard

**Just run your optimization and results are saved automatically:**

```bash
python3 -m engines.optimization.cli run --experiment configs/experiments/my_exp.yaml
```

At the end, you'll see:
```
================================================================================
SAVING TO OPTIMIZATION TRACKER
================================================================================
✓ Experiment logged (ID: 2)
✓ Saved 300 results to tracker

📊 Top 3 from this run:
  1. BPS=1.173, CAGR=17.82% | momentum_period=77, top_n=3, min_momentum=0.044
  2. BPS=1.126, CAGR=16.95% | momentum_period=78, top_n=3, min_momentum=0.039
  3. BPS=1.097, CAGR=16.21% | momentum_period=77, top_n=3, min_momentum=0.042
```

---

## Example Workflow

```bash
# 1. Run optimization
python3 -m engines.optimization.cli run --experiment configs/experiments/my_exp.yaml

# 2. Manually log results (for now)
# Use Python script or demo as template

# 3. View leaderboard
python3 -m utils.optimization_tracker_cli leaderboard

# 4. Export best params
python3 -m utils.optimization_tracker_cli export \
  --experiment my_exp \
  --output results/best_my_exp.json

# 5. Create profile from best params
# Use exported JSON to create new profile in configs/profiles.yaml
```

---

## Files Created

1. **`utils/optimization_tracker.py`** - Main tracking system
2. **`utils/optimization_tracker_cli.py`** - CLI interface
3. **`examples/demo_optimization_tracking.py`** - Demo/example
4. **`results/optimization_tracker.db`** - DuckDB database (auto-created)

---

## Benefits

✅ **Never lose optimization results** - All experiments saved permanently
✅ **Compare across runs** - See which approach worked best
✅ **Track progress over time** - See improvement trajectory
✅ **Easy parameter extraction** - Export best params to JSON
✅ **SQL queryable** - Use DuckDB for advanced analysis

---

## Next Steps

1. **Integrate with optimization CLI** to auto-save results
2. **Add visualization** (plotly charts of parameter spaces)
3. **Walk-forward analysis tracking** (in-sample vs out-of-sample)
4. **Parameter sensitivity analysis** (which params matter most)

---

## Current Status

✅ System implemented and tested
✅ CLI working
✅ Manual logging demonstrated
⏳ Integration with optimization CLI (future enhancement)
⏳ Walk-forward optimization support (next task)
