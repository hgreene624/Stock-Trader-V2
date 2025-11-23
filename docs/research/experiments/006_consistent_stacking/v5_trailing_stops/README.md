# V5 Trailing Stops (2.0 ATR)

## Hypothesis
Adding trailing ATR-based stops to V3 will reduce drawdowns by protecting profits on winning positions without significantly hurting returns.

## Parameters
- `trailing_atr_mult`: 2.0 (exit if price drops 2.0 ATR from high watermark)
- All other parameters same as V3 baseline

## Results
- **CAGR**: 16.12% (down from 17.17% baseline)
- **Sharpe**: 1.935 (down from 2.013)
- **Max Drawdown**: 35.29% (barely improved from 35.78%)
- **Commission**: $50,342 (down from $55,224)

## Conclusion
**FAILED** - Trailing stops at 2.0 ATR are too tight. They cut winners early, hurting returns by 1% CAGR while providing minimal drawdown improvement (0.5%).

## Next Steps
- Test wider trailing stops (3.0 ATR) in v5_wide_trailing
