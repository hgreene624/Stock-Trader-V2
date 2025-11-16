# Multi-Model Algorithmic Trading Platform

A production-ready algorithmic trading platform that combines multiple strategy models (equity trend, index mean-reversion, crypto momentum) with regime-aware portfolio management and risk controls.

## Features

- **Multi-Model Architecture**: Run multiple trading strategies simultaneously with independent budgets
- **Risk-First Design**: Hard limits on exposures, leverage, and drawdown enforcement
- **Regime-Aware**: Automatically adapt budgets based on market conditions (equity/vol/crypto/macro regimes)
- **No Look-Ahead Bias**: Strict enforcement ensures backtests use only past data
- **Multi-Asset Support**: Trade equities (via Alpaca) and cryptocurrencies (via Binance/Kraken)
- **H4 Trading**: Primary decision frequency on 4-hour bars with daily data as slow features
- **Progression Path**: Research → Backtest → Paper → Live trading with systematic validation

## Quick Start

See [quickstart.md](specs/001-trading-platform/quickstart.md) for detailed setup instructions.

### Prerequisites

- Python 3.9 or higher
- 500 MB disk space for dependencies + data
- Internet connection for data download and broker APIs

### Installation

```bash
# Clone repository
cd /path/to/PythonProject

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys (optional for backtest-only usage)
```

### Run Your First Backtest

```bash
# Download sample data (SPY, QQQ for 2020-2025)
python -m engines.data.cli download --symbols SPY QQQ --start 2020-01-01 --end 2025-01-15

# Run backtest with default config
python -m backtest.cli run --config configs/base/system.yaml

# View results
ls results/  # DuckDB database with metrics
ls logs/     # JSON logs (trades, performance, errors)
```

## Project Structure

```
project/
├── data/                   # Historical data (Parquet files)
│   ├── equities/           # SPY_h4.parquet, SPY_daily.parquet, etc.
│   ├── crypto/             # BTC_h4.parquet, ETH_h4.parquet, etc.
│   └── macro/              # yield_curve.parquet, pmi.parquet
│
├── configs/                # YAML configuration
│   ├── base/               # Default system configs
│   └── experiments/        # Experiment override files
│
├── models/                 # Strategy implementations
│   ├── equity_trend_v1.py  # 200D MA + momentum
│   ├── index_mean_rev_v1.py  # RSI + Bollinger Bands
│   └── crypto_momentum_v1.py  # 30-60D momentum + regime gating
│
├── engines/                # Core engines
│   ├── data/               # Data pipeline, features, validation
│   ├── portfolio/          # Multi-model aggregation, attribution
│   ├── risk/               # Risk limit enforcement
│   ├── regime/             # Market regime classification
│   ├── execution/          # Backtest/paper/live execution
│   └── optimization/       # Grid search, evolutionary algorithms
│
├── backtest/               # Backtest CLI and reporting
├── live/                   # Paper/live trading runners
├── utils/                  # Shared utilities (logging, config, metrics)
├── tests/                  # Test suite (unit, integration, contract)
├── logs/                   # JSON logs (gitignored)
└── results/                # DuckDB results database (gitignored)
```

## Configuration

All system behavior is controlled via YAML configuration files:

- **system.yaml**: Execution mode, model selection, budgets, risk limits
- **models.yaml**: Model-specific parameters (MA periods, RSI thresholds, etc.)
- **regime_budgets.yaml**: Budget adjustments per market regime

Example:

```yaml
# configs/base/system.yaml
system:
  mode: backtest
  backtest_initial_nav: 100000.00
  models:
    - name: EquityTrendModel_v1
      budget_fraction: 0.30
  risk:
    per_asset_cap: 0.40
    crypto_class_cap: 0.20
    max_leverage: 1.2
    drawdown_trigger: 0.15
```

## Documentation

- **[Quickstart Guide](specs/001-trading-platform/quickstart.md)**: Setup and first backtest
- **[Specification](specs/001-trading-platform/spec.md)**: Business requirements and user stories
- **[Implementation Plan](specs/001-trading-platform/plan.md)**: Technical architecture and roadmap
- **[Data Model](specs/001-trading-platform/data-model.md)**: Entities, relationships, validation rules
- **[Research](specs/001-trading-platform/research.md)**: Technology decisions and patterns
- **[Tasks](specs/001-trading-platform/tasks.md)**: Implementation task breakdown
- **[Constitution](.specify/constitution.md)**: Architectural principles

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black .

# Lint
flake8 .

# Type checking
mypy .
```

## Usage

### Backtesting

```bash
# Single model backtest
python -m backtest.cli run --config configs/base/system.yaml --start 2020-01-01 --end 2024-12-31

# Multi-model portfolio
# (Edit configs/base/system.yaml to add multiple models)
python -m backtest.cli run --config configs/base/system.yaml

# Parameter optimization
python -m engines.optimization run-grid --config configs/experiments/trend_sweep.yaml
```

### Paper Trading

```bash
# Configure Alpaca paper credentials in .env
# Set EXECUTION_MODE=paper
python -m live.paper_runner --config configs/base/system.yaml
```

### Live Trading

⚠️ **WARNING**: Only proceed after thorough paper trading validation

```bash
# Configure live broker credentials in .env
# Set EXECUTION_MODE=live
# Ensure kill switch is tested
python -m live.live_runner --config configs/base/system.yaml
```

## Model Lifecycle

Models progress through stages with validation:

1. **Research**: Development and backtesting (config-based, no real capital)
2. **Candidate**: Passed backtest criteria (Sharpe ≥ 1.0, MaxDD ≤ 25%, 2+ years data)
3. **Paper**: Live market testing with simulated execution (30+ days)
4. **Live**: Active trading with real capital (manual approval required)

## Risk Controls

The platform enforces non-negotiable risk limits:

- **Per-Asset Cap**: Max 40% NAV in any single asset
- **Asset Class Cap**: Max 20% NAV in crypto
- **Gross Leverage**: Max 1.2x NAV
- **Drawdown Auto-Derisking**: 50% reduction at 15% drawdown
- **Drawdown Halt**: Full exit at 20% drawdown
- **Kill Switch**: Immediate order halt via config or command

## Performance Metrics

- **Sharpe Ratio**: Risk-adjusted returns (annualized)
- **CAGR**: Compound annual growth rate
- **Max Drawdown**: Worst peak-to-trough decline
- **Win Rate**: Fraction of profitable trades
- **BPS**: Balanced Performance Score = 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD

## Contributing

This is a private trading platform. See `specs/001-trading-platform/tasks.md` for implementation roadmap.

## License

Proprietary - All rights reserved

## Support

For issues or questions:
- Check documentation in `specs/001-trading-platform/`
- Review error logs in `logs/errors.log`
- Consult constitution at `.specify/constitution.md`

## Disclaimer

This software is for educational and research purposes. Trading involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk.
