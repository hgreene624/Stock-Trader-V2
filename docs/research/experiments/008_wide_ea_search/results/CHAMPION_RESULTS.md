# EA Wide Search Champion - SectorRotationAdaptive_v3

**Date**: 2024-11-23
**Experiment**: 008_wide_ea_search
**Model**: SectorRotationAdaptive_v3

## Performance Summary

| Metric | Value | vs SPY (14.34%) |
|--------|-------|-----------------|
| **CAGR** | 27.89% | +13.55% |
| **Sharpe Ratio** | 3.192 | Excellent |
| **BPS** | 1.432 | - |
| **Max Drawdown** | -27.69% | Higher risk |
| **Total Trades** | 1114 | Active trading |
| **Final NAV** | $340,175 | 3.4x initial |

## Winning Parameters

```yaml
atr_period: 12
stop_loss_atr_mult: 1.46
take_profit_atr_mult: 3.75
min_hold_days: 2
bull_leverage: 1.86
bear_leverage: 2.0
bull_momentum_period: 138
bear_momentum_period: 175
bull_top_n: 4
bear_top_n: 3
```

## EA Optimization Details

- **Population Size**: 30
- **Generations**: 20
- **Total Backtests**: 600
- **Runtime**: ~16 minutes
- **Seed**: 42 (reproducible)
- **Parallel Cores**: 7

### Evolution Progress
- Gen 1: BPS 1.055
- Gen 5: BPS 1.242
- Gen 10: BPS 1.330
- Gen 15: BPS 1.358
- Gen 20: BPS 1.440

## Key Insights

### What Makes This Configuration Work

1. **Short ATR Period (12)**: Quick adaptation to volatility changes
2. **Wide Take Profit (3.75x ATR)**: Lets winners run
3. **Tight Stop Loss (1.46x ATR)**: Cuts losses quickly
4. **Asymmetric Leverage**: Bear leverage (2.0) > Bull leverage (1.86)
   - More aggressive in bear markets (buying dips)
5. **Long Momentum Periods**: 138-175 days captures longer trends
6. **4 Sectors in Bull, 3 in Bear**: More diversified in bull, concentrated in bear

### Risk Considerations

- Max drawdown of -27.69% is significant
- High leverage (up to 2.0x) amplifies both gains and losses
- 1114 trades over 5 years = ~223 trades/year = active trading

## Reproduction

### Run Backtest
```bash
python3 -m backtest.analyze_cli --profile ea_wide_search_winner
```

### Profile Location
`configs/profiles.yaml` - profile name: `ea_wide_search_winner`

### Results Location
`docs/research/experiments/008_wide_ea_search/results/ea_winner_validation/`

## Comparison to Previous Champion

| Metric | Previous (ea_optimized_atr) | New (ea_wide_search_winner) | Improvement |
|--------|----------------------------|----------------------------|-------------|
| CAGR | 17.64% | 27.89% | +58% |
| Sharpe | 2.238 | 3.192 | +43% |
| BPS | 1.020 | 1.432 | +40% |

## Deployment Notes

- Deployed to VPS: 2024-11-23
- Account: paper_2k
- Mode: paper trading
- Version: See git commit for exact code version

## Git Commit

Commit hash will be recorded after deployment.
