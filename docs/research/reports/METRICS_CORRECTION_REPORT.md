# Metrics Correction Report

## Date: November 21, 2025

## Issue Identified

Documentation contained fabricated performance metrics for models that had never been properly backtested. This violated fundamental principles of scientific integrity and research honesty.

## Corrections Made

### 1. /docs/research/RESEARCH_SUMMARY.md

**Fabricated Metrics Removed:**
- SectorRotationBull_v1: Listed as 11.8% CAGR, 1.45 Sharpe, -15.2% MaxDD → Corrected to "Not Yet Tested"
- SectorRotationBear_v1: Listed as 9.2% CAGR, 1.28 Sharpe, -18.5% MaxDD → Corrected to "Not Yet Tested"
- EquityTrendModel_v1: Listed as 8.5% CAGR → Corrected to "Not Yet Tested"
- IndexMeanReversionModel_v1: Listed as 6.2% CAGR → Corrected to "Not Yet Tested"
- CryptoMomentumModel_v1: Listed as 15.3% CAGR, 0.85 Sharpe, -35% MaxDD → Corrected to "Not Yet Tested"

### 2. /docs/models/README.md

**Fabricated Metrics Removed:**
- SectorRotationBull_v1: Listed as 11.8% CAGR, 1.45 Sharpe, -15.2% MaxDD, 0.68 BPS → Corrected to "Not Yet Tested"
- SectorRotationBear_v1: Listed as 9.2% CAGR, 1.28 Sharpe, -18.5% MaxDD, 0.55 BPS → Corrected to "Not Yet Tested"
- EquityTrendModel_v1: Listed as 8.5% CAGR, 0.92 Sharpe, -22% MaxDD, 0.45 BPS → Corrected to "Not Yet Tested"
- IndexMeanReversionModel_v1: Listed as 6.2% CAGR, 0.78 Sharpe, -18% MaxDD, 0.38 BPS → Corrected to "Not Yet Tested"
- CryptoMomentumModel_v1: Listed as 15.3% CAGR, 0.85 Sharpe, -35% MaxDD, 0.42 BPS → Corrected to "Not Yet Tested"

### 3. /docs/models/SectorRotationBull_v1.md

**Fabricated Metrics Removed:**
- Performance section showed 11.8% CAGR, 1.45 Sharpe, -15.2% MaxDD, 55% Win Rate, 0.68 BPS
- All metrics replaced with "Not Yet Tested"
- Added note: "This model has been deployed but lacks documented backtest results"

### 4. /docs/models/SectorRotationBear_v1.md

**Fabricated Metrics Removed:**
- Performance section showed 9.2% CAGR, 1.28 Sharpe, -18.5% MaxDD, 52% Win Rate, 0.55 BPS
- All metrics replaced with "Not Yet Tested"
- Added note: "This model has been deployed but lacks documented backtest results"

### 5. /docs/MODEL_PERFORMANCE.md

**Fabricated Metrics Removed:**
- SectorRotationBull_v1: Listed as 11.8% CAGR, 1.45 Sharpe, -15.2% MaxDD, 55% Win Rate, 0.68 BPS → Corrected to "Not Yet Tested"
- SectorRotationBear_v1: Listed as 9.2% CAGR, 1.28 Sharpe, -18.5% MaxDD, 52% Win Rate, 0.55 BPS → Corrected to "Not Yet Tested"
- Added "Data Source" column to performance table for transparency

### 6. /docs/research/AGENT_CONTEXT.md

**Fabricated Metrics Removed:**
- SectorRotationBull_v1: Listed as 11.8% CAGR → Corrected to "Not Yet Tested"
- SectorRotationBear_v1: Listed as 9.2% CAGR → Corrected to "Not Yet Tested"

## Verified Data Sources

The ONLY model with verified performance metrics from actual backtests is:

**SectorRotationModel_v1:**
- CAGR: 13.01%
- Sharpe: 1.712
- Max Drawdown: -12.3%
- BPS: 0.784
- Source: Documented in CLAUDE.md and verified through backtest results

## Additional Findings

- `/docs/reports/implementation_status.md` mentions EquityTrendModel_v1 with "30% return / 26.9% CAGR / Sharpe 3.31" but notes this is for a limited "668-bar sample" - not a full backtest
- `/docs/research/WHAT_WORKED.md` and `/docs/research/WHAT_FAILED.md` correctly reference only verified metrics

## Lessons Learned

1. **Never fabricate data** - If metrics don't exist, state "Not Yet Tested" or "TBD"
2. **Always cite sources** - Every metric should have a traceable source (backtest file, results database, etc.)
3. **Distinguish between planned and actual** - Clearly separate what we intend to test from what has been tested
4. **Document uncertainty** - When unsure, err on the side of transparency

## Recommendations

1. **Run proper backtests** for SectorRotationBull_v1 and SectorRotationBear_v1 before claiming any performance metrics
2. **Add verification step** to documentation process - require backtest evidence for any performance claims
3. **Create audit trail** - Link each metric to specific backtest runs with timestamps and configuration
4. **Regular audits** - Periodically verify all documented metrics against source data

## Integrity Commitment

Going forward, all performance metrics will:
- Be based on actual backtest results
- Include source references
- Be clearly marked if estimated or projected
- Be updated only when new verified data is available

This correction ensures the research documentation maintains scientific integrity and provides accurate information for decision-making.