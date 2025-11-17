# Quick Start Guide - Trading Platform MVP

**You now have a fully functional backtesting platform!** 🎉

This guide will get you running your first backtest in 5 minutes.

---

## Prerequisites Check

Ensure you have the dependencies installed:

```bash
pip install -r requirements.txt
```

---

## Step 1: Download Historical Data

Download SPY and QQQ data (equities):

```bash
# Download daily data (for features like 200D MA)
python -m engines.data.downloader download-equity \
  --symbols SPY QQQ \
  --start 2020-01-01 \
  --end 2025-01-01 \
  --timeframe 1D

# Download 4-hour data (primary decision frequency)
python -m engines.data.downloader download-equity \
  --symbols SPY QQQ \
  --start 2020-01-01 \
  --end 2025-01-01 \
  --timeframe 4H
```

**Expected output**:
```
✓ Downloaded SPY (1D)
✓ Downloaded QQQ (1D)
✓ Downloaded SPY (4H)
✓ Downloaded QQQ (4H)
```

**Data will be saved to**: `data/equities/SPY_1D.parquet`, etc.

---

## Step 2: Review Configuration

The default config is at `configs/base/system.yaml`:

```yaml
backtest:
  initial_nav: 100000.0     # Starting capital
  start_date: "2023-01-01"  # Backtest period
  end_date: "2024-12-31"
  fill_timing: "close"      # Fill at bar close
  slippage_bps: 5.0         # 5 basis points slippage
  commission_pct: 0.001     # 0.1% commission

models:
  EquityTrendModel_v1:
    budget: 0.30            # 30% of NAV allocated to this model
    ma_period: 200          # 200-day moving average
    momentum_period: 120    # 6-month momentum
```

You can modify this or create your own config file.

---

## Step 3: Run Your First Backtest

```bash
python -m backtest.cli run \
  --config configs/base/system.yaml \
  --start 2023-01-01 \
  --end 2024-12-31 \
  --output results/my_first_backtest
```

**Expected output**:
```
======================================================================
BACKTEST RESULTS
======================================================================

Model: EquityTrendModel_v1
Period: 2023-01-01 to 2024-12-31

----------------------------------------------------------------------
PERFORMANCE METRICS
----------------------------------------------------------------------

Returns:
  Total Return:          XX.XX%
  CAGR:                  XX.XX%

Risk Metrics:
  Max Drawdown:          XX.XX%
  Sharpe Ratio:           X.XX

Trading Metrics:
  Total Trades:              XX
  Win Rate:              XX.XX%

Balanced Performance Score (BPS):
  BPS:                    X.XXXX

NAV:
  Initial NAV:      $100,000.00
  Final NAV:        $XXX,XXX.XX

----------------------------------------------------------------------
TRADE LOG SUMMARY
----------------------------------------------------------------------
[Trade details...]

✓ Backtest complete
```

---

## Step 4: View Results

Results are saved to `results/my_first_backtest/`:

```
results/my_first_backtest/
├── equity_curve.png         # NAV over time
├── drawdown.png             # Drawdown chart
├── monthly_returns.png      # Monthly returns heatmap
├── trade_distribution.png   # Trades by symbol
├── nav_series.csv           # Raw NAV data
├── trade_log.csv            # All trades
└── metrics.json             # Performance metrics
```

Open the PNG files to visualize your backtest:
- `equity_curve.png` - Shows portfolio value over time
- `drawdown.png` - Shows maximum drawdown periods
- `monthly_returns.png` - Heatmap of monthly performance

---

## Step 5: Run Tests (Optional)

Validate the platform is working correctly:

```bash
# Test no look-ahead bias enforcement (6 tests)
python -m tests.test_no_lookahead

# Test complete workflow (2 integration tests)
python -m tests.test_integration
```

**Expected output**:
```
======================================================================
NO LOOK-AHEAD VALIDATION TESTS
======================================================================

✓ TimeAligner correctly validates no look-ahead
✓ Context correctly rejects future asset features
✓ Lookback window correctly enforces no look-ahead
✓ enforce_no_lookahead correctly filters data
✓ Daily to H4 alignment handles boundary cases correctly
✓ DataPipeline.create_context enforces no look-ahead

======================================================================
RESULTS: 6 passed, 0 failed
======================================================================
```

---

## What Just Happened?

Your backtest just:

1. ✅ Loaded SPY and QQQ historical data (H4 + Daily)
2. ✅ Computed technical features (200D MA, 6M momentum, RSI, etc.)
3. ✅ Aligned multi-timeframe data with **no look-ahead bias**
4. ✅ Simulated EquityTrendModel_v1 trading decisions bar-by-bar
5. ✅ Executed trades with realistic slippage and commissions
6. ✅ Tracked positions and calculated NAV
7. ✅ Computed performance metrics (Sharpe, CAGR, MaxDD, BPS)
8. ✅ Generated charts and saved results to disk

---

## Understanding EquityTrendModel_v1

The model uses a simple trend-following strategy:

**Signal Logic**:
- **LONG**: If price > 200-day MA AND 6-month momentum > 0
- **FLAT**: Otherwise

**Position Sizing**:
- Equal weight across LONG signals
- 30% of total NAV allocated to this model (configurable)
- Assets: SPY, QQQ

**Example**:
- If SPY is LONG and QQQ is FLAT → 100% of model budget goes to SPY
- If both are LONG → 50% to SPY, 50% to QQQ
- If both are FLAT → 0% exposure (cash)

---

## Customizing Your Backtest

### Change Date Range
```bash
python -m backtest.cli run \
  --config configs/base/system.yaml \
  --start 2020-01-01 \
  --end 2023-12-31
```

### Modify Model Parameters

Edit `configs/base/system.yaml`:

```yaml
models:
  EquityTrendModel_v1:
    budget: 0.50              # Increase to 50% allocation
    ma_period: 100            # Use 100D MA instead of 200D
    momentum_period: 60       # Use 3M momentum instead of 6M
```

### Change Slippage/Commissions

Edit `configs/base/system.yaml`:

```yaml
backtest:
  slippage_bps: 10.0          # 10 bps slippage (more conservative)
  commission_pct: 0.0005      # 0.05% commission (interactive brokers rate)
```

---

## Analyzing Results

### Key Metrics to Watch

**Returns**:
- **Total Return**: Overall % gain/loss
- **CAGR**: Annualized return (accounts for compounding)

**Risk**:
- **Sharpe Ratio**: Risk-adjusted return (>1.0 is good, >2.0 is excellent)
- **Max Drawdown**: Largest peak-to-trough decline (lower is better)

**Trading**:
- **Total Trades**: Number of round trips
- **Win Rate**: % of profitable trades

**Overall**:
- **BPS (Balanced Performance Score)**: Composite score
  - Formula: 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD
  - Higher is better

### Interpreting the Equity Curve

- **Smooth upward slope**: Consistent returns
- **Volatility**: Choppy curve indicates higher risk
- **Flat periods**: Model is in cash (no signals)
- **Sharp drops**: Drawdown events (losses)

### Trade Log Analysis

Open `trade_log.csv` to see:
- When trades were executed
- Buy/sell decisions
- Prices paid/received
- Commissions incurred

---

## Next Steps

### 1. Experiment with Parameters
Try different MA periods, momentum lookbacks, and budget allocations to see how they affect performance.

### 2. Add More Data
Download longer history or additional assets:
```bash
python -m engines.data.downloader download-equity \
  --symbols DIA IWM VTI \
  --start 2015-01-01 \
  --timeframe 1D
```

### 3. Compare Time Periods
Run the same model on different market conditions:
- Bull market: 2020-2021
- Bear market: 2022
- Sideways: 2015-2016

### 4. Read the Code
Explore the implementation:
- `models/equity_trend_v1.py` - Strategy logic
- `backtest/runner.py` - Orchestration
- `engines/data/alignment.py` - No look-ahead enforcement

### 5. Wait for Phase 4
Next phase adds:
- Second model (IndexMeanReversionModel_v1)
- Regime classification
- Multi-model coordination
- Model comparison tools

---

## Troubleshooting

### "No data files found"
Make sure you ran the download commands in Step 1.

### "Insufficient data for backtest period"
The start_date might be before your downloaded data begins. Check `data/equities/` to see date ranges.

### "Module not found"
Install dependencies: `pip install -r requirements.txt`

### Tests failing
This shouldn't happen! Check:
1. Python version (3.9+)
2. All dependencies installed
3. No modifications to core files

---

## Resources

- **Full Documentation**: `specs/001-trading-platform/spec.md`
- **Architecture**: `specs/001-trading-platform/plan.md`
- **Phase 3 Summary**: `specs/001-trading-platform/PHASE3_COMPLETE.md`
- **Task List**: `specs/001-trading-platform/tasks.md`

---

## Questions?

The codebase is extensively documented. Every module has:
- Module docstring explaining purpose
- Function/class docstrings with examples
- Type hints for all parameters
- Example usage in `if __name__ == "__main__":` blocks

**Happy backtesting!** 🚀
