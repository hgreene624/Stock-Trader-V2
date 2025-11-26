# Algorithmic Trading (2013) — Lessons Applied to Our Platform

**Date:** 2025-11-27  
**Context:** Using Chan's 2013 playbook to harden validation, data lineage, and stat-arb expansion for the multi-model trading stack.  
**Source:** `docs/Research Resources/Algorithmic Trading (2013)/notes/Algorithmic Trading Winning Strategies and Their Rationale (2013) - overall-summary.md`

---

## Executive Summary

Chan's core message is that process quality beats clever signals: relentless data hygiene, cross-validation, and Monte Carlo stress-testing are the real edge. For us, that means upgrading experiment outputs (CV spreads, p-values, lineage artifacts), expanding beyond pairs into PCA baskets and sector-neutral contrarian trades, and making futures term-structure explicit so momentum bots declare their true driver (roll, news, flows). Leverage must stay fractional-Kelly with Monte Carlo evidence, and every promoted model should ship with reproducibility metadata.

---

## Validation and Reporting Upgrades

- **Default to rolling CV + Monte Carlo p-values:** Every `engines.optimization` run should report cross-validation dispersion and bootstrap/permutation p-values next to Sharpe/BPS so reviewers can see robustness, not just point estimates.  
- **Single-source code paths:** Backtests, optimization, paper, and live must share the same loaders/adjusters to avoid look-ahead drift; forbid notebook-only preprocessing.  
- **Experiment manifests:** Persist config hash, data slices, feature toggles, and random seeds with each results DB/CSV. Promote a model only if its manifest is present and readable.  
- **Walk-forward visibility:** Add stitched out-of-sample equity curves and CV spread plots to reporting so we can spot instability early.

## Data Lineage and Reproducibility

- **Track transformation metadata:** Save continuous-futures settings, adjustment multipliers, ETF/future combo ratios, and PCA eigenvectors alongside the generated datasets (e.g., `data/metadata/*.yaml`). Without these, reruns are non-deterministic.  
- **Cost/borrow metadata:** Record borrow rates, locate fees, and hard-to-borrow flags per instrument per date so stat-arb backtests reflect reality.  
- **Integrity checks:** Extend `engines.data.validator` to verify metadata presence before pipelines run; fail fast if lineage is missing.

## Strategy Roadmap Shifts

- **Stat-arb beyond pairs:** Move to PCA/eigenportfolio baskets and sector-neutral cross-sectional contrarian (Khandani/Lo style). Require neutral weighting, turnover-aware sizing, and realistic borrow/cost modeling.  
- **Momentum driver taxonomy:** Label bots by primary edge—roll-driven, news-driven, flow-driven—and monitor health with driver-specific metrics (roll persistence, news sentiment decay, volume/imbalance saturation).  
- **Term-structure awareness:** Decompose futures returns into spot vs. roll; let signals explicitly bet roll yield (or hedge it) instead of implicitly taking term-structure risk.  
- **ETF vs. underlying arbitrage:** Add monitoring for ETF/constituent dislocations; include borrow/frictions so the arb doesn't assume free inventory.

## Execution and Risk Controls

- **Execution engineering:** Support tiered entries for mean-reversion baskets, enforce borrow availability before order creation, and model partial fills; add locate/borrow fees into P&L.  
- **Fractional-Kelly sizing:** Keep leverage at fractional-Kelly levels selected via Monte Carlo of the trade path; refuse size increases without a stress-test write-up.  
- **Crowding and flow risk:** Track volume share and correlation clustering; throttle signals when crowding metrics breach thresholds to avoid liquidity cliffs.

## Immediate Actions for the Platform

1) Add CV/bootstrapped p-value reporting plus manifest export to `engines.optimization.reporting`.  
2) Extend `engines.data.pipeline` to write `data/metadata/*.yaml` for futures adjustments, PCA eigenvectors, and ETF/future ratios; block runs when lineage is missing.  
3) Spin up a `stat_arb_pca_v1` research track: PCA basket construction, sector-neutral weighting, borrow-aware execution tests.  
4) Add momentum-driver labels to model configs (`roll`, `news`, `flows`) and log driver-specific health metrics during backtest/paper.  
5) Integrate fractional-Kelly + Monte Carlo leverage selection into the risk engine; require evidence before promoting any model with higher sizing.

---
