# Multi-Model Algorithmic Trading Platform

A production-ready algorithmic trading platform that combines multiple strategy models (equity trend, index mean-reversion, crypto momentum) with regime-aware portfolio management, systematic parameter optimization, and comprehensive risk controls.

## Features

- ✅ **Multi-Model Architecture**: Run multiple trading strategies simultaneously with independent budgets
- ✅ **Parameter Optimization**: Grid search, random search, and evolutionary algorithms to find best-performing models
- ✅ **Model Lifecycle Management**: Systematic progression from research → candidate → paper → live
- ✅ **Risk-First Design**: Hard limits on exposures, leverage, and automatic drawdown enforcement
- ✅ **Regime-Aware**: Automatically adapt budgets based on market conditions (equity/vol/crypto/macro regimes)
- ✅ **No Look-Ahead Bias**: Strict enforcement ensures backtests use only past data
- ✅ **Multi-Asset Support**: Trade equities (via Alpaca) and cryptocurrencies (via Binance/Kraken)
- ✅ **H4 Trading**: Primary decision frequency on 4-hour bars with daily data as slow features
- ✅ **Comprehensive Testing**: 200+ unit and integration tests ensuring platform reliability

## Quick Start

See **[QUICKSTART.md](QUICKSTART.md)** for a comprehensive guide to exploring models and finding high-performers.

**30-Minute Workflow:**
1. Setup environment and download data (10 min)
2. Run baseline backtest (5 min)
3. Run optimization experiment to find best parameters (15 min)
4. Analyze results and promote winning models

### Prerequisites

- Python 3.9 or higher
- 500 MB disk space for dependencies + data
- Internet connection for data download

### Installation

```bash
# Clone/navigate to project
cd /path/to/PythonProject

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install pandas==2.1.0 numpy==1.25.0 pyarrow==13.0.0 \
            pyyaml==6.0.1 pydantic==2.4.0 \
            python-json-logger==2.0.7 yfinance==0.2.28 \
            duckdb==0.9.0 deap==1.4.1 pytest==7.4.0

# Validate installation
python validate_pipeline.py
# Expected: ✓ ALL TESTS PASSED - PLATFORM READY
```

### Run Your First Backtest

```bash
# 1. Download data
python -m engines.data.cli download \
    --symbols SPY QQQ \
    --asset-class equity \
    --timeframes 1D 4H \
    --start 2020-01-01

# 2. Run backtest
python -m backtest.cli run \
    --config configs/base/system.yaml \
    --start 2020-01-01 \
    --end 2024-12-31

# 3. View results
ls results/  # DuckDB database
ls logs/     # JSON logs (trades, performance)
```

### Find Better Models with Optimization

```bash
# Run grid search to find best parameters
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_001_equity_trend_grid.yaml

# View top performers
head -11 results/exp_001_summary.csv | column -t -s,
```

## Project Structure

```
project/
├── data/                       # Historical data (Parquet files)
│   ├── equities/               # SPY_1D.parquet, SPY_4H.parquet, etc.
│   ├── crypto/                 # BTC-USD_1D.parquet, ETH-USD_4H.parquet, etc.
│   └── macro/                  # yield_curve.parquet, pmi.parquet
│
├── configs/                    # YAML configuration
│   ├── base/                   # Default system configs
│   │   ├── system.yaml         # System settings (mode, models, risk)
│   │   ├── models.yaml         # Model parameters
│   │   └── regime_budgets.yaml # Regime-based budget adjustments
│   ├── experiments/            # Optimization experiment configs
│   │   ├── exp_001_equity_trend_grid.yaml
│   │   ├── exp_002_mean_reversion_random.yaml
│   │   └── exp_003_crypto_momentum_ea.yaml
│   └── .model_lifecycle.json   # Model lifecycle state tracking
│
├── models/                     # Strategy implementations
│   ├── base.py                 # BaseModel abstract class, Context, ModelOutput
│   ├── equity_trend_v1.py      # 200D MA + momentum trend following
│   ├── index_mean_rev_v1.py    # RSI + Bollinger Bands mean reversion
│   └── crypto_momentum_v1.py   # 30-60D momentum crypto strategy
│
├── engines/                    # Core engines
│   ├── data/                   # Data pipeline
│   │   ├── cli.py              # Data download/update CLI
│   │   ├── pipeline.py         # Centralized feature computation
│   │   ├── validator.py        # Data quality validation
│   │   └── aligner.py          # H4 alignment enforcement
│   ├── portfolio/              # Multi-model portfolio
│   │   ├── engine.py           # Weight aggregation & attribution
│   │   └── attribution.py      # Model performance attribution
│   ├── risk/                   # Risk management
│   │   ├── engine.py           # Risk limit enforcement
│   │   └── scaling.py          # Regime-based scaling
│   ├── regime/                 # Market regime classification
│   │   └── engine.py           # Equity/vol/crypto/macro regimes
│   ├── optimization/           # Parameter optimization
│   │   ├── cli.py              # Optimization CLI
│   │   ├── grid_search.py      # Exhaustive grid search
│   │   ├── evolutionary.py     # Genetic algorithm
│   │   └── reporting.py        # Results analysis & comparison
│   └── execution/              # (Future: backtest/paper/live execution)
│
├── backtest/                   # Backtesting
│   ├── cli.py                  # Backtest + lifecycle management CLI
│   ├── runner.py               # Backtest orchestration
│   ├── executor.py             # Bar-by-bar simulation
│   └── reporting.py            # Performance reports
│
├── live/                       # Paper & live trading
│   ├── paper_runner.py         # Paper trading (candidate/paper models only)
│   └── live_runner.py          # Live trading (live models only)
│
├── utils/                      # Shared utilities
│   ├── logging.py              # Structured JSON logging
│   ├── config.py               # YAML config loader
│   ├── time.py                 # H4 alignment helpers
│   └── metrics.py              # Performance metrics (Sharpe, CAGR, BPS)
│
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests (150+ tests)
│   │   ├── test_portfolio_aggregation.py
│   │   ├── test_risk_enforcement.py
│   │   ├── test_regime_classification.py
│   │   └── test_model_lifecycle.py
│   └── integration/            # Integration tests (50+ tests)
│       ├── test_backtest_workflow.py
│       ├── test_optimization_pipeline.py
│       └── test_model_lifecycle.py
│
├── logs/                       # Structured JSON logs (gitignored)
│   ├── trades.log              # Trade executions
│   ├── orders.log              # Order submissions
│   ├── performance.log         # Portfolio snapshots
│   ├── errors.log              # Errors and exceptions
│   └── model_lifecycle_events.jsonl  # Model promotions/demotions
│
├── results/                    # Backtest & optimization results (gitignored)
│   ├── *.db                    # DuckDB databases
│   └── *.csv                   # Summary CSVs
│
├── validate_pipeline.py        # Comprehensive validation script
├── test_functionality.py       # Functional test script
└── README.md                   # This file
```

## Available Models

### 1. EquityTrendModel_v1
**Strategy**: 200-day MA + momentum trend following
**Universe**: SPY, QQQ (major equity indexes)
**Best For**: Bull markets, trending conditions
**Key Parameters**:
- `slow_ma_period`: Long-term MA filter (default: 200)
- `momentum_lookback_days`: Momentum calculation window (default: 60)
- `exit_ma_period`: Exit signal MA (default: 50)

**Optimization Example**:
```bash
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_001_equity_trend_grid.yaml
```

### 2. IndexMeanReversionModel_v1
**Strategy**: RSI + Bollinger Bands mean reversion
**Universe**: SPY, QQQ (4H bars)
**Best For**: Ranging markets, choppy conditions
**Key Parameters**:
- `rsi_period`: RSI calculation period (default: 2)
- `rsi_oversold`: Oversold threshold (default: 10)
- `rsi_overbought`: Overbought threshold (default: 90)
- `bb_period`: Bollinger Band period (default: 20)

**Optimization Example**:
```bash
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_002_mean_reversion_random.yaml
```

### 3. CryptoMomentumModel_v1
**Strategy**: 30-60 day momentum
**Universe**: BTC, ETH
**Best For**: Crypto bull markets
**Key Parameters**:
- `short_lookback`: Short momentum window (default: 30 days)
- `long_lookback`: Long momentum window (default: 60 days)
- `rebalance_days`: Rebalancing frequency (default: 7)

**Optimization Example**:
```bash
# First download crypto data
python -m engines.data.cli download \
    --symbols BTC/USD ETH/USD \
    --asset-class crypto \
    --timeframes 1D 4H \
    --start 2020-01-01

# Then optimize
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_003_crypto_momentum_ea.yaml
```

## Model Lifecycle Management

Models progress through 4 stages with validation at each step:

```
research → candidate → paper → live
```

### Lifecycle Stages

1. **research**: Development and backtesting
   - No restrictions
   - For experimentation and parameter tuning

2. **candidate**: Passed backtest validation
   - Requirements: Sharpe ≥ 1.0, MaxDD ≤ -20%, CAGR ≥ 10%, 10+ trades
   - Eligible for paper trading

3. **paper**: Live market testing with simulated execution
   - Runs for 30+ days in paper mode
   - Must complete 10+ paper trades with acceptable slippage

4. **live**: Production trading with real capital
   - Requires manual approval after paper validation
   - Only accessible via live runner with `--confirm` flag

### Managing Lifecycle

```bash
# View current status of all models
python -m backtest.cli list-models

# Promote model after successful backtest
python -m backtest.cli promote \
    --model EquityTrendModel_v1 \
    --reason "BPS=0.91, Sharpe=1.38, validated 2020-2024" \
    --operator your_name

# Demote if performance degrades
python -m backtest.cli demote \
    --model EquityTrendModel_v1 \
    --reason "Paper trading underperformed"

# View lifecycle history
cat logs/model_lifecycle_events.jsonl | jq .
```

### Lifecycle Filtering

- **Backtest Runner**: Runs all models regardless of stage
- **Paper Runner**: Only loads `candidate` and `paper` stage models
- **Live Runner**: Only loads `live` stage models

This ensures proper validation before risking real capital.

## Configuration

All system behavior is controlled via YAML configuration files in `configs/`:

### System Config (`configs/base/system.yaml`)

```yaml
system:
  mode: "backtest"  # backtest | paper | live
  backtest_initial_nav: 100000.00
  timeframe: "H4"

  models:
    - name: "EquityTrendModel_v1"
      version: "1.0.0"
      status: "research"
      budget_fraction: 0.40  # 40% of NAV

    - name: "IndexMeanReversionModel_v1"
      version: "1.0.0"
      status: "research"
      budget_fraction: 0.30  # 30% of NAV

  risk:
    per_asset_cap: 0.40        # Max 40% NAV per asset
    crypto_class_cap: 0.20     # Max 20% NAV in crypto
    max_leverage: 1.2          # Max 1.2x gross exposure
    drawdown_trigger: 0.15     # De-risk at 15% drawdown
    drawdown_halt: 0.20        # Full exit at 20% drawdown
    derisking_factor: 0.50     # Reduce to 50% on trigger
```

### Model Parameters (`configs/base/models.yaml`)

```yaml
models:
  EquityTrendModel_v1:
    universe: ["SPY", "QQQ"]
    asset_classes: ["equity"]

    parameters:
      slow_ma_period: 200
      momentum_lookback_days: 60
      exit_ma_period: 50
      equal_weight: true
      max_positions: 2
```

Update parameters here after finding optimal values via optimization.

### Experiment Config (`configs/experiments/*.yaml`)

```yaml
experiment:
  name: "my_optimization"
  method: "grid"  # grid | random | evolutionary
  target_model: "EquityTrendModel_v1"

  parameter_grid:
    models.EquityTrendModel_v1.parameters.slow_ma_period: [150, 200, 250]
    models.EquityTrendModel_v1.parameters.momentum_lookback_days: [30, 60, 90]

  optimization:
    metric: "bps"  # Balanced Performance Score
    maximize: true
    save_top_n: 10
```

## Parameter Optimization

The platform includes 3 optimization methods to find best-performing parameters:

### 1. Grid Search (Exhaustive)

Tests ALL combinations of parameters.

**Use when**: Small parameter space (< 100 combinations)
**Example**: 3 MA periods × 4 momentum lookbacks × 3 exit MAs = 36 backtests

```bash
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_001_equity_trend_grid.yaml
```

**Output**: Ranked list of all 36 parameter sets by BPS score

### 2. Random Search (Sampling)

Tests random samples from parameter distributions.

**Use when**: Large parameter space (100+ combinations)
**Example**: Sample 50 random combinations from continuous distributions

```bash
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_002_mean_reversion_random.yaml
```

**Output**: Top N performers from random sample

### 3. Evolutionary Algorithm (Genetic)

Evolves population toward better parameters over generations.

**Use when**: Complex parameter interactions
**Example**: Population of 20, evolve over 15 generations

```bash
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_003_crypto_momentum_ea.yaml
```

**Output**: Best individuals from final generation

### Comparing Results

```bash
# List all experiments
python -m engines.optimization.cli list

# Compare multiple experiments
python -m engines.optimization.cli compare exp_001 exp_002 exp_003

# Query results database
duckdb results/exp_001_equity_trend_grid.db
> SELECT * FROM experiment_results ORDER BY bps DESC LIMIT 10;
```

## Risk Controls

The platform enforces non-negotiable risk limits via the Risk Engine:

- **Per-Asset Cap**: Max 40% NAV in any single asset
- **Asset Class Cap**: Max 20% NAV in crypto, configurable per class
- **Gross Leverage**: Max 1.2x NAV (configurable)
- **Drawdown Auto-Derisking**: 50% reduction at 15% drawdown
- **Drawdown Halt**: Full exit at 20% drawdown
- **Kill Switch**: Immediate order halt via config or command

All limits are enforced before execution - orders that would violate limits are scaled down or rejected.

## Performance Metrics

### Balanced Performance Score (BPS)

Primary optimization metric combining multiple factors:

```
BPS = 0.4 × Sharpe + 0.3 × CAGR + 0.2 × WinRate - 0.1 × |MaxDrawdown|
```

**Interpretation**:
- BPS > 0.80: Good
- BPS > 1.00: Excellent
- BPS > 1.20: Outstanding

### Individual Metrics

- **Sharpe Ratio**: Risk-adjusted returns (annualized)
  - Good: > 1.0
  - Excellent: > 1.5

- **CAGR**: Compound annual growth rate
  - Good: > 10%
  - Excellent: > 15%

- **Max Drawdown**: Worst peak-to-trough decline
  - Good: > -20%
  - Excellent: > -15%

- **Win Rate**: Fraction of profitable trades
  - Good: > 55%
  - Excellent: > 60%

## Development

### Running Tests

```bash
# Run all tests (200+ tests)
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific categories
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest tests/unit/test_model_lifecycle.py  # Specific test file

# Validate entire pipeline
python validate_pipeline.py
```

### Code Quality

```bash
# Format code (if black installed)
black .

# Lint (if flake8 installed)
flake8 .

# Type checking (if mypy installed)
mypy .
```

## Usage Examples

### Single Model Backtest

```bash
python -m backtest.cli run \
    --config configs/base/system.yaml \
    --start 2020-01-01 \
    --end 2024-12-31
```

### Multi-Model Portfolio

Edit `configs/base/system.yaml` to add multiple models with budget allocations, then:

```bash
python -m backtest.cli run --config configs/base/system.yaml
```

### Parameter Optimization

```bash
# Grid search
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_001_equity_trend_grid.yaml

# Random search
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_002_mean_reversion_random.yaml

# Evolutionary algorithm
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_003_crypto_momentum_ea.yaml
```

### Paper Trading

```bash
# Ensure model is at candidate or paper stage
python -m backtest.cli promote --model EquityTrendModel_v1

# Run paper trading (only loads candidate/paper models)
python -m live.paper_runner --config configs/base/system.yaml
```

### Live Trading

⚠️ **WARNING**: Only proceed after thorough paper trading validation

```bash
# Promote to live stage
python -m backtest.cli promote --model EquityTrendModel_v1

# Run live trading (requires --confirm flag)
python -m live.live_runner \
    --config configs/base/system.yaml \
    --confirm
```

## Documentation

- **[Quickstart Guide](QUICKSTART.md)**: Detailed walkthrough for model exploration
- **[Validation Guide](VALIDATION_GUIDE.md)**: Platform validation procedures
- **[Specification](specs/001-trading-platform/spec.md)**: Business requirements
- **[Implementation Plan](specs/001-trading-platform/plan.md)**: Technical architecture
- **[Data Model](specs/001-trading-platform/data-model.md)**: Entities and relationships
- **[Research](specs/001-trading-platform/research.md)**: Technology decisions
- **[Tasks](specs/001-trading-platform/tasks.md)**: Implementation task breakdown
- **[Constitution](.specify/constitution.md)**: Architectural principles

## Key Commands

```bash
# Data Management
python -m engines.data.cli download --symbols SPY QQQ --start 2020-01-01
python -m engines.data.cli update --asset-class equity
python -m engines.data.cli validate --symbols SPY QQQ

# Backtesting
python -m backtest.cli run --config configs/base/system.yaml
python -m backtest.cli list-models

# Lifecycle Management
python -m backtest.cli promote --model MODEL_NAME --reason "REASON"
python -m backtest.cli demote --model MODEL_NAME --reason "REASON"

# Optimization
python -m engines.optimization.cli run --experiment EXPERIMENT.yaml
python -m engines.optimization.cli list
python -m engines.optimization.cli compare exp1 exp2 exp3

# Trading
python -m live.paper_runner --config configs/base/system.yaml
python -m live.live_runner --config configs/base/system.yaml --confirm

# Testing & Validation
python validate_pipeline.py
pytest
pytest tests/integration/
```

## Contributing

This is a private trading platform. See `specs/001-trading-platform/tasks.md` for implementation roadmap and status.

## License

Proprietary - All rights reserved

## Support

For issues or questions:
1. Check documentation in `specs/001-trading-platform/`
2. Review error logs in `logs/errors.log`
3. Run validation: `python validate_pipeline.py`
4. Consult constitution at `.specify/constitution.md`

## Disclaimer

This software is for educational and research purposes. Trading involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk.

---

**Built with**: Python, Pandas, DuckDB, PyArrow, YAML
**Architecture**: Multi-model portfolio system with regime awareness and systematic risk management
**Testing**: 200+ unit and integration tests ensuring reliability
**Documentation**: Comprehensive specs, plans, and guides in `specs/`
