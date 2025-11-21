# SectorRotationBear_v1

## Overview
Defensive sector rotation variant designed for bear market and uncertain conditions. Prioritizes capital preservation with conservative parameters.

## Strategy Details

### Activation Conditions
- Active in BEAR or NEUTRAL regimes
- Complements Bull model for all-weather coverage
- Provides defensive positioning during uncertainty

### Entry/Exit Logic
- 126-day momentum (same as base for stability)
- Top 2 sectors only (concentration in strongest)
- 1.0x leverage (no leverage in uncertain times)
- Higher minimum momentum (0.10) for quality filter
- Monthly rebalancing

## Parameters
- **momentum_period**: 126 days (proven stable)
- **top_n**: 2 (defensive concentration)
- **min_momentum**: 0.10 (high quality threshold)
- **target_leverage**: 1.0x (conservative)

## Performance
- **CAGR**: Not Yet Tested
- **Sharpe**: Not Yet Tested
- **Max Drawdown**: Not Yet Tested
- **Win Rate**: Not Yet Tested
- **BPS Score**: Not Yet Tested

**Note**: This model has been deployed but lacks documented backtest results. Performance metrics will be updated once proper backtesting is completed.

## Production Status
- **Deployed**: Yes, on VPS
- **Account**: paper_main
- **Budget**: 0.33 (shared with Bull model)
- **Regime Gate**: Bear/Neutral markets

## Design Philosophy
During bear markets:
- Preserve capital first
- High quality only
- No leverage
- Accept lower returns for safety

## Strategy Rationale
- Longer momentum period filters noise
- Fewer positions reduce whipsaws
- Higher momentum threshold ensures strength
- No leverage protects during volatility

## Related Models
- [SectorRotationModel_v1](SectorRotationModel_v1.md) - Base model
- [SectorRotationBull_v1](SectorRotationBull_v1.md) - Aggressive variant