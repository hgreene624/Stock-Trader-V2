# Quickstart Guide: Finding High-Performance Trading Models

**Goal**: Learn how to explore different model parameters, run optimization experiments, and find models that perform well on historical data.

**Time**: 30-45 minutes from setup to first optimized model

---

## Prerequisites

- **Python**: 3.9 or higher
- **Operating System**: macOS, Linux, or Windows with WSL
- **Disk Space**: ~500 MB for dependencies + data
- **Internet**: Required for data download
- **Knowledge**: Basic Python and command-line familiarity

---

## Part 1: Initial Setup (10 minutes)

### Step 1.1: Environment Setup

```bash
# Navigate to project directory
cd /path/to/PythonProject

# Create Python virtual environment
python3 -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows WSL:
source .venv/bin/activate
```

### Step 1.2: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install core dependencies
pip install pandas==2.1.0 \
            numpy==1.25.0 \
            pyarrow==13.0.0 \
            pyyaml==6.0.1 \
            pydantic==2.4.0 \
            python-json-logger==2.0.7 \
            yfinance==0.2.28 \
            duckdb==0.9.0 \
            deap==1.4.1 \
            pytest==7.4.0 \
            pytest-cov==4.1.0
```

### Step 1.3: Validate Installation

```bash
# Run comprehensive validation
python validate_pipeline.py

# Expected output: ✓ ALL TESTS PASSED - PLATFORM READY
```

If validation passes, you're ready to start exploring models! ✅

---

## Part 2: Download Data (5 minutes)

### Step 2.1: Download Equity Data

```bash
# Download SPY and QQQ (both daily and 4H data)
python -m engines.data.cli download \
    --symbols SPY QQQ \
    --asset-class equity \
    --timeframes 1D 4H \
    --start 2020-01-01 \
    --validate
```

**Expected output**:
```
================================================================================
DATA DOWNLOAD
================================================================================
Asset Class: equity
Symbols: SPY, QQQ
Timeframes: 1D, 4H
Period: 2020-01-01 to today
================================================================================

Downloading SPY (1D)...
✓ SPY (1D): 1256 bars downloaded
Downloading SPY (4H)...
✓ SPY (4H): 7536 bars downloaded
Downloading QQQ (1D)...
✓ QQQ (1D): 1256 bars downloaded
Downloading QQQ (4H)...
✓ QQQ (4H): 7536 bars downloaded

================================================================================
DOWNLOAD SUMMARY
================================================================================
Successful: 4
Failed: 0
================================================================================
```

### Step 2.2: Verify Data Files

```bash
ls -lh data/equities/
```

**Expected**:
```
SPY_1D.parquet    (147 KB)
SPY_4H.parquet    (882 KB)
QQQ_1D.parquet    (147 KB)
QQQ_4H.parquet    (882 KB)
```

---

## Part 3: Run Your First Backtest (5 minutes)

### Step 3.1: Run Baseline Backtest

Use the default EquityTrendModel_v1 configuration:

```bash
# Run backtest with default parameters
python -m backtest.cli run \
    --config configs/base/system.yaml \
    --start 2020-01-01 \
    --end 2024-12-31
```

**Expected output**:
```
================================================================================
BACKTEST STARTING
================================================================================
Config: configs/base/system.yaml
Period: 2020-01-01 to 2024-12-31
Initial NAV: $100,000.00
Models: EquityTrendModel_v1

Processing bars: 100%|████████████| 7536/7536 [00:18<00:00, 418.67 bars/s]

================================================================================
BACKTEST COMPLETE
================================================================================

Performance Summary:
  Total Return:        +67.8%
  CAGR:                11.2%
  Sharpe Ratio:        1.15
  Max Drawdown:        -21.3%
  Win Rate:            61.2%
  Num Trades:          28
  BPS (Balanced):      0.82

Results saved to:
  - results/backtest_20241116_143025.db
  - logs/trades.log
  - logs/performance.log
```

**Notes:**
- **BPS (Balanced Performance Score)** = 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD
- Higher BPS = Better overall performance
- Default parameters are a starting point - optimization can significantly improve results!

---

## Part 4: Explore Models with Parameter Optimization (15 minutes)

Now let's find better-performing parameters using automated optimization.

### Understanding the 3 Available Models

The platform includes 3 trading models:

1. **EquityTrendModel_v1**: 200-day MA + momentum (SPY, QQQ)
   - Best for trending equity markets
   - Key parameters: `slow_ma_period`, `momentum_lookback_days`, `exit_ma_period`

2. **IndexMeanReversionModel_v1**: RSI + Bollinger Bands (SPY, QQQ, 4H bars)
   - Best for ranging markets
   - Key parameters: `rsi_period`, `rsi_oversold`, `rsi_overbought`, `bb_period`

3. **CryptoMomentumModel_v1**: 30-60 day momentum (BTC, ETH)
   - Best for crypto bull markets
   - Key parameters: `short_lookback`, `long_lookback`, `rebalance_days`

### Step 4.1: Run Grid Search Optimization

Let's optimize the EquityTrendModel_v1 to find the best MA periods and momentum lookback:

```bash
# Run grid search experiment (36 parameter combinations)
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_001_equity_trend_grid.yaml
```

**What this does**:
- Tests 3 values for `slow_ma_period`: 150, 200, 250
- Tests 4 values for `momentum_lookback_days`: 30, 60, 90, 120
- Tests 3 values for `exit_ma_period`: 30, 50, 70
- **Total**: 3 × 4 × 3 = 36 backtests
- **Time**: ~5-10 minutes depending on your machine

**Expected output**:
```
================================================================================
OPTIMIZATION EXPERIMENT: equity_trend_ma_optimization
================================================================================
Method: Grid Search
Target Model: EquityTrendModel_v1
Parameter Combinations: 36
Period: 2020-01-01 to 2024-12-31
================================================================================

Running backtest 1/36: slow_ma=150, momentum=30, exit_ma=30
  ✓ BPS: 0.68 | Sharpe: 0.95 | CAGR: 8.2% | MaxDD: -24.1%

Running backtest 2/36: slow_ma=150, momentum=30, exit_ma=50
  ✓ BPS: 0.73 | Sharpe: 1.02 | CAGR: 9.1% | MaxDD: -22.5%

...

Running backtest 36/36: slow_ma=250, momentum=120, exit_ma=70
  ✓ BPS: 0.91 | Sharpe: 1.38 | CAGR: 12.8% | MaxDD: -18.2%

================================================================================
OPTIMIZATION COMPLETE
================================================================================

Top 10 Parameter Sets (by BPS):
  1. BPS: 0.91 | slow_ma=250, momentum=120, exit_ma=70
  2. BPS: 0.89 | slow_ma=250, momentum=90, exit_ma=70
  3. BPS: 0.87 | slow_ma=200, momentum=120, exit_ma=50
  4. BPS: 0.85 | slow_ma=250, momentum=120, exit_ma=50
  5. BPS: 0.84 | slow_ma=200, momentum=90, exit_ma=70
  ...

Results saved to:
  - results/exp_001_equity_trend_grid.db
  - results/exp_001_summary.csv
  - logs/optimization.log
```

**🎯 Key Finding**: Best parameters achieved **BPS = 0.91** vs baseline **BPS = 0.82** (+11% improvement!)

### Step 4.2: View Detailed Results

```bash
# View top 10 results in CSV
head -11 results/exp_001_summary.csv | column -t -s,

# Query results database
duckdb results/exp_001_equity_trend_grid.db

# Inside DuckDB:
SELECT
  parameter_set_id,
  slow_ma_period,
  momentum_lookback_days,
  exit_ma_period,
  bps,
  sharpe_ratio,
  cagr,
  max_drawdown
FROM experiment_results
ORDER BY bps DESC
LIMIT 10;
```

### Step 4.3: Compare Optimization Methods

**Grid Search** (exhaustive):
- Tests ALL combinations
- Use when: Small parameter space (< 100 combinations)
- Pro: Guaranteed to find global optimum
- Con: Slow for large parameter spaces

**Random Search** (sampling):
```bash
# Example: Test 50 random combinations
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_002_mean_reversion_random.yaml
```
- Tests random samples from parameter distributions
- Use when: Large parameter space (100+ combinations)
- Pro: Fast, good coverage
- Con: May miss optimal combination

**Evolutionary Algorithm** (genetic):
```bash
# Example: Evolve population over 20 generations
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_003_crypto_momentum_ea.yaml
```
- Evolves population toward better parameters
- Use when: Complex parameter interactions
- Pro: Finds good solutions efficiently
- Con: Can get stuck in local optima

---

## Part 5: Creating Custom Optimization Experiments (5 minutes)

### Step 5.1: Create Your Own Experiment

Create `configs/experiments/my_first_experiment.yaml`:

```yaml
# My First Optimization Experiment
experiment:
  name: "my_trend_model_test"
  description: "Testing different MA periods"
  method: "grid"
  base_config: "configs/base/system.yaml"
  target_model: "EquityTrendModel_v1"

  # Override system settings
  overrides:
    system:
      mode: "backtest"
      backtest_initial_nav: 100000.00
      models:
        - name: "EquityTrendModel_v1"
          version: "1.0.0"
          status: "research"
          budget_fraction: 1.0

  # Define parameter grid
  parameter_grid:
    models.EquityTrendModel_v1.parameters.slow_ma_period:
      - 100
      - 150
      - 200
      - 250

    models.EquityTrendModel_v1.parameters.momentum_lookback_days:
      - 60
      - 90
      - 120

  # Backtest period
  backtest:
    start_date: "2020-01-01"
    end_date: "2024-12-31"

  # Optimization settings
  optimization:
    metric: "bps"
    maximize: true
    save_top_n: 5

  # Results storage
  results:
    database: "results/my_first_experiment.db"
    summary_csv: "results/my_experiment_summary.csv"
```

### Step 5.2: Run Your Experiment

```bash
python -m engines.optimization.cli run \
    --experiment configs/experiments/my_first_experiment.yaml
```

### Step 5.3: Tips for Effective Optimization

**Parameter Selection**:
- Start with wide ranges to explore broadly
- Then narrow down based on initial results
- Don't over-optimize (overfitting risk)

**Validation Best Practices**:
1. **In-Sample Period**: Train on 2020-2022
2. **Out-of-Sample Period**: Validate on 2023-2024
3. **Walk-Forward**: Test on multiple time periods

**Avoiding Overfitting**:
- Use 3+ years of data minimum
- Test on out-of-sample period
- Verify strategy makes economic sense
- Don't optimize more than 3-4 parameters

---

## Part 6: Model Lifecycle Management (5 minutes)

Once you find well-performing parameters, promote models through lifecycle stages.

### Lifecycle Stages

```
research → candidate → paper → live
```

1. **research**: Development and backtesting (current stage)
2. **candidate**: Passed backtest criteria (Sharpe ≥ 1.0, MaxDD ≤ 25%)
3. **paper**: Live paper trading for 30+ days
4. **live**: Production trading with real capital

### Step 6.1: View Model Lifecycle Status

```bash
# List all models and their stages
python -m backtest.cli list-models
```

**Output**:
```
================================================================================
MODEL LIFECYCLE STATUS
================================================================================

Model: EquityTrendModel_v1
  Lifecycle Stage: research
  Version: 1.0.0

Model: IndexMeanReversionModel_v1
  Lifecycle Stage: research
  Version: 1.0.0

Model: CryptoMomentumModel_v1
  Lifecycle Stage: research
  Version: 1.0.0
================================================================================
```

### Step 6.2: Promote a Model

After verifying good backtest performance:

```bash
# Promote to candidate stage
python -m backtest.cli promote \
    --model EquityTrendModel_v1 \
    --reason "Optimized parameters: BPS=0.91, Sharpe=1.38, validated on 2020-2024" \
    --operator your_name
```

**Output**:
```
======================================================================
MODEL LIFECYCLE PROMOTION
======================================================================

Model:       EquityTrendModel_v1
From Stage:  research
To Stage:    candidate
Reason:      Optimized parameters: BPS=0.91, Sharpe=1.38, validated on 2020-2024
Operator:    your_name
Timestamp:   2024-11-16T14:35:22Z

⚠  WARNING: Manual validation required. Ensure model meets:
   {'min_sharpe': 1.0, 'min_cagr': 0.1, 'max_drawdown': -0.2, 'min_trades': 10}

✓ Promotion successful
  Event logged to: logs/model_lifecycle_events.jsonl
  State updated in: configs/.model_lifecycle.json
======================================================================
```

### Step 6.3: Track Lifecycle History

```bash
# View all lifecycle events
cat logs/model_lifecycle_events.jsonl | jq .
```

**Output**:
```json
{
  "timestamp": "2024-11-16T14:35:22Z",
  "model_name": "EquityTrendModel_v1",
  "from_stage": "research",
  "to_stage": "candidate",
  "reason": "Optimized parameters: BPS=0.91, Sharpe=1.38",
  "operator": "your_name"
}
```

---

## Part 7: Multi-Model Portfolios (Advanced)

Once you have multiple optimized models, combine them in a portfolio.

### Step 7.1: Update System Config

Edit `configs/base/system.yaml`:

```yaml
system:
  mode: "backtest"
  backtest_initial_nav: 100000.00
  timeframe: "H4"

  # Add multiple models with budget allocations
  models:
    - name: "EquityTrendModel_v1"
      version: "1.0.0"
      status: "candidate"  # Promoted to candidate
      budget_fraction: 0.40  # 40% of NAV

    - name: "IndexMeanReversionModel_v1"
      version: "1.0.0"
      status: "research"
      budget_fraction: 0.30  # 30% of NAV

    - name: "CryptoMomentumModel_v1"
      version: "1.0.0"
      status: "research"
      budget_fraction: 0.15  # 15% of NAV

  # Total: 85% allocated, 15% cash buffer
```

### Step 7.2: Run Multi-Model Backtest

```bash
python -m backtest.cli run \
    --config configs/base/system.yaml \
    --start 2020-01-01 \
    --end 2024-12-31
```

**Expected Benefits**:
- **Diversification**: Lower drawdowns
- **Smoother Equity Curve**: Different strategies perform in different regimes
- **Better Risk-Adjusted Returns**: Higher Sharpe ratio

---

## Part 8: Configuration Reference

### Creating Config Files

#### Minimal System Config

Create `configs/base/my_system.yaml`:

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
      budget_fraction: 1.0

  risk:
    max_leverage: 1.2
    per_asset_cap: 0.40
    crypto_class_cap: 0.20
    drawdown_trigger: 0.15
    drawdown_halt: 0.20
    derisking_factor: 0.50
```

#### Model Parameters Config

The platform reads model parameters from `configs/base/models.yaml`:

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
      slow_ma_period: 200        # Long-term trend filter
      momentum_lookback_days: 60  # Momentum calculation period
      exit_ma_period: 50          # Exit signal MA
      equal_weight: true          # Equal weight or momentum-weighted
      max_positions: 2            # Max concurrent positions

    execution:
      urgency: "normal"           # low | normal | high
      horizon: "position"         # intraday | swing | position
```

**To use optimized parameters**: Update the `parameters` section with your best values from optimization experiments.

---

## Next Steps

### 1. **Optimize Other Models**

Run optimization on IndexMeanReversionModel_v1:

```bash
python -m engines.optimization.cli run \
    --experiment configs/experiments/exp_002_mean_reversion_random.yaml
```

### 2. **Download Crypto Data** (Optional)

```bash
python -m engines.data.cli download \
    --symbols BTC/USD ETH/USD \
    --asset-class crypto \
    --timeframes 1D 4H \
    --start 2020-01-01 \
    --exchange binance
```

Then run CryptoMomentumModel_v1 optimization.

### 3. **Walk-Forward Testing**

Test on multiple periods to validate robustness:

```yaml
# configs/experiments/walk_forward.yaml
backtest:
  periods:
    - start: "2020-01-01"
      end: "2021-12-31"
    - start: "2022-01-01"
      end: "2023-12-31"
    - start: "2024-01-01"
      end: "2024-12-31"
```

### 4. **Paper Trading**

Once models are validated:

1. Get Alpaca paper trading API keys
2. Update `configs/base/system.yaml` with credentials
3. Promote model to paper stage
4. Run paper trading:

```bash
python -m live.paper_runner --config configs/base/system.yaml
```

### 5. **Live Trading** (Use with Extreme Caution)

Only after 30+ days of successful paper trading:

```bash
# Requires --confirm flag for safety
python -m live.live_runner \
    --config configs/base/system.yaml \
    --confirm
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError"

**Solution**: Activate virtual environment and install dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt  # (create if needed)
```

### Issue: "FileNotFoundError: data/equities/SPY_4H.parquet"

**Solution**: Download data first:
```bash
python -m engines.data.cli download --symbols SPY QQQ --start 2020-01-01
```

### Issue: Optimization is very slow

**Solutions**:
- Reduce parameter grid size (fewer values per parameter)
- Shorten backtest period (e.g., 2022-2024 instead of 2020-2024)
- Use random search instead of grid search
- Run in parallel (modify experiment config to enable multiprocessing)

### Issue: "ValueError: timestamp must be H4-aligned"

**Solution**: Data timestamps must be at H4 boundaries (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC). Re-download data using the CLI.

### Issue: All backtests have similar performance

**Solutions**:
- Widen parameter ranges
- Test on different market regimes (bull, bear, sideways)
- Verify model logic is actually using the parameters
- Check for bugs in model implementation

---

## Performance Metrics Explained

- **BPS (Balanced Performance Score)**: Composite metric = 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD
  - **Good**: BPS > 0.80
  - **Excellent**: BPS > 1.00

- **Sharpe Ratio**: Risk-adjusted returns (annualized)
  - **Good**: Sharpe > 1.0
  - **Excellent**: Sharpe > 1.5

- **CAGR**: Compound annual growth rate
  - **Good**: CAGR > 10%
  - **Excellent**: CAGR > 15%

- **Max Drawdown**: Worst peak-to-trough decline
  - **Good**: MaxDD < -20%
  - **Excellent**: MaxDD < -15%

---

## Resources

- **Documentation**: `specs/001-trading-platform/`
- **Constitution**: `.specify/constitution.md`
- **Tasks**: `specs/001-trading-platform/tasks.md`
- **Test Results**: `tests/` (run `pytest` to verify)

---

## Getting Help

1. Check `logs/errors.log` for error messages
2. Run validation: `python validate_pipeline.py`
3. Review config schemas in `specs/001-trading-platform/contracts/`
4. Consult implementation plan: `specs/001-trading-platform/plan.md`

**Happy model hunting! 🚀📈**
