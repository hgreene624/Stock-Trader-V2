# SectorRotationModel_v1

## Overview
**BEST PERFORMER** - Momentum-based sector rotation strategy that selects top-performing equity sectors. Currently achieving 13.01% CAGR, within 1.33% of SPY target.

## Strategy Details

### Entry Conditions
- Calculate 126-day momentum for all sectors
- Rank sectors by momentum
- Select top 3 sectors
- Equal weight allocation
- Rebalance monthly (first trading day)

### Exit Conditions
- Sector falls out of top 3 ranking
- Monthly rebalancing trigger
- Momentum turns negative (if min_momentum > 0)

### Position Sizing
- Equal weight across selected sectors
- 1.25x leverage applied
- Example: 3 sectors × 33.3% × 1.25 = 41.6% per position

### Risk Management
- Maximum 3 positions
- Monthly rebalancing to reduce whipsaws
- Optional minimum momentum threshold
- Leverage limited to 1.25x

## Parameters

- **momentum_period**: 126 days (default) - Lookback for momentum calculation
- **top_n**: 3 (default) - Number of top sectors to hold
- **min_momentum**: 0.0 (default) - Minimum momentum to enter position
- **leverage**: 1.25 (optimal) - Applied leverage factor
- **rebalance_frequency**: "monthly" - When to rebalance

## Universe
- XLK (Technology)
- XLF (Financials)
- XLE (Energy)
- XLV (Healthcare)
- XLI (Industrials)
- XLP (Consumer Staples)
- XLU (Utilities)
- XLY (Consumer Discretionary)
- XLC (Communications)
- XLB (Materials)
- XLRE (Real Estate)

## Performance (2020-2024 Backtest)

- **CAGR**: 13.01%
- **Sharpe**: 1.712
- **Max Drawdown**: -12.3%
- **Win Rate**: 58%
- **BPS Score**: 0.784
- **Average Trade**: +2.3%
- **Best Year**: 2021 (+28.5%)
- **Worst Year**: 2022 (-8.2%)

## Walk-Forward Validation Results

Tested across 8 windows (6-month in-sample, 3-month out-of-sample):

| Window | In-Sample CAGR | Out-Sample CAGR | Sharpe |
|--------|---------------|-----------------|---------|
| 1 | 14.2% | 12.8% | 1.65 |
| 2 | 13.5% | 13.2% | 1.71 |
| 3 | 12.9% | 12.5% | 1.68 |
| 4 | 13.8% | 13.9% | 1.82 |
| 5 | 13.3% | 12.1% | 1.59 |
| 6 | 12.7% | 13.4% | 1.73 |
| 7 | 13.1% | 12.9% | 1.70 |
| 8 | 13.4% | 13.1% | 1.75 |

**Average Out-of-Sample**: 13.0% CAGR, 1.70 Sharpe

## Optimization History

### Grid Search Results
- Tested momentum periods: 60, 90, 126, 140, 160 days
- Tested top_n: 1, 2, 3, 4, 5, 6 sectors
- Optimal: 126 days, 3 sectors

### Evolutionary Algorithm Results
- Found alternative optimum: 77-day momentum
- Min momentum threshold: 0.044
- Slightly higher BPS but less stable

### Leverage Optimization
- Tested: 1.0x, 1.1x, 1.25x, 1.5x, 2.0x
- 1.25x optimal for Sharpe ratio
- 1.5x+ caused excessive drawdowns

## Production Deployment

- **Status**: Live on VPS
- **Account**: paper_main (PA3PSSF)
- **Started**: November 2024
- **Budget**: 100% of account
- **Health Port**: 8080

## Known Issues

1. **Whipsaws in choppy markets**: Can get caught in sideways action
2. **Lag during regime changes**: 126-day lookback slow to adapt
3. **Concentration risk**: Only 3 positions can be volatile

## Improvement Ideas

1. **Dynamic leverage based on volatility**
   - Scale down in high VIX environments
   - Scale up in low volatility trends

2. **Add trend confirmation filter**
   - Require SPY above 200D MA
   - Check market breadth indicators

3. **Regime-conditional parameters**
   - Shorter lookback in bull markets
   - Longer lookback in bear markets

4. **Sector pair trading**
   - Long top 3, short bottom 3
   - Market neutral approach

## Code Location
- Model: `/models/sector_rotation_v1.py`
- Production: `/production/models/SectorRotationModel_v1/`
- Config: `/configs/profiles.yaml` → `sector_rotation_leverage_1.25x`

## Testing Commands
```bash
# Quick backtest
python3 -m backtest.analyze_cli --profile sector_rotation_leverage_1.25x

# View results
python3 -m backtest.cli show-last

# Walk-forward validation
python3 -m engines.optimization.walk_forward_cli --quick
```

## Related Models
- [SectorRotationBull_v1](SectorRotationBull_v1.md) - Aggressive variant
- [SectorRotationBear_v1](SectorRotationBear_v1.md) - Defensive variant
- [SectorRotationAdaptive_v3](SectorRotationAdaptive_v3.md) - Volatility-targeting variant