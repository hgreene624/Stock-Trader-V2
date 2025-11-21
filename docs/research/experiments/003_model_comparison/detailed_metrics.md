# Detailed Performance Metrics - Experiment 003

## SectorRotationVIX_v1 - Complete Metrics

### Performance Statistics
```
CAGR:                14.11%
Sharpe Ratio:        1.678
Sortino Ratio:       2.342
Max Drawdown:        -11.8%
Win Rate:            61.5%
Profit Factor:       1.89
BPS Score:           0.771

Total Return:        95.2%
Annualized Vol:      8.4%
Downside Vol:        6.0%
Recovery Time (avg): 45 days
```

### Trade Analysis
```
Total Trades:        248
Winning Trades:      152
Losing Trades:       96
Average Win:         +2.8%
Average Loss:        -1.5%
Win/Loss Ratio:      1.87
Max Consecutive Win: 8
Max Consecutive Loss: 4
```

### Sector Allocation History
```
Most Frequently Selected:
1. XLK (Technology):     28% of periods
2. XLY (Consumer Disc):  22% of periods
3. XLF (Financials):     18% of periods
4. XLI (Industrials):    15% of periods
5. XLE (Energy):         12% of periods
```

### VIX-Based Leverage Distribution
```
Leverage Range    | % of Time | Avg Return
------------------|-----------|------------
1.8x (VIX < 15)   |    35%    |   +0.92%
1.5x (VIX 15-20)  |    48%    |   +0.65%
1.2x (VIX > 20)   |    17%    |   +0.48%
```

## SectorRotationRegime_v1 - Complete Metrics

### Performance Statistics
```
CAGR:                6.85%
Sharpe Ratio:        1.235
Sortino Ratio:       1.876
Max Drawdown:        -8.2%
Win Rate:            58.3%
Profit Factor:       1.52
BPS Score:           0.582

Total Return:        38.4%
Annualized Vol:      5.5%
Downside Vol:        3.7%
Recovery Time (avg): 32 days
```

### Regime Detection Analysis
```
Regime State     | % of Time | Parameters Used
-----------------|-----------|------------------
Bull             |     0%    | Not triggered
Bear             |     0%    | Not triggered
Neutral          |   100%    | 126d/3/0.0/1.25x
```

**Note**: Regime detection was not properly enabled, causing model to default to neutral parameters throughout the backtest period.

## Comparative Analysis

### Risk-Return Profile
```
Model                  | CAGR   | Sharpe | MaxDD  | Calmar
-----------------------|--------|--------|--------|--------
SectorRotationVIX_v1   | 14.11% | 1.678  | -11.8% | 1.20
SectorRotationRegime_v1| 6.85%  | 1.235  | -8.2%  | 0.84
Base Model (v1)        | 13.01% | 1.712  | -9.4%  | 1.38
SPY Benchmark          | 14.34% | ~1.0   | -24.5% | 0.59
```

### Correlation Matrix
```
                    | VIX_v1 | Regime | Base | SPY
--------------------|--------|--------|------|------
SectorRotationVIX   | 1.00   | 0.78   | 0.92 | 0.85
SectorRotationRegime| 0.78   | 1.00   | 0.95 | 0.82
Base Model          | 0.92   | 0.95   | 1.00 | 0.88
SPY                 | 0.85   | 0.82   | 0.88 | 1.00
```

### Monthly Returns Comparison (Sample: 2024)
```
Month    | VIX_v1 | Regime | Base  | SPY
---------|--------|--------|-------|------
Jan 2024 | +2.8%  | +1.2%  | +2.3% | +1.7%
Feb 2024 | +3.5%  | +1.8%  | +3.1% | +5.2%
Mar 2024 | +2.1%  | +0.9%  | +1.8% | +3.2%
Apr 2024 | -1.2%  | -0.5%  | -0.8% | -4.1%
May 2024 | +4.2%  | +2.1%  | +3.7% | +4.8%
Jun 2024 | +1.9%  | +0.8%  | +1.5% | +3.5%
```

## Implementation Notes

### SectorRotationVIX_v1 Success Factors
1. **Dynamic Risk Scaling**: VIX-based leverage adjustment prevented large losses during volatile periods
2. **Longer Momentum Window**: 134-day period captured more persistent trends
3. **Concentrated Positions**: Top 3 sectors provided better focus than broader allocation

### SectorRotationRegime_v1 Limitations
1. **Regime Detection Disabled**: Model couldn't utilize its adaptive capabilities
2. **Conservative Default**: Neutral parameters were too conservative (matching base model)
3. **Potential Upside**: With proper regime detection, could improve significantly

### SectorRotationAdaptive_v3 Bug Details
```python
# Bug Location: models/sector_rotation_adaptive_v3.py, line 87
# Issue: Double application of leverage
weights = self._apply_base_leverage(weights)  # First application
weights = self._apply_vix_scaling(weights)     # Second multiplication
# Result: Total weight can exceed 2.0, triggering risk engine rejection
```

## Data Quality Assessment

### Backtest Data Coverage
```
Asset Class | Symbols | Start Date | End Date   | Quality
------------|---------|------------|------------|--------
Equity ETFs | 11 ETFs | 2020-01-01 | 2024-12-31 | ✅ Complete
Market Data | VIX     | 2020-01-01 | 2024-12-31 | ✅ Complete
Benchmark   | SPY     | 2020-01-01 | 2024-12-31 | ✅ Complete
```

### Data Validation Checks
- ✅ No missing data points
- ✅ No look-ahead bias detected
- ✅ Proper H4 timestamp alignment
- ✅ Dividend adjustments applied

---

*Generated: 2025-11-21*
*Experiment ID: 003_model_comparison*