# Experiment Protocol

This document defines the standardized structure and workflow for all trading experiments.

## Directory Structure

Every experiment MUST follow this directory structure:

```
docs/research/experiments/XXX_experiment_name/
├── README.md                    # Main results document (required)
├── manifest.json                # Machine-readable metadata (required)
├── config/
│   ├── experiment.yaml          # Experiment configuration
│   └── profiles.yaml            # Test profiles used
├── logs/
│   └── *.log                    # All run logs
├── results/
│   ├── backtests/
│   │   └── *.json               # Individual backtest results
│   └── optimization/
│       └── *.json               # Optimization results (EA, grid, etc.)
└── analysis/
    ├── figures/
    │   ├── equity_curve.png     # Portfolio value over time
    │   ├── drawdown.png         # Drawdown chart
    │   └── *.png                # Additional visualizations
    └── summary.json             # Aggregated metrics
```

## Required Files

### 1. README.md
Main human-readable results document using this format:

```markdown
# EXP-XXX: Title

**Date**: YYYY-MM-DD
**Model**: Model name
**Status**: Planning | In Progress | Completed | Failed

## Hypothesis
What we're testing and why

## Methods
- Parameters tested
- Backtest period
- Optimization method (if applicable)

## Results

### Summary Table
| Variant | CAGR | Sharpe | BPS | Max DD | Trades |
|---------|------|--------|-----|--------|--------|

### Key Metrics
- Best performer: [variant name]
- vs SPY (14.34%): [comparison]

## Conclusion
Key findings and recommended next action

## Files
- Config: `config/experiment.yaml`
- Best result: `results/backtests/best_run.json`
- Analysis: `analysis/figures/`
```

### 2. manifest.json
Machine-readable metadata:

```json
{
  "experiment_id": "004",
  "name": "atr_stop_loss",
  "title": "ATR Stop Loss Optimization",
  "date_created": "2025-11-23",
  "date_completed": "2025-11-23",
  "status": "completed",
  "model": "SectorRotationAdaptive_v3",
  "method": "evolutionary",
  "best_result": {
    "bps": 1.028,
    "cagr": 0.1245,
    "sharpe": 1.85,
    "params": {
      "atr_period": 21,
      "stop_loss_atr_mult": 1.6
    }
  },
  "files": {
    "config": "config/experiment.yaml",
    "best_backtest": "results/backtests/ea_optimized.json",
    "analysis": "analysis/summary.json"
  }
}
```

## Sub-Agent Responsibilities

Each sub-agent has specific responsibilities in the experiment workflow:

### /agent.research
- Creates experiment folder and README.md skeleton
- Defines hypothesis and method
- Creates `config/experiment.yaml`
- Updates manifest.json with initial metadata

### /agent.optimize (if optimization needed)
- Runs optimization (grid/random/EA)
- Saves results to `results/optimization/`
- Saves all logs to `logs/`
- Updates manifest.json with optimization results

### /agent.test
- Runs backtests with specific profiles
- Saves results to `results/backtests/`
- Saves logs to `logs/`
- Creates profiles in `config/profiles.yaml`

### /agent.analyze
- Generates figures in `analysis/figures/`
- Creates `analysis/summary.json`
- Updates README.md with results tables
- Provides conclusions and recommendations

## Workflow

### Phase 1: Setup (/agent.research)
```bash
# Create experiment directory
mkdir -p docs/research/experiments/004_atr_stop_loss/{config,logs,results/backtests,results/optimization,analysis/figures}

# Create initial files
# - README.md with hypothesis
# - manifest.json with metadata
# - config/experiment.yaml
```

### Phase 2: Optimization (/agent.optimize)
```bash
# Run optimization
python3 -m engines.optimization.cli run \
  --experiment docs/research/experiments/004_atr_stop_loss/config/experiment.yaml \
  2>&1 | tee docs/research/experiments/004_atr_stop_loss/logs/optimization.log

# Results automatically saved to results/optimization/
```

### Phase 3: Validation (/agent.test)
```bash
# Run validation backtest
python3 -m backtest.analyze_cli --profile ea_optimized \
  --output-dir docs/research/experiments/004_atr_stop_loss/results/backtests \
  2>&1 | tee docs/research/experiments/004_atr_stop_loss/logs/validation.log
```

### Phase 4: Analysis (/agent.analyze)
```bash
# Generate analysis
python3 -m backtest.analyze_cli --profile ea_optimized \
  --charts docs/research/experiments/004_atr_stop_loss/analysis/figures \
  --summary docs/research/experiments/004_atr_stop_loss/analysis/summary.json
```

### Phase 5: Documentation (any agent)
- Update README.md with final results
- Update manifest.json with completion status
- Update docs/research/experiments/INDEX.md

## Output Naming Conventions

### Backtest Results
- `results/backtests/{profile_name}.json` - Single backtest
- `results/backtests/{variant}_{date}.json` - Dated variant

### Optimization Results
- `results/optimization/ea_final.json` - EA results
- `results/optimization/grid_results.json` - Grid search
- `results/optimization/random_results.json` - Random search

### Figures
- `analysis/figures/equity_curve.png` - Main equity curve
- `analysis/figures/drawdown.png` - Drawdown chart
- `analysis/figures/comparison_{variant}.png` - Comparison charts
- `analysis/figures/parameter_sensitivity.png` - Parameter heatmaps

### Logs
- `logs/run_{n}.log` - Numbered run logs
- `logs/optimization.log` - Optimization run
- `logs/validation.log` - Validation backtest

## Best Practices

1. **Always use sub-agents** - Each phase should invoke the appropriate sub-agent
2. **Keep everything in the experiment** - No results in /tmp or scattered locations
3. **Update manifest.json** - Keep it current as experiment progresses
4. **Generate figures** - Visual results are essential for review
5. **Document conclusions** - README should have clear, actionable findings
6. **Update INDEX.md** - Register experiment in master index when complete

## Quick Commands

```bash
# Create new experiment
EXP_DIR="docs/research/experiments/005_new_experiment"
mkdir -p "$EXP_DIR"/{config,logs,results/backtests,results/optimization,analysis/figures}

# Run with output to experiment
python3 -m backtest.analyze_cli --profile my_test \
  --output-dir "$EXP_DIR/results/backtests" \
  2>&1 | tee "$EXP_DIR/logs/backtest.log"
```
