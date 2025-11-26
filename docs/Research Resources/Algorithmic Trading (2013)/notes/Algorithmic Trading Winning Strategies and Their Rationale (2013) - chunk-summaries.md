# Algorithmic Trading (2013) — Chunk Summaries

_Manual pass using 15-page chunks. Citations reference the printed page numbers in the PDF._

## Chunk 1 (Pages 1–15)

### Main Points
- The preface sets expectations: Chan shares prototype strategies for both mean-reversion and momentum but pairs them with exhaustive warnings about implementation pitfalls (Preface, pp.xi–xiii).
- Compared with his 2009 book, this volume dives deeper into data quirks—survivorship bias, quote venues, futures settlement nuances—and promises more “why this works” rationale, not just how-to steps (pp.xii–xiii).
- The book urges readers to focus on rigorous backtesting discipline because the real differentiator for independent shops is process, not exotic hardware (pp.xi–xiii).

### Project-Relevant Highlights
- Treat each strategy write-up as a template: we still need to bolt on our own production risk controls before running anything live.
- Make sure our documentation mirrors Chan’s emphasis on recording data limitations alongside strategy logic so future maintainers know the edge’s assumptions.

## Chunk 2 (Pages 16–30)

### Main Points
- Chapter 1 stresses robust validation: use cross-validation or rolling windows when data is scarce, and add Monte Carlo bootstraps to gauge the probability that a backtest result could occur under randomness (pp.4–9).
- He advocates a single codebase for backtests and live trading to eliminate look-ahead bias and version drift (pp.9–10).
- Survivorship bias affects long-only and short-only portfolios differently, so traders must ensure dead tickers stay in the sample, especially when testing value shorts (pp.11–12).
- Intraday spread strategies demand either native spread quotes or synchronized bid/ask data for both legs; otherwise apparent profits vanish in live trading (pp.13–14).

### Project-Relevant Highlights
- Integrate cross-validation switches into our experiment harness so researchers can’t skip the step when data is thin.
- Keep archived symbol masters with delisted names for every equities dataset we touch; otherwise our short bias research will be overstated from day one.

## Chunk 3 (Pages 31–45)

### Main Points
- Chan explains why futures traders should rely on continuous contracts that splice rolls cleanly; naive concatenation can double-count roll returns or introduce gaps (pp.13–18).
- He catalogues reliable historical data sources for equities, futures, and FX, emphasizing the need to reconcile vendor-specific adjustments before backtesting (pp.18–21).
- Examples show how to convert broker-quoted rolls into clean price series and how to store metadata about contract specifications for reproducibility (pp.22–25).

### Project-Relevant Highlights
- Our data pipeline should store both raw contract series and the transformation logic we used to create continuous prices so auditors can replay historical rolls.
- Add data-quality checks that alert us when two vendors disagree materially on corporate action adjustments.

## Chunk 4 (Pages 46–60)

### Main Points
- The platform survey compares institutional stacks (Progress Apama, QuantHouse, Deltix) with retail favorites (MetaTrader, NinjaTrader, TradeStation) and explains when custom C++/Java is still worth the effort (pp.26–32).
- Chan recommends learning at least one general-purpose language tied directly to broker APIs so traders can control execution logic and monitoring rather than relying on opaque vendor scripts (pp.31–34).
- He underscores the operational value of logging frameworks, configuration management, and staging environments even for solo quants (pp.35–40).

### Project-Relevant Highlights
- Keep our Python core but invest in lightweight typed modules for the latency-sensitive execution path; this mirrors Chan’s push toward controllable infrastructure.
- Document deploy pipelines (dev → paper → live) so we never promote code straight from notebooks into production.

## Chunk 5 (Pages 61–75)

### Main Points
- Chapter 2 opens with mean-reversion basics: the Ornstein-Uhlenbeck model, augmented Dickey-Fuller (ADF) tests, and half-life estimates to confirm stationarity before trading (pp.41–46).
- Worked examples show how to code ADF/T-statistics for FX pairs (USD/CAD) and how parameter choices such as including drift impact conclusions (pp.42–44).
- Chan stresses that traders should base thresholds on statistical confidence, not chart patterns, and should store these diagnostics with the model (pp.44–48).

### Project-Relevant Highlights
- Build reusable stationarity test utilities in our research notebooks so every proposed mean-reversion strategy ships with ADF stats, p-values, and half-life outputs.
- Tie execution bands to these half-life calculations rather than arbitrary fixed distances.

## Chunk 6 (Pages 76–90)

### Main Points
- The chapter introduces multi-asset mean-reversion: use eigenvectors from the covariance matrix (or PCA) to form stationary ETF portfolios, then treat that synthetic spread like a single asset (pp.49–55).
- Kalman filters and rolling regressions are presented as adaptive alternatives to fixed-coefficient spreads, especially when constituent volatility drifts (pp.55–58).
- Chan highlights that the “best” portfolio is the eigenvector with the fastest mean-reversion half-life, not necessarily the one with the prettiest chart (pp.55–57).

### Project-Relevant Highlights
- Extend our stat-arb toolkit beyond pairs by adding PCA-based basket builders so we can capture sector-level dislocations instead of just two-legged trades.
- Store the eigenvectors and calibration windows in version control because re-estimating them later can produce materially different portfolios.

## Chunk 7 (Pages 91–105)

### Main Points
- Implementation details matter: he contrasts “all-in at L1” entries versus laddering capital at deeper z-scores (L2) and shows how probability estimates determine optimal scaling (pp.73–77).
- Stop-loss placement, capital reuse, and order types (limit vs. market) are analyzed as integral parts of a mean-reversion system, not afterthoughts (pp.77–83).
- The chapter warns that ignoring borrowing constraints and locate delays can turn a backtest winner into an infeasible live strategy (pp.82–84).

### Project-Relevant Highlights
- Formalize tiered entry templates inside our signal router so each mean-reversion bot declares how many tranches it expects to deploy.
- Integrate stock-loan availability checks ahead of sending shorts instead of reacting after fills fail.

## Chunk 8 (Pages 106–120)

### Main Points
- Cross-sectional mean reversion (a.k.a. pairs/basket trading) is explored: index arbitrage between ETFs and their underlying stocks, and modified spreads that compensate for today’s thinner mispricings (pp.88–94).
- Chan demonstrates ranking stocks by recent under/over-performance and using overnight convergence as the profit driver; it’s a complement to time-series reversion (pp.94–100).
- Execution tweaks such as using ETFs for hedges and accounting for basket transaction costs are critical for keeping signal edges positive (pp.97–100).

### Project-Relevant Highlights
- We should expand our cross-sectional engine so we can mix ETF hedges with single-stock legs, freeing us from needing borrows on every component.
- Ensure our optimizer includes exchange fees and taxes when evaluating market-versus-ETF arbitrage—these frictions now dominate edge sizing.

## Chunk 9 (Pages 121–135)

### Main Points
- Chan revisits the Khandani & Lo contrarian strategy: allocate capital proportional to the negative of each stock’s excess return relative to the index average, ensuring the book is dollar-neutral each close (pp.101–105).
- The text details enhancements such as volatility scaling, universe selection (S&P 500 vs. Russell 2000), and filtering out corporate action noise (pp.105–110).
- Risk sections emphasize sector-neutral versions and guardrails against deleveraging spirals during market stress (pp.110–112).

### Project-Relevant Highlights
- Adopt the capital-allocation formula (Equation 4.1) in our cross-sectional research repo so every engineer starts from a common baseline before customizing.
- Tag each simulation with the sector/industry constraints it used; otherwise we can’t compare drawdown performance apples-to-apples.

## Chunk 10 (Pages 136–150)

### Main Points
- Chapter 5 decomposes futures returns into spot return and roll return using exponential models for both components (Equations 5.7–5.8) to illustrate contango/backwardation math (pp.119–123).
- He demonstrates how to calculate realized roll yield and why it can dominate total return when holding contracts across multiple rolls (pp.123–127).
- Case studies explain when to prefer spot ETFs, when to stay in futures, and how to hedge out spot exposure while harvesting roll (pp.126–130).

### Project-Relevant Highlights
- Build analytics that separate spot and roll contributions for every futures strategy we test so we know whether an observed edge comes from price view or term-structure quirks.
- Consider ETF-versus-future arbitrage modules that monetize persistent roll without taking commodity directional bets.

## Chunk 11 (Pages 151–165)

### Main Points
- Chapter 6 introduces four structural causes of interday momentum: persistent roll signs, slow information diffusion, forced fund flows, and HFT manipulation (pp.131–133).
- A Treasury note (TU) case study walks through computing lagged returns, filtering independent samples, and confirming statistical significance before trading (pp.134–138).
- Chan compares time-series momentum (single asset) with cross-sectional momentum (rank across assets) and shows how each behaves differently across futures and equities (pp.138–142).

### Project-Relevant Highlights
- When we build momentum bots, log which “cause” they rely on; roll-persistence systems need very different monitoring than news-diffusion ones.
- Reuse the TU example code structure for other rate futures so we keep independent-sample filters consistent across desks.

## Chunk 12 (Pages 166–180)

### Main Points
- Factor models enter the scene: traders can regress stock returns against economic or statistical factors (including PCA components) to create cleaner cross-sectional signals (pp.143–147).
- The chapter highlights alternative data, especially news analytics (RavenPack, etc.), for ranking equities when fundamentals lag (pp.147–149).
- Chan notes that the same factor-style thinking can extend to futures, pairing macro factors like GDP growth with commodity returns (pp.148–150).

### Project-Relevant Highlights
- Incorporate news-sentiment features in our feature store and treat them as additional factors rather than standalone signals to avoid double-counting exposures.
- Train PCA models per asset class so we know which latent factors matter for equities versus currencies.

## Chunk 13 (Pages 181–195)

### Main Points
- Chapter 7 pivot to intraday and event-driven momentum: earnings drift windows have shrunk to hours, so systems must react intraday to capture residual move (pp.151–155).
- Macro announcement effects differ by market; EURUSD showed little edge, while GBPUSD exhibited tradable bursts after Bank of England releases (pp.155–158).
- Chan surveys vendor data (e.g., RavenPack) and academic findings to underline that signal half-lives keep shortening as more firms automate responses (pp.158–160).

### Project-Relevant Highlights
- For intraday experiments, bake in exchange-specific blackout rules and data-release calendars; edges vanish if we sample the wrong timestamps.
- Track half-life metrics for every event-driven signal so we know when increased competition has compressed the window below our latency budget.

## Chunk 14 (Pages 196–210)

### Main Points
- Chapter 8 revisits money management: the Kelly criterion maximizes long-term growth but is dangerously sensitive to estimation error, so fractional Kelly and Monte Carlo stress tests are recommended (pp.169–176).
- Graphs show how leverage selection interacts with drawdown tolerance; optimizing on historical CAGR is just another form of overfitting (pp.176–179).
- Chan advocates a culture of continuous monitoring—watch for correlation spikes, strategy crowding, and operational glitches—because even quantitative books blow up when leverage is mis-set (pp.179–182).

### Project-Relevant Highlights
- Standardize on fractional-Kelly limits for live books and justify any override with documented Monte Carlo scenarios.
- Feed our monitoring dashboards with leverage-utilization stats so we can react before combined exposures breach board-approved thresholds.

## Chunk 15 (Pages 211–225)

### Main Points
- The back matter (bibliography and index) provides references to academic papers, practitioner blogs, and vendor research that inspired the strategies in earlier chapters (pp.193–225).
- These references highlight ongoing research threads—news analytics, factor models, roll-yield harvesting—that we can mine for future experiments.

### Project-Relevant Highlights
- Use the bibliography as a roadmap for expanding our research backlog; assign owners to key papers so insights flow into new agents.
- Add links in our internal wiki to these cited resources so future engineers can trace every production strategy back to source literature.
