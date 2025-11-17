# Pipeline Validation Guide

The `validate_pipeline.py` script comprehensively tests every component of the trading platform to ensure everything works correctly.

## Quick Start

```bash
# Run all validation tests
python validate_pipeline.py

# Run with detailed logging
python validate_pipeline.py --verbose
```

## What It Tests

### Phase 1: Import Dependencies
- ✓ pandas, numpy, pyarrow
- ✓ yaml, pydantic
- ✓ yfinance (equity data)
- ✓ ccxt (crypto data)
- ✓ duckdb (results database)
- ✓ matplotlib (visualization)

### Phase 2: Utilities
- ✓ **Structured Logger**: 4 separate log streams (trades, orders, performance, errors)
- ✓ **Config Loader**: YAML loading with merge semantics
- ✓ **Time Utilities**: H4 boundary detection, UTC normalization
- ✓ **Performance Metrics**: Sharpe, CAGR, MaxDD, Win Rate, BPS

### Phase 3: Data Layer
- ✓ **Data Validator**: OHLC consistency, gap detection, timestamp validation
- ✓ **Time Alignment**: Daily → H4 alignment with **no look-ahead validation**
- ✓ **Feature Computation**: MA, RSI, ATR, Bollinger Bands, momentum
- ✓ **Data Pipeline**: Multi-timeframe loading and preparation

### Phase 4: Model Layer
- ✓ **Base Context**: Context creation with timestamp validation
- ✓ **EquityTrendModel_v1**: Signal generation logic
  - Tests uptrend detection (price > MA + positive momentum)
  - Tests downtrend rejection
  - Validates weight allocation

### Phase 5: Backtest Engine
- ✓ **Backtest Executor**: Trade simulation with slippage/fees
  - Position tracking
  - NAV calculation
  - Order execution
- ✓ **Full Workflow**: End-to-end backtest
  - Data generation
  - Config loading
  - Model execution
  - Results validation

### Phase 6: Results Layer
- ✓ **DuckDB Database**: Results persistence and retrieval
  - Save backtest results
  - Retrieve NAV series
  - Retrieve trade log
  - Query metrics

## Output Format

### Normal Mode

```
======================================================================
TRADING PLATFORM PIPELINE VALIDATION
======================================================================

[12:34:56.123] → Testing: Import Dependencies
[12:34:56.234] ✓ PASSED: Import Dependencies

======================================================================
PHASE 2: Utilities Tests
======================================================================

[12:34:56.345] → Testing: Utils: Structured Logger
[12:34:56.456] ✓ PASSED: Utils: Structured Logger

...

======================================================================
VALIDATION SUMMARY
======================================================================

Total Tests: 16
Passed: 16
Failed: 0
Time: 12.34s

======================================================================
✓ ALL TESTS PASSED - PLATFORM READY
======================================================================
```

### Verbose Mode

With `--verbose`, you get detailed logging for each test:

```
[12:34:56.123] → Testing: Utils: Time Utilities
[12:34:56.124]   H4 boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
[12:34:56.234] ✓ PASSED: Utils: Time Utilities

[12:34:57.123] → Testing: Model: EquityTrendModel_v1
[12:34:57.124]   SPY signal: LONG (100.00%)
[12:34:57.125]   QQQ signal: FLAT (0.00%)
[12:34:57.234] ✓ PASSED: Model: EquityTrendModel_v1
```

If a test fails, verbose mode shows the full traceback.

## Test Details

### Critical Tests

#### 1. No Look-Ahead Validation
The most critical test ensures the system never uses future data:

```python
# Creates daily data at 21:00 UTC (market close)
# Creates H4 timestamps
# Aligns daily → H4
# Verifies: for each H4 timestamp T, daily data source ≤ T
```

**If this test fails**: DO NOT use the platform for backtesting until fixed!

#### 2. Time Alignment
Tests proper forward-filling of daily data to H4 bars:

```
Daily:  2025-01-15 21:00 (market close)
H4:     2025-01-15 20:00 → uses 2025-01-14 data (no look-ahead)
        2025-01-16 00:00 → uses 2025-01-15 data
```

#### 3. OHLC Consistency
Validates:
- High ≥ max(Open, Close)
- Low ≤ min(Open, Close)
- All prices > 0
- Volume ≥ 0

#### 4. Model Signal Logic
Tests EquityTrendModel_v1 with synthetic data:
- **Uptrend**: price > MA AND momentum > 0 → LONG signal
- **Downtrend**: price < MA OR momentum < 0 → FLAT signal

#### 5. Backtest Execution
Simulates complete backtest:
- Generates 500 days daily + 3000 bars H4 data
- Runs model for 6 months
- Validates NAV consistency
- Checks metrics are in valid ranges

## Troubleshooting

### "ImportError: Some required packages are missing"

Install missing dependencies:
```bash
pip install -r requirements.txt
```

### "FAILED: Data: Time Alignment (No Look-Ahead)"

**CRITICAL ISSUE** - This means the system is using future data in backtests!

Check:
1. `engines/data/alignment.py` - Time alignment logic
2. `models/base.py` - Context validation
3. File modifications since last known-good state

Do NOT run backtests until this is fixed!

### "FAILED: Backtest: Full Workflow"

This can fail for several reasons:

**Common causes**:
- Insufficient data (need 500+ days for 200D MA)
- Invalid config file format
- Missing model parameters

**Debug with verbose mode**:
```bash
python validate_pipeline.py --verbose
```

Look for the specific error message and traceback.

### Test Passes Locally But Backtest Fails

The validation uses synthetic data. Real data might have:
- Gaps (market holidays, data issues)
- Different date ranges
- Missing symbols

Run the actual backtest with small date range first:
```bash
python -m backtest.cli run \
  --config configs/base/system.yaml \
  --start 2024-01-01 --end 2024-01-31
```

## Performance Benchmarks

Expected runtime on typical hardware:
- **Normal mode**: 10-15 seconds
- **Verbose mode**: 12-18 seconds

If tests take significantly longer:
- Check disk I/O (temp directory)
- Check available memory
- Reduce synthetic data size (edit script)

## When to Run

### Always Run Before:
- First-time setup
- After updating dependencies
- After modifying core engine code
- Before running real backtests with capital at risk

### Optional (But Recommended):
- After git pull
- Weekly as regression test
- Before paper trading
- Before live trading

## Integration with CI/CD

The script returns exit code 0 on success, 1 on failure:

```bash
# In GitHub Actions, GitLab CI, etc.
python validate_pipeline.py || exit 1
```

## Extending the Validation

To add new tests, edit `validate_pipeline.py`:

```python
def test_my_new_component(self):
    """Test description."""
    from my_module import MyComponent
    
    # Setup
    component = MyComponent()
    
    # Test
    result = component.do_something()
    
    # Assert
    assert result == expected_value
    
    self.log_verbose("  Test details...")

# Add to run_all_tests():
self.test_step("My Component", self.test_my_new_component)
```

## Understanding Test Failures

### Pattern: "AssertionError"
A validation check failed. Read the assertion message:
```
AssertionError: Look-ahead violation: 2025-01-16 > 2025-01-15
```

### Pattern: "FileNotFoundError"
Missing file or directory. Check:
- Working directory
- File paths in config
- Temp directory permissions

### Pattern: "ValueError"
Invalid input or configuration. Check:
- Config file format
- Parameter ranges
- Data formats

### Pattern: "KeyError"
Missing required field. Check:
- DataFrame columns
- Config keys
- Model outputs

## Advanced Usage

### Run Specific Phase Only

Edit the script and comment out phases you don't want:

```python
# Phase 2: Utils
# self.test_step("Utils: Structured Logger", self.test_utils_logging)
# self.test_step("Utils: Config Loader", self.test_utils_config)
```

### Change Synthetic Data Size

Reduce data for faster tests:

```python
# In test_data_pipeline():
dates_1d = pd.date_range('2023-01-01', periods=100, freq='1D', tz='UTC')  # Was 500
dates_4h = pd.date_range('2023-01-01', periods=600, freq='4H', tz='UTC')   # Was 3000
```

### Save Test Output

```bash
python validate_pipeline.py --verbose > validation_report.txt 2>&1
```

## FAQ

**Q: Why does it create a temp directory?**  
A: To avoid polluting your data/results directories with test artifacts.

**Q: Can I run this in production?**  
A: It's designed for validation, not production monitoring. Use proper monitoring tools for production.

**Q: Does it test real broker APIs?**  
A: No, it uses simulated execution only. Broker API tests should be separate.

**Q: What if I only want to test data pipeline?**  
A: Run individual tests or comment out other phases in the script.

**Q: How do I know what changed between runs?**  
A: Compare validation reports or use git to track code changes.

---

**Remember**: If any test fails, investigate and fix before using the platform with real capital!
