# Algorithmic Trading (2013) — Overall Summary

## Book Overview
- Chan frames the entire workflow—data hygiene, validation, automation, and risk control—as the true competitive edge for independent quants; the “prototype” strategies simply illustrate how to think about mean-reversion and momentum edges (Preface).
- Validation discipline is front-loaded: use cross-validation/rolling windows, Monte Carlo bootstraps, and single-source codebases to prevent look-ahead bias or parameter overfitting (Chapter 1).
- Mean-reversion coverage spans stationarity diagnostics (ADF, half-life), eigenportfolio construction, and execution engineering (tiered entries, borrow management), so traders can move from simple pairs to multi-asset baskets (Chapters 2–3).
- Cross-sectional strategies—both contrarian (Khandani & Lo style) and ETF-versus-stock arbitrage—require meticulous weighting, sector neutrality, and realistic cost modeling to stay viable in today’s thin spreads (Chapter 4).
- Futures material decomposes returns into spot versus roll, then harvests roll via ETF/future combos or uses roll persistence as a momentum signal (Chapters 5–6).
- Momentum sections explain structural drivers (roll, information diffusion, forced flows, HFT) and branch into factor models, alternative data (news analytics), and event-driven intraday edges whose half-lives keep shrinking (Chapters 6–7).
- Risk management returns to the Kelly framework but tempers it with fractional sizing, Monte Carlo leverage selection, and operational monitoring to avoid crowding blowups (Chapter 8).

## Key Project Takeaways
- Bake cross-validation and Monte Carlo p-value reporting into every experiment summary so reviewers can see how robust a backtest really is.
- Store data-transformation metadata (continuous futures settings, adjustment multipliers, eigenvectors) with the strategy; reproducibility is impossible without it.
- Expand our stat-arb research to include PCA-based ETF baskets and cross-sectional mean-reversion so we’re not dependent on pair signals alone.
- Differentiate momentum bots by their underlying driver (roll vs. news vs. flows) and monitor them with driver-specific health metrics.
- Separate spot and roll contributions in our futures analytics; otherwise we may be implicitly betting on term structure when we think we’re trading direction.
- Enforce fractional-Kelly leverage caps and require Monte Carlo stress write-ups before any model requests higher sizing.
- Use the extensive bibliography as a research backlog: assign owners to explore news analytics, macro-factor models, and roll-harvest techniques that we haven’t automated yet.

_Prepared 2025-11-26._
