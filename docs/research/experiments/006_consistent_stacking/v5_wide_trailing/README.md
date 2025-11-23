# V5 Wide Trailing Stops (3.0 ATR)

## Hypothesis
Wider trailing stops (3.0 ATR) will preserve more winners while still providing some drawdown protection.

## Parameters
- `trailing_atr_mult`: 3.0 (exit if price drops 3.0 ATR from high watermark)
- All other parameters same as V3 baseline

## Results
- **CAGR**: 14.16% (down from 17.17% baseline)
- **Sharpe**: 1.759 (down from 2.013)
- **Max Drawdown**: ~35%
- **Trades**: 1368

## Conclusion
**FAILED** - Wider stops performed even worse than tight stops. Performance dropped 3% CAGR from baseline with no meaningful benefit.

## Final Assessment
Trailing ATR stops are counterproductive for this momentum rotation strategy. The momentum-based rotation already provides natural exits when momentum shifts. Adding trailing stops just cuts winners early.

**Recommendation**: Abandon trailing stops approach. V3 remains best model at 17.17% CAGR.
