# SectorRotationBull_v1

## Overview
Aggressive sector rotation variant optimized for bull market conditions. Designed to capture upside with higher leverage and more positions during favorable market regimes.

## Strategy Details

### Activation Conditions
- Only active when regime classifier detects BULL market
- Uses equity regime from RegimeEngine
- Returns empty weights in non-bull conditions

### Entry/Exit Logic
- Similar to base model but with aggressive parameters
- 80-day momentum lookback (faster than base)
- Top 4 sectors (more diversification)
- 1.3x leverage (higher than base)
- Monthly rebalancing

## Parameters
- **momentum_period**: 80 days (optimized for bull markets)
- **top_n**: 4 (more positions for upside capture)
- **min_momentum**: 0.03 (lower threshold)
- **target_leverage**: 1.3x (aggressive positioning)

## Performance
- **CAGR**: Not Yet Tested
- **Sharpe**: Not Yet Tested
- **Max Drawdown**: Not Yet Tested
- **Win Rate**: Not Yet Tested
- **BPS Score**: Not Yet Tested

**Note**: This model has been deployed but lacks documented backtest results. Performance metrics will be updated once proper backtesting is completed.

## Walk-Forward Optimization
Optimized on bull market periods from Windows 1 and 5:
- Shorter momentum captures quick rotations
- Higher leverage justified by favorable conditions
- More positions reduce concentration risk

## Production Status
- **Deployed**: Yes, on VPS
- **Account**: paper_main
- **Budget**: 0.33 (shared with Bear model)
- **Regime Gate**: Bull markets only

## Design Philosophy
During bull markets:
- Be more aggressive
- Capture broad rally
- Accept higher volatility
- Maximize upside participation

## Related Models
- [SectorRotationModel_v1](SectorRotationModel_v1.md) - Base model
- [SectorRotationBear_v1](SectorRotationBear_v1.md) - Defensive variant