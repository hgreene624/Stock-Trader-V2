# Model Documentation

This directory contains detailed documentation for all trading models in the system.

## Production Models

### Sector Rotation Family (BEST PERFORMERS)
- [SectorRotationModel_v1.md](SectorRotationModel_v1.md) - **13.01% CAGR (verified)** - Base momentum model
- [SectorRotationBull_v1.md](SectorRotationBull_v1.md) - Not Yet Tested - Bull market specialist
- [SectorRotationBear_v1.md](SectorRotationBear_v1.md) - Not Yet Tested - Bear market defensive
- [SectorRotationAdaptive_v3.md](SectorRotationAdaptive_v3.md) - Testing - Volatility targeting

## Research Models

### Equity Trend Models
- [EquityTrendModel_v1.md](EquityTrendModel_v1.md) - 200D MA trend following
- [EquityTrendModel_v2_daily.md](EquityTrendModel_v2_daily.md) - Daily bar variant

### Mean Reversion Models
- [IndexMeanReversionModel_v1.md](IndexMeanReversionModel_v1.md) - RSI + Bollinger Bands

### Crypto Models
- [CryptoMomentumModel_v1.md](CryptoMomentumModel_v1.md) - Dual momentum for BTC/ETH

### Options Models
- [CashSecuredPut_v1.md](CashSecuredPut_v1.md) - Income generation strategy

## Model Performance Summary

| Model | Stage | CAGR | Sharpe | MaxDD | BPS | Data Source |
|-------|-------|------|--------|-------|-----|-------------|
| SectorRotationModel_v1 | Production | **13.01%** | 1.712 | -12.3% | 0.784 | Verified (CLAUDE.md) |
| SectorRotationBull_v1 | Production | Not Yet Tested | N/A | N/A | N/A | No backtest found |
| SectorRotationBear_v1 | Production | Not Yet Tested | N/A | N/A | N/A | No backtest found |
| SectorRotationAdaptive_v3 | Paper | TBD | TBD | TBD | TBD | In testing |
| EquityTrendModel_v1 | Research | Not Yet Tested | N/A | N/A | N/A | No backtest found |
| IndexMeanReversionModel_v1 | Research | Not Yet Tested | N/A | N/A | N/A | No backtest found |
| CryptoMomentumModel_v1 | Research | Not Yet Tested | N/A | N/A | N/A | No backtest found |

**Important**: Only SectorRotationModel_v1 has verified performance metrics from actual backtests. Other models have been developed but lack documented test results.

**Target**: Beat SPY's 14.34% CAGR (2020-2024)

## Model Development Lifecycle

```
Research → Backtest → Paper → Production
```

1. **Research**: Initial development and testing
2. **Backtest**: Historical validation with walk-forward
3. **Paper**: Live market testing with virtual capital
4. **Production**: Real money deployment

## Adding New Models

1. Create model file in `models/` directory
2. Add documentation here with template below
3. Add to `configs/profiles.yaml` for testing
4. Run walk-forward validation
5. Document results in `docs/research/experiments/`

## Documentation Template

```markdown
# ModelName_v1

## Overview
Brief description of strategy

## Strategy Details
- Entry conditions
- Exit conditions
- Position sizing
- Risk management

## Parameters
- param1: description (default: X)
- param2: description (default: Y)

## Performance
- CAGR: X%
- Sharpe: X.XX
- Max Drawdown: -X%
- Win Rate: X%
- BPS Score: X.XX

## Backtest Results
[Include key metrics from walk-forward validation]

## Known Issues
- Issue 1
- Issue 2

## Improvement Ideas
- Idea 1
- Idea 2
```