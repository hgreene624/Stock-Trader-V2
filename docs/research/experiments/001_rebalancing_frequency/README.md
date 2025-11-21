# EXP-001: Optimal Rebalancing Frequency for SectorRotationAdaptive_v3

**Date**: 2025-11-21
**Model**: SectorRotationAdaptive_v3
**Status**: Completed

## Abstract

Tested the impact of rebalancing frequency (2-day, 7-day, 21-day) on SectorRotationAdaptive_v3 performance to determine the most profitable period accounting for Alpaca's fee structure. Monthly (21-day) rebalancing significantly outperformed, delivering +1.48% higher CAGR than the current weekly setting with fewer trades.

## Methods

- **Parameters tested**: Rebalancing period (2, 7, 21 trading days)
- **Backtest period**: 2020-01-01 to 2024-12-31
- **Data**: Daily bars for sector ETFs (XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC)
- **Profiles run**:
  - `sector_v3_rebalance_2day`
  - `sector_v3_rebalance_7day`
  - `sector_v3_rebalance_21day`

## Results

| Rebalancing | CAGR | Sharpe | BPS | Trades | Final NAV |
|-------------|------|--------|-----|--------|-----------|
| 2-Day | 10.50% | 1.734 | 0.802 | 2,461 | $164,389 |
| 7-Day (current) | 11.65% | 1.881 | 0.865 | 1,422 | $173,106 |
| **21-Day** | **13.13%** | **2.079** | **0.946** | **1,120** | **$184,920** |

## Conclusion

Monthly rebalancing is optimal for this model. The 126-day momentum signal changes slowly, making frequent rebalancing counterproductive (noise trading + transaction costs). Recommend updating production model from 7-day to 21-day rebalancing for +1.48% annual improvement.
