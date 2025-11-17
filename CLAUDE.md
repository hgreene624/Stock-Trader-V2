# CLAUDE.md - Agent-First Trading Platform

**🤖 This is an AI-agent-first project.** You are expected to drive trading research autonomously.

---

## ⚡ Quick Start for Agents

**READ FIRST**: `/AGENT_README.md` - Comprehensive agent guide

**Your Role**: Autonomously propose, test, and iterate on trading strategies to beat SPY

**Current Goal**: Beat SPY's 14.34% CAGR (2020-2024)

**Best Model So Far**: SectorRotationModel_v1 @ 13.01% CAGR (126-day momentum + 1.25x leverage)
- Sharpe: 1.712, BPS: 0.784
- Within 1.33% of SPY (close!)
- See `WALK_FORWARD_GUIDE.md` for optimization methodology

**Your Workflow**:
1. User provides goal → 2. You propose approach → 3. You test → 4. You analyze → 5. You iterate → 6. You report

**Key Commands**:
```bash
# Run quick test
python3 -m backtest.analyze_cli --profile sector_rotation_leverage_1.25x

# View last results
python3 -m backtest.cli show-last

# Download data
python3 -m engines.data.cli download --symbols SPY,QQQ --start-date 2020-01-01 --timeframe 1D

# Walk-forward optimization (prevents overfitting!)
python3 -m engines.optimization.walk_forward_cli --quick

# Walk-forward in new tab for real-time monitoring (macOS)
python3 -m engines.optimization.walk_forward_cli --quick --new-tab

# Standard optimization (use with caution - can overfit)
python3 -m engines.optimization.cli run --experiment configs/experiments/my_exp.yaml
```

**Specialized Sub-Agents** (see [SUB_AGENTS.md](SUB_AGENTS.md)):
```
/agent.test      - Execute testing workflows autonomously
/agent.analyze   - Deep analysis of results and patterns
/agent.research  - Propose new strategies and approaches
/agent.optimize  - Systematic parameter optimization
```

**When to Check In**:
- ✅ Found strategy that beats SPY
- ✅ Hit dead end after 10+ iterations
- ✅ Need strategic direction (multiple paths)
- ✅ Major architecture changes planned

**What You Can Do Autonomously**:
- ✅ Create/modify models
- ✅ Add profiles to `configs/profiles.yaml`
- ✅ Run backtests and analyze results
- ✅ Iterate on parameters
- ✅ Troubleshoot issues
- ✅ Document findings

---

## Project Overview

Multi-model algorithmic trading platform combining equity trend following, index mean-reversion, and crypto momentum strategies with regime-aware portfolio management and systematic risk controls. The system progresses through research → backtest → paper → live stages with strict no-look-ahead bias enforcement.

**Primary decision frequency**: H4 (4-hour bars) with daily data as slow features
**Universe**: Equities (SPY, QQQ via Alpaca) and crypto (BTC, ETH via Binance/Kraken)
**Storage**: Parquet for data, DuckDB for results, JSON logs for events
**Testing**: 200+ unit and integration tests

## Architecture

### Core Principles (see .specify/constitution.md for full details)

1. **No Look-Ahead Bias**: Time alignment strictly enforced - at timestamp T, only data ≤ T is accessible
2. **Model Isolation**: Models receive Context (market state, features, regime, budget) and output target weights (0-1 of budget). They never access data files directly or know about other models
3. **Risk-First Design**: Risk Engine is final arbiter - enforces per-asset caps (40% NAV), asset class caps (crypto 20%), leverage limits (1.2x), and drawdown triggers (15%)
4. **Configuration-Driven**: All behavior controlled via YAML configs - zero hardcoded parameters in production code
5. **Unified Execution**: Same interface works in backtest/paper/live modes via broker adapters

### Data Flow

```
Data Sources (Yahoo Finance/CCXT)
    ↓
Parquet Files (data/equities/, data/crypto/)
    ↓
Data Pipeline (engines/data/pipeline.py) - computes features
    ↓
Context Object (models/base.py) - immutable market snapshot
    ↓
Models (models/*.py) - generate target weights
    ↓
Portfolio Engine (engines/portfolio/engine.py) - aggregates weights
    ↓
Risk Engine (engines/risk/engine.py) - enforces limits
    ↓
Execution Engine (backtest/executor.py or live/*) - executes trades
```

### Component Responsibilities

- **Models** (`models/`): Receive Context, return target weight vectors. No side effects.
- **Portfolio Engine** (`engines/portfolio/`): Aggregates multi-model weights, maintains attribution
- **Risk Engine** (`engines/risk/`): Enforces hard limits (per-asset, per-class, leverage, drawdown)
- **Regime Engine** (`engines/regime/`): Classifies market state (equity/vol/crypto/macro regimes)
- **Execution Engine** (`backtest/executor.py`, `live/`): Bar-by-bar simulation (backtest) or live order submission
- **Data Pipeline** (`engines/data/`): Downloads data, computes features, validates time alignment
- **Optimization** (`engines/optimization/`): Grid/random/evolutionary parameter search

## Quick Iteration Workflow (NEW!)

The platform now supports a streamlined workflow for rapid model testing:

```bash
# 1. Run a test using a pre-configured profile
python -m backtest.cli run --profile equity_trend_default

# 2. View results anytime
python -m backtest.cli show-last

# 3. Edit profile parameters in configs/profiles.yaml and re-run
python -m backtest.cli run --profile equity_trend_default
```

**Benefits**:
- ✅ Auto-downloads missing data
- ✅ Smart date defaults (last 5 years)
- ✅ Saves last run for quick review
- ✅ No need to remember complex command arguments

See [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) for detailed examples and iteration patterns.

## Common Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Validate entire platform
python validate_pipeline.py
```

### Testing
```bash
# Run all tests (200+ unit and integration tests)
pytest

# Run specific test categories
pytest tests/unit/                           # Unit tests only
pytest tests/integration/                    # Integration tests only
pytest tests/unit/agent.test_model_lifecycle.py    # Specific test file

# Run with coverage report
pytest --cov=. --cov-report=html

# Run critical no-lookahead test
pytest tests/agent.test_no_lookahead.py -v
```

### Data Management
```bash
# Download historical data
python -m engines.data.cli download \
    --symbols SPY QQQ \
    --asset-class equity \
    --timeframes 1D 4H \
    --start 2020-01-01

# Update existing data
python -m engines.data.cli update --asset-class equity

# Validate data quality
python -m engines.data.cli validate --symbols SPY QQQ

# Download crypto data
python -m engines.data.cli download \
    --symbols BTC/USD ETH/USD \
    --asset-class crypto \
    --timeframes 1D 4H \
    --start 2020-01-01
```

### Backtesting

**Profile-based (Recommended for iteration):**
```bash
# Quick test using a pre-configured profile
python -m backtest.cli run --profile equity_trend_default

# Override dates
python -m backtest.cli run --profile equity_trend_default --start 2023-01-01

# View last run results
python -m backtest.cli show-last

# Try different profiles
python -m backtest.cli run --profile equity_trend_aggressive
python -m backtest.cli run --profile mean_rev_default
```

**Traditional config-based:**
```bash
# Run backtest with config file
python -m backtest.cli run \
    --config configs/base/system.yaml \
    --start 2020-01-01 \
    --end 2024-12-31

# Run backtest with custom date range
python -m backtest.cli run \
    --config configs/base/system.yaml \
    --start 2023-01-01 \
    --end 2023-12-31
```

### Parameter Optimization
```bash
# Grid search (exhaustive)
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_001_equity_trend_grid.yaml

# Random search (sampling)
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_002_mean_reversion_random.yaml

# Evolutionary algorithm
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_003_crypto_momentum_ea.yaml

# List all experiments
python -m engines.optimization.cli list

# Compare experiments
python -m engines.optimization.cli compare exp_001 exp_002 exp_003

# Query results database
duckdb results/exp_001_equity_trend_grid.db
> SELECT * FROM experiment_results ORDER BY bps DESC LIMIT 10;
```

### Model Lifecycle Management
```bash
# View all models and their lifecycle stages
python -m backtest.cli list-models

# Promote model to next stage (research → candidate → paper → live)
python -m backtest.cli promote \
    --model EquityTrendModel_v1 \
    --reason "BPS=0.91, Sharpe=1.38, validated 2020-2024" \
    --operator your_name

# Demote model if performance degrades
python -m backtest.cli demote \
    --model EquityTrendModel_v1 \
    --reason "Paper trading underperformed expectations"

# View lifecycle history
cat logs/model_lifecycle_events.jsonl | jq .
```

### Paper and Live Trading
```bash
# Paper trading (only loads candidate/paper stage models)
python -m live.paper_runner --config configs/base/system.yaml

# Live trading (only loads live stage models, requires --confirm)
python -m live.live_runner \
    --config configs/base/system.yaml \
    --confirm
```

## Configuration

### Test Profiles (`configs/profiles.yaml`) - **NEW!**
- Pre-configured test scenarios for rapid iteration
- Includes model, universe, dates, and parameters
- Custom test slots (`my_test_1`, `my_test_2`) for your experiments
- Reusable universe definitions
- **Best for**: Quick parameter testing and iteration

### System Config (`configs/base/system.yaml`)
- Mode selection: backtest | paper | live
- Model registration with budget allocations
- Risk limits (per-asset caps, leverage, drawdown triggers)
- Timeframe and data paths
- **Best for**: Production configuration

### Model Parameters (`configs/base/models.yaml`)
- Model-specific parameters (MA periods, thresholds, etc.)
- Universe definition (symbols)
- Asset classes
- Execution hints (urgency, horizon)
- **Best for**: Permanent model parameter storage

### Experiment Configs (`configs/experiments/*.yaml`)
- Parameter grids/distributions for optimization
- Target model selection
- Optimization method (grid/random/evolutionary)
- Backtest period and metric to optimize
- **Best for**: Systematic parameter optimization

### Model Lifecycle State (`configs/.model_lifecycle.json`)
- Tracks current stage for each model (research/candidate/paper/live)
- DO NOT manually edit - use CLI commands

## Available Models

1. **EquityTrendModel_v1** (`models/equity_trend_v1.py`)
   - Strategy: 200D MA + 60D momentum trend following
   - Universe: SPY, QQQ
   - Key parameters: `slow_ma_period`, `momentum_lookback_days`, `exit_ma_period`

2. **IndexMeanReversionModel_v1** (`models/index_mean_rev_v1.py`)
   - Strategy: RSI + Bollinger Bands mean reversion
   - Universe: SPY, QQQ (4H bars)
   - Key parameters: `rsi_period`, `rsi_oversold`, `rsi_overbought`, `bb_period`

3. **CryptoMomentumModel_v1** (`models/crypto_momentum_v1.py`)
   - Strategy: 30-60 day dual momentum
   - Universe: BTC, ETH
   - Key parameters: `short_lookback`, `long_lookback`, `rebalance_days`

## Available Profiles (NEW!)

Pre-configured test profiles in `configs/profiles.yaml`:

**Equity Trend:**
- `equity_trend_default` - 200D MA, 60D momentum (baseline)
- `equity_trend_aggressive` - Faster MA periods (150/40/30)
- `equity_trend_conservative` - Slower MA periods (250/90/70)
- `equity_trend_recent` - Test on 2023-2024 only

**Mean Reversion:**
- `mean_rev_default` - Standard RSI+BB parameters
- `mean_rev_extreme` - More extreme thresholds
- `mean_rev_short_term` - Shorter periods for quick trades

**Crypto:**
- `crypto_momentum_default` - 30/60 day momentum
- `crypto_momentum_fast` - 14/30 day momentum
- `crypto_momentum_no_regime` - Without regime gating

**Custom Slots:**
- `my_test_1` - Your experiments here
- `my_test_2` - Another test slot

**Usage:**
```bash
# List available profiles
grep "^  [a-z_].*:" configs/profiles.yaml

# Run a profile
python -m backtest.cli run --profile equity_trend_default
```

## Key Design Patterns

### Adding a New Model

1. Inherit from `BaseModel` in `models/base.py`
2. Implement `generate_weights(context: Context) -> Dict[str, float]`
3. Register in `configs/base/models.yaml` with parameters
4. Add to `configs/base/system.yaml` with budget allocation
5. Write unit tests for signal logic
6. Run backtest to validate

Example structure:
```python
from models.base import BaseModel, Context

class MyNewModel_v1(BaseModel):
    def __init__(self, config: dict):
        super().__init__(config)
        self.my_param = config['parameters']['my_param']

    def generate_weights(self, context: Context) -> Dict[str, float]:
        # Access features: context.asset_features[symbol]['close']
        # Access regime: context.regime_state.equity_regime
        # Return weights: {"SPY": 0.5, "QQQ": 0.5}
        pass
```

### Time Alignment Rules

**CRITICAL**: Daily data is aligned to H4 bars using forward-fill to prevent look-ahead bias.

- Daily bar closes at 21:00 UTC (US market close)
- H4 boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
- At H4 timestamp T, use daily data from day T-1 if T < 21:00, else use day T

Alignment is handled automatically by `engines/data/pipeline.py` and validated in tests.

### Performance Metrics

- **BPS (Balanced Performance Score)**: Primary optimization metric
  - Formula: `0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×|MaxDD|`
  - Good: > 0.80, Excellent: > 1.00

- **Sharpe Ratio**: Risk-adjusted returns (annualized, good > 1.0)
- **CAGR**: Compound annual growth rate (good > 10%)
- **Max Drawdown**: Worst peak-to-trough decline (good > -20%)
- **Win Rate**: Fraction of profitable trades (good > 55%)

## Critical Validation

### Before Running Any Backtest
```bash
# Ensure no look-ahead bias
pytest tests/agent.test_no_lookahead.py -v

# Validate entire pipeline
python validate_pipeline.py
```

If `validate_pipeline.py` reports "FAILED: Data: Time Alignment (No Look-Ahead)", **DO NOT** run backtests until fixed - this indicates the system may be using future data.

### Before Promoting to Paper Trading
- Minimum requirements: Sharpe ≥ 1.0, MaxDD ≤ -20%, CAGR ≥ 10%, 10+ trades
- Verify on out-of-sample period (e.g., train on 2020-2022, validate on 2023-2024)
- Check strategy makes economic sense (not just curve-fitted)

### Before Going Live
- 30+ days of successful paper trading
- 10+ paper trades with acceptable slippage
- Manual review and explicit confirmation required
- Kill switch tested and accessible

## Logs and Results

### Structured Logs (`logs/`)
- `trades.log`: All trade executions with timestamps, symbols, quantities, prices
- `orders.log`: Order submissions and fills
- `performance.log`: Portfolio NAV snapshots at each H4 bar
- `errors.log`: Errors and exceptions with stack traces
- `model_lifecycle_events.jsonl`: Model promotions/demotions

All logs use JSON format and can be analyzed with `jq` or loaded into pandas.

### Results Database (`results/`)
- `*.db`: DuckDB databases with backtest/optimization results
- `*.csv`: Summary CSVs with top performers
- Query with DuckDB CLI or Python connector

## Troubleshooting

### "ModuleNotFoundError" or import errors
Ensure virtual environment is activated and dependencies installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### "FileNotFoundError: data/equities/SPY_4H.parquet"
Download data first:
```bash
python -m engines.data.cli download --symbols SPY QQQ --start 2020-01-01
```

### "ValueError: timestamp must be H4-aligned"
Data timestamps must be at H4 boundaries. Re-download using the CLI which handles alignment automatically.

### Backtest runs but all trades have zero profit
Check:
1. Slippage/fees not set too high
2. Model is actually generating non-zero weights
3. Date range has sufficient data (need 200+ days for 200D MA)

### Optimization is very slow
- Reduce parameter grid size
- Shorten backtest period
- Use random search instead of grid search
- Enable multiprocessing in experiment config

## Important Notes

- **Risk Controls**: All limits in `configs/base/system.yaml` under `risk:` are enforced before execution. Models cannot override these.

- **Regime Budgets**: Budget adjustments based on regime are in `configs/base/regime_budgets.yaml`. E.g., reduce equity trend budget in bear markets.

- **Data Sources**: Equity data from Yahoo Finance (free), crypto from exchange APIs. For production, consider paid data providers for better quality.

- **Broker Adapters**: Alpaca (equities) requires API keys in config. Crypto exchanges (Binance/Kraken) support both paper and live modes with separate credentials.

- **Reproducibility**: Same config + same data = identical backtest results. Logs include full config snapshots for each run.

- **Documentation**: See `specs/001-trading-platform/` for detailed specification, implementation plan, and task breakdown. Constitution is in `.specify/constitution.md`.

## Quick Reference

| Task | Command |
|------|---------|
| Setup environment | `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` |
| Validate platform | `python validate_pipeline.py` |
| Run all tests | `pytest` |
| **Quick test (profile)** | `python -m backtest.analyze_cli --profile sector_rotation_leverage_1.25x` |
| **View last results** | `python -m backtest.cli show-last` |
| Download data | `python -m engines.data.cli download --symbols SPY QQQ --start 2020-01-01` |
| Run backtest (traditional) | `python -m backtest.cli run --config configs/base/system.yaml` |
| **Walk-forward optimization** | `python -m engines.optimization.walk_forward_cli --quick` |
| **Walk-forward (monitored)** | `python -m engines.optimization.walk_forward_cli --quick --new-tab` |
| Standard optimization | `python -m engines.optimization.cli run --experiment configs/experiments/exp_001_equity_trend_grid.yaml` |
| View model stages | `python -m backtest.cli list-models` |
| Promote model | `python -m backtest.cli promote --model MODEL_NAME --reason "REASON"` |
| Paper trading | `python -m live.paper_runner --config configs/base/system.yaml` |

## Additional Resources

- **Walk-Forward Guide**: [WALK_FORWARD_GUIDE.md](WALK_FORWARD_GUIDE.md) - **NEW!** Prevent overfitting with out-of-sample validation
- **Walk-Forward Implementation**: [WALK_FORWARD_IMPLEMENTATION.md](WALK_FORWARD_IMPLEMENTATION.md) - Technical details
- **Monitoring Long Runs**: [docs/MONITORING_LONG_RUNS.md](docs/MONITORING_LONG_RUNS.md) - **NEW!** Real-time progress monitoring for EA optimization
- **Workflow Guide**: [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) - Rapid iteration patterns using profiles
- **Session Summaries**: [SESSION_SUMMARY_2025-11-17_CONTINUED.md](SESSION_SUMMARY_2025-11-17_CONTINUED.md) - Recent improvements
- **Quickstart Guide**: [QUICKSTART.md](QUICKSTART.md) - Detailed 30-minute walkthrough
- **Validation Guide**: [VALIDATION_GUIDE.md](VALIDATION_GUIDE.md) - Platform validation procedures
- **Constitution**: [.specify/constitution.md](.specify/constitution.md) - Architectural principles
- **Full Specification**: `specs/001-trading-platform/spec.md`
- **Implementation Plan**: `specs/001-trading-platform/plan.md`
- **Test Results**: Run `pytest` to execute 200+ tests
