# Experiment Directory Structure Standard

**IMPORTANT**: All experiments MUST follow this structure. No exceptions.

## Required Structure

```
experiment_name/
├── analysis/           # Backtest results and visualizations
│   ├── equity_curve.png
│   ├── drawdown.png
│   ├── monthly_returns_heatmap.png
│   ├── trade_analysis.png
│   ├── rolling_metrics.png
│   ├── returns_distribution.png
│   ├── summary_report.txt
│   ├── metadata.json
│   ├── nav_series.csv
│   ├── trades.csv
│   └── model_source.py
├── config/             # Configuration and parameters
│   └── metadata.json   # Copy of parameters used
├── logs/               # Execution logs
│   └── {experiment}.log
└── README.md           # Experiment documentation
```

## Model and Parameter IDs

Every experiment's `metadata.json` includes unique identifiers for consistent tracking:

```json
{
  "model": "SectorRotationConsistent_v3",
  "model_id": "SectorRotationConsistent_v3::p-ea90f831",
  "param_id": "p-ea90f831",
  "param_summary": "mom=126, top_n=4, bull_lev=1.2, bear_lev=1, min_mom=0.1",
  ...
}
```

- **model_id**: `ModelName::p-XXXXXXXX` - Full identifier combining model and parameter hash
- **param_id**: `p-XXXXXXXX` - 8-character deterministic hash of parameters (same params = same ID)
- **param_summary**: Human-readable summary of key parameters

These IDs ensure we can always identify exactly which model+parameters produced a result, even across sessions.

## README.md Template

Each experiment README MUST include:

```markdown
# {Experiment Name}

## Hypothesis
{What you're testing and why}

## Parameters
{Key parameter changes from baseline}

## Results
- **CAGR**: X.XX%
- **Sharpe**: X.XXX
- **Max Drawdown**: XX.XX%
- **Commission**: $XX,XXX

## Conclusion
{PASSED/FAILED} - {Why and key findings}

## Next Steps
{What to try next based on results}
```

## Workflow

1. **Before running**: Create experiment directory with subdirs
2. **Run backtest**: Output to `analysis/`
3. **Copy log**: From `/tmp/{profile}.log` to `logs/`
4. **Copy config**: Copy `metadata.json` to `config/`
5. **Write README**: Document hypothesis, results, conclusion

## Example Commands

```bash
# Create structure
EXP=/path/to/experiments/006_experiment/v1_test
mkdir -p "$EXP/analysis" "$EXP/config" "$EXP/logs"

# Run backtest (outputs to results/analysis/TIMESTAMP/)
python3 -m backtest.analyze_cli --profile my_profile 2>&1 | tee /tmp/my_profile.log

# Move results
mv results/analysis/TIMESTAMP/* "$EXP/analysis/"
cp /tmp/my_profile.log "$EXP/logs/"
cp "$EXP/analysis/metadata.json" "$EXP/config/"

# Write README
# Document your experiment!
```

## DO NOT

- Put results directly in `results/` subdirectory
- Skip the logs/ or config/ directories
- Forget to write the README
- Use different structures for different experiments
