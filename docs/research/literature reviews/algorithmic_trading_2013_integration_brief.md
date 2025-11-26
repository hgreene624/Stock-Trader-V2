# Integration Brief — Algorithmic Trading (2013) Lessons

**Purpose:** Translate Chan's 2013 guidance into actionable architecture/infra/workflow updates for the trading platform.  
**Status:** Draft for review. Simple 3 (monkey tests, component tests, data burn tracker) already implemented.  
**Source:** `docs/research/literature reviews/algorithmic_trading_2013_lessons.md`

---

## Core Advice to Integrate
- **Process > signals:** Validation discipline (CV, Monte Carlo, manifests) and data hygiene are the edge.
- **Lineage:** Persist transformation metadata (continuous futures settings, adjustment multipliers, ETF/future ratios, PCA eigenvectors).
- **Stat-arb depth:** Move beyond pairs to PCA/eigenportfolios and sector-neutral contrarian baskets with borrow/cost awareness.
- **Driver clarity:** Label momentum bots by edge (roll, news, flows) and monitor driver-specific health.
- **Leverage discipline:** Fractional-Kelly sizing selected via Monte Carlo; no size increases without evidence.

## Proposed Changes (Post–Simple 3)

### Reporting & Validation
- Add CV dispersion + bootstrap/permutation p-values to `engines/optimization.reporting` outputs and CLI summaries.
- Emit `results/<exp>/manifest.yaml` (config hash, data slice, seeds, feature toggles) per run; require manifest for model promotion.
- Plot stitched out-of-sample equity curves and CV spread in reports to surface stability.
- Keep leverage gate: risk engine blocks >1.0x unless a Monte Carlo sizing memo is attached (stub now; full Monte Carlo later).

### Data Lineage & Repro
- Extend `engines/data.pipeline` to write `data/metadata/*.yaml` capturing futures adjustments, ETF/future ratios, PCA eigenvectors.
- Update `engines/data.validator` to hard-fail when lineage metadata is missing; log which strategies have consumed which slices.
- Store borrow/cost metadata (borrow rates, locate fees, HTB flags) per instrument/date and thread into backtests.

### Strategy Architecture
- Add `driver:` field to model configs (`roll|news|flows|mixed`) and log driver-specific health metrics in backtest/paper.
- Stand up a PCA stat-arb track: eigenportfolio construction, sector-neutral weighting, turnover-aware sizing, borrow-aware execution; validate with Simple 3 + CV.
- Make term-structure explicit: decompose futures P&L into spot vs roll; let strategies declare and hedge roll exposure.
- Add ETF-vs-constituent dislocation monitor with borrow/friction inputs to avoid “free inventory” assumptions.

### Execution & Risk
- Enforce borrow-availability checks pre-order; inject locate/borrow fees into P&L; model partial fills and tiered entries for mean-reversion baskets.
- Integrate fractional-Kelly sizing via Monte Carlo trade-path resampling; tie any leverage increase to that output once built.

### Workflow / SOP
- Promotion checklist: Simple 3 outputs + manifest + CV/p-values + driver tag + lineage present. No manifest, no promotion.
- Run cadence: backtest → monkey/component → walk-forward → CV/p-values (Monte Carlo only when requesting >1.0x leverage).
- Data SOP: declared train/validate split and burn-log entry before optimization; block reruns on burned ranges unless explicitly waived.

## Owners & Dependencies (suggested)
- Validation/reporting: Optimization engine owner.
- Data lineage: Data pipeline owner.
- Stat-arb track: Research owner with data pipeline support.
- Risk/exec changes: Risk engine + execution owner.

## Open Questions
- Where should manifests and metadata live long-term (`results/` vs `logs/` vs `artifacts/`)?  
- Do we standardize on a single CV scheme (k-fold vs rolling window) for reporting?  
- What percentile thresholds unlock leverage >1.0x when Monte Carlo sizing lands (e.g., 95th percentile DD < 40%, RoR < 10%)?  
- How to prioritize PCA stat-arb vs term-structure work in the research queue?

---

**Next Action:** Confirm storage location for this brief and link it from the relevant index. Once location is set, socialize with the optimization, data, and research owners.  
