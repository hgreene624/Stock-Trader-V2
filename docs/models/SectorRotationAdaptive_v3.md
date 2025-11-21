# SectorRotationAdaptive_v3

## Overview
Volatility-targeting sector rotation model that dynamically adjusts leverage based on market volatility to maintain consistent risk exposure.

## Strategy Details

### Core Innovation
Instead of fixed leverage, dynamically scales position size to target 15% annualized volatility:
- Low market vol → Higher leverage (up to 2x)
- High market vol → Lower leverage (down to 0.5x)
- Maintains consistent risk profile

### Calculation Method
```python
current_vol = calculate_rolling_volatility(21_days)
target_vol = 15%
leverage = min(2.0, max(0.5, target_vol / current_vol))
```

### Base Strategy
- Uses proven 126-day momentum
- Top 3 sectors
- Monthly rebalancing
- Volatility adjustment layer on top

## Parameters
- **momentum_period**: 126 days
- **top_n**: 3
- **target_volatility**: 15% annualized
- **vol_lookback**: 21 days
- **max_leverage**: 2.0x
- **min_leverage**: 0.5x

## Expected Performance
**Currently in Testing** (Started Nov 20, 2025)

Theoretical benefits:
- More consistent returns
- Lower drawdowns in volatile periods
- Higher returns in calm periods
- Better Sharpe ratio

## Testing Status
- **Account**: paper_2k ($2,000 test account)
- **Started**: November 20, 2025
- **Health Port**: 8081
- **Results**: TBD (need 30+ days)

## Design Hypothesis
Market volatility clusters:
- High vol periods → Reduce exposure
- Low vol periods → Increase exposure
- Target constant portfolio volatility
- Should improve risk-adjusted returns

## Implementation Details
- Calculates rolling 21-day volatility daily
- Adjusts leverage before rebalancing
- Applies leverage to entire portfolio
- Respects min/max bounds

## Monitoring Plan
Track vs base model:
1. Daily volatility realized vs target
2. Drawdown comparison
3. Sharpe ratio improvement
4. Leverage utilization stats

## Success Criteria
- Achieve 15% ± 2% realized volatility
- Improve Sharpe by 0.1+
- Reduce max drawdown by 2%+
- Maintain 12%+ CAGR

## Related Models
- [SectorRotationModel_v1](SectorRotationModel_v1.md) - Base model (fixed leverage)
- This is the adaptive version