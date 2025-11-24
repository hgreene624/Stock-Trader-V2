# V3: All Improvements (Correlation Sizing)

## Hypothesis
Adding correlation-based sizing on top of tuned crash + relative strength will reduce drawdown by avoiding correlated sector pairs.

## Parameters
- Tuned crash thresholds
- `use_relative_strength: true`
- `use_correlation_sizing: true`
- `correlation_threshold: 0.75`
- `correlation_weight_reduction: 0.5`

## Results
- **CAGR**: 10.13%
- **Sharpe**: 1.555
- **Max DD**: 31.4%
- **BPS**: 0.727

## Conclusion
**NO EFFECT** - Identical results to V2 (10.13% CAGR both).

Correlation sizing at 0.75 threshold had no measurable impact. Either:
1. Threshold too high (sectors rarely correlated > 0.75)
2. Implementation issue
3. Sector ETFs not correlated enough to matter

## Next Steps
- Test correlation threshold at 0.6 or 0.7
- Or abandon this approach
