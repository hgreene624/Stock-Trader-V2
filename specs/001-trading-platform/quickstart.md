# Quickstart Guide

**Feature**: Multi-Model Algorithmic Trading Platform
**Purpose**: Get the platform running with your first backtest in under 30 minutes
**Target Audience**: Developers setting up the platform for the first time

---

## Prerequisites

- **Python**: 3.9 or higher
- **Operating System**: macOS, Linux, or Windows with WSL
- **Disk Space**: ~500 MB for dependencies + data
- **Internet**: Required for data download and package installation
- **Knowledge**: Basic Python and command-line familiarity

---

## Step 1: Environment Setup

### 1.1 Clone Repository and Create Virtual Environment

```bash
# Navigate to project directory
cd /path/to/PythonProject

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows WSL:
source venv/bin/activate
```

### 1.2 Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install pandas==2.1.0 \
            numpy==1.25.0 \
            pyarrow==13.0.0 \
            pyyaml==6.0.1 \
            pydantic==2.4.0 \
            python-json-logger==2.0.7

# Install data sources
pip install yfinance==0.2.28  # Yahoo Finance data

# Install broker adapters (optional for backtest)
pip install alpaca-py==0.12.0 \
            ccxt==4.1.0

# Install optimization
pip install deap==1.4.1

# Install database
pip install duckdb==0.9.0

# Install testing (development only)
pip install pytest==7.4.0 \
            pytest-cov==4.1.0
```

**OR** use requirements.txt (to be created):

```bash
pip install -r requirements.txt
```

### 1.3 Verify Installation

```bash
python -c "import pandas, pyarrow, yaml, pydantic; print('All dependencies installed successfully!')"
```

---

## Step 2: Download Sample Data

### 2.1 Create Data Directory Structure

```bash
mkdir -p data/equities
mkdir -p data/crypto
mkdir -p data/macro
```

### 2.2 Download Historical Data (Manual for v1)

Create a data download script `scripts/download_data.py`:

```python
"""
Download historical H4 and daily data for backtesting.
Run once to populate data/ directory.
"""

import yfinance as yf
import pandas as pd
from pathlib import Path

def download_equity_data(symbol: str, start: str = "2020-01-01", end: str = "2025-01-15"):
    """Download H4 and daily data for equity symbol."""

    print(f"Downloading {symbol}...")

    # Download daily data
    ticker = yf.Ticker(symbol)
    daily = ticker.history(start=start, end=end, interval="1d")

    # Save daily data
    daily_path = f"data/equities/{symbol}_daily.parquet"
    daily.to_parquet(daily_path)
    print(f"  Saved {len(daily)} daily bars to {daily_path}")

    # Download 1-hour data (resample to H4)
    # Note: yfinance limits 1h data to ~730 days, download in chunks for longer history
    hourly = ticker.history(start=start, end=end, interval="1h")

    # Resample to H4 (4-hour bars at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
    h4 = hourly.resample('4H', origin='start').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()

    # Filter to H4 alignment (keep only 00, 04, 08, 12, 16, 20 hours)
    h4 = h4[h4.index.hour.isin([0, 4, 8, 12, 16, 20])]

    # Save H4 data
    h4_path = f"data/equities/{symbol}_h4.parquet"
    h4.to_parquet(h4_path)
    print(f"  Saved {len(h4)} H4 bars to {h4_path}")

def main():
    # Download equity data
    symbols = ["SPY", "QQQ"]  # Start with 2 symbols for quickstart

    for symbol in symbols:
        download_equity_data(symbol)

    print("\nData download complete!")
    print("Next step: Run your first backtest with `python backtest/run_backtest.py`")

if __name__ == "__main__":
    main()
```

Run the download script:

```bash
python scripts/download_data.py
```

**Expected output**:
```
Downloading SPY...
  Saved 1258 daily bars to data/equities/SPY_daily.parquet
  Saved 3521 H4 bars to data/equities/SPY_h4.parquet
Downloading QQQ...
  Saved 1258 daily bars to data/equities/QQQ_daily.parquet
  Saved 3521 H4 bars to data/equities/QQQ_h4.parquet

Data download complete!
```

### 2.3 Verify Data Files

```bash
ls -lh data/equities/
```

**Expected**:
```
SPY_daily.parquet
SPY_h4.parquet
QQQ_daily.parquet
QQQ_h4.parquet
```

---

## Step 3: Create Base Configuration

### 3.1 Create Configuration Directory

```bash
mkdir -p configs/base
```

### 3.2 Create `configs/base/system.yaml`

Copy the example from `specs/001-trading-platform/contracts/config_schemas.yaml` or use this minimal version:

```yaml
system:
  mode: "backtest"
  backtest_initial_nav: 100000.00
  timeframe: "H4"

  data_dir: "./data"
  results_dir: "./results"
  logs_dir: "./logs"

  models:
    - name: "EquityTrendModel_v1"
      version: "1.0.0"
      status: "research"
      budget_fraction: 1.0  # 100% for single-model test

  risk:
    max_leverage: 1.2
    per_asset_cap: 0.50  # Allow 50% per asset for 2-asset universe
    crypto_class_cap: 0.20
    drawdown_trigger: 0.15
    drawdown_halt: 0.20
    derisking_factor: 0.50

  logging:
    level: "INFO"
    format: "json"
    files:
      trades: "./logs/trades.log"
      performance: "./logs/performance.log"
      regime: "./logs/regime.log"
      errors: "./logs/errors.log"
```

### 3.3 Create `configs/base/models.yaml`

```yaml
models:
  EquityTrendModel_v1:
    version: "1.0.0"
    description: "Equity trend following using 200D MA and momentum"

    universe:
      - "SPY"
      - "QQQ"

    asset_classes:
      - "equity"

    parameters:
      slow_ma_period: 200
      momentum_lookback_days: 60
      exit_ma_period: 50
      equal_weight: true
      max_positions: 2

    execution:
      urgency: "normal"
      horizon: "position"
```

---

## Step 4: Run Your First Backtest

### 4.1 Create Backtest Runner Script

Create `backtest/run_backtest.py`:

```python
"""
Simple backtest runner for quickstart.
Runs EquityTrendModel_v1 on SPY + QQQ from 2020-2025.
"""

import yaml
import pandas as pd
from pathlib import Path

# NOTE: Actual implementation requires completed engines and models
# This is a placeholder to show the expected flow

def load_config(config_path: str) -> dict:
    """Load YAML configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)

def run_backtest(system_config: dict, models_config: dict):
    """Run backtest with given configuration."""

    print("=" * 60)
    print("BACKTEST STARTING")
    print("=" * 60)

    # TODO: Implement backtest engine
    # 1. Load data from data_dir
    # 2. Initialize models from models_config
    # 3. Initialize Portfolio, Risk, Regime engines
    # 4. Loop through H4 bars:
    #    - Construct Context
    #    - Generate model outputs
    #    - Aggregate to target weights
    #    - Apply risk constraints
    #    - Execute trades
    #    - Update portfolio state
    # 5. Calculate performance metrics
    # 6. Save results to database

    print("\nConfiguration:")
    print(f"  Mode: {system_config['system']['mode']}")
    print(f"  Initial NAV: ${system_config['system']['backtest_initial_nav']:,.2f}")
    print(f"  Models: {[m['name'] for m in system_config['system']['models']]}")

    print("\nBacktest period: 2020-01-01 to 2025-01-15")
    print("Universe: SPY, QQQ")
    print("Timeframe: H4")

    print("\n[Backtest execution not yet implemented - requires Phase 2 completion]")
    print("\nExpected output (once implemented):")
    print("  - Equity curve plot")
    print("  - Performance metrics (Sharpe, CAGR, max drawdown)")
    print("  - Trade log (JSON)")
    print("  - Results stored in DuckDB")

    print("\n" + "=" * 60)
    print("BACKTEST COMPLETE")
    print("=" * 60)

def main():
    # Load configurations
    system_config = load_config("configs/base/system.yaml")
    models_config = load_config("configs/base/models.yaml")

    # Run backtest
    run_backtest(system_config, models_config)

if __name__ == "__main__":
    main()
```

### 4.2 Run the Backtest

```bash
# Create logs and results directories
mkdir -p logs results

# Run backtest
python backtest/run_backtest.py
```

**Expected output** (once implementation complete):

```
============================================================
BACKTEST STARTING
============================================================

Configuration:
  Mode: backtest
  Initial NAV: $100,000.00
  Models: ['EquityTrendModel_v1']

Backtest period: 2020-01-01 to 2025-01-15
Universe: SPY, QQQ
Timeframe: H4

Processing bars: 100%|████████████████| 3521/3521 [00:12<00:00, 289.25 bars/s]

============================================================
BACKTEST COMPLETE
============================================================

Performance Summary:
  Total Return: +42.5%
  CAGR: 7.8%
  Sharpe Ratio: 1.23
  Max Drawdown: -18.2%
  Win Rate: 58.3%
  Num Trades: 24
  Balanced Performance Score (BPS): 0.89

Results saved to:
  - results/backtest_20250116_123045.db (DuckDB)
  - logs/trades.log (JSON lines)
  - logs/performance.log (JSON lines)
```

---

## Step 5: Interpret Results

### 5.1 View Trade Log

```bash
# View first 5 trades (JSON format)
head -5 logs/trades.log | jq .
```

**Example output**:
```json
{
  "timestamp": "2020-03-15T16:00:00Z",
  "symbol": "SPY",
  "side": "buy",
  "quantity": 300,
  "price": 258.45,
  "fees": 0.78,
  "slippage": 0.13,
  "nav_at_trade": 100000.00,
  "mode": "backtest",
  "source_models": ["EquityTrendModel_v1"]
}
```

### 5.2 Query Results Database

```bash
# Launch DuckDB CLI
duckdb results/backtest_20250116_123045.db

# View backtest summary
SELECT * FROM backtests;

# View all trades
SELECT timestamp, symbol, side, quantity, price FROM trades ORDER BY timestamp;

# Exit
.quit
```

### 5.3 Analyze Performance (Manual for v1)

Create `scripts/analyze_results.py`:

```python
import duckdb
import pandas as pd

# Connect to results database
con = duckdb.connect('results/backtest_20250116_123045.db')

# Load trades
trades = con.execute("SELECT * FROM trades").df()

# Calculate equity curve
trades['cumulative_pnl'] = trades['unrealized_pnl'].cumsum()
trades['nav'] = 100000 + trades['cumulative_pnl']

# Plot equity curve (requires matplotlib)
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 6))
plt.plot(trades['timestamp'], trades['nav'])
plt.title('Equity Curve - EquityTrendModel_v1')
plt.xlabel('Date')
plt.ylabel('NAV ($)')
plt.grid(True)
plt.savefig('equity_curve.png')
print("Equity curve saved to equity_curve.png")
```

---

## Next Steps

### 1. **Explore Multi-Model Portfolios**

Edit `configs/base/system.yaml` to add more models:

```yaml
models:
  - name: "EquityTrendModel_v1"
    budget_fraction: 0.40

  - name: "IndexMeanReversionModel_v1"
    budget_fraction: 0.30
```

### 2. **Run Parameter Optimization**

Create experiment config in `configs/experiments/` and run grid search:

```bash
python optimization/run_grid_search.py --config configs/experiments/exp_001.yaml
```

### 3. **Add Regime Engine**

Implement regime classification and configure budget adjustments in `configs/base/regime_budgets.yaml`.

### 4. **Progress to Paper Trading**

Once backtest results are satisfactory:

1. Set up Alpaca paper trading account
2. Update `configs/base/system.yaml` with broker credentials
3. Change mode to `paper`
4. Run `python live/run_paper_trading.py`

### 5. **Deploy to Cloud**

For continuous operation:

1. Set up Linux server (AWS EC2, Digital Ocean, etc.)
2. Install dependencies and codebase
3. Configure cron job for H4 execution
4. Set up monitoring and alerting

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pandas'"

**Solution**: Ensure virtual environment is activated and dependencies installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "FileNotFoundError: data/equities/SPY_h4.parquet"

**Solution**: Run data download script:
```bash
python scripts/download_data.py
```

### Issue: "ValueError: timestamp must be H4-aligned"

**Solution**: Check that data timestamps are at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC. Resample using:
```python
df = df[df.index.hour.isin([0, 4, 8, 12, 16, 20])]
```

### Issue: Backtest is very slow

**Solution**:
- Reduce backtest period (e.g., 2023-2024 instead of 2020-2025)
- Use fewer assets in universe
- Optimize feature computation (vectorize with pandas/numpy)

---

## Resources

- **Constitution**: `.specify/constitution.md` - Architectural principles
- **Specification**: `specs/001-trading-platform/spec.md` - Business requirements
- **Plan**: `specs/001-trading-platform/plan.md` - Implementation roadmap
- **Research**: `specs/001-trading-platform/research.md` - Technology decisions
- **Contracts**: `specs/001-trading-platform/contracts/` - Python interfaces

---

## Getting Help

If you encounter issues:

1. Check `logs/errors.log` for error messages
2. Verify configuration files against schemas in `contracts/config_schemas.yaml`
3. Review constitution for architectural constraints
4. Consult plan.md for implementation phases and dependencies

**Happy backtesting! 🚀**
