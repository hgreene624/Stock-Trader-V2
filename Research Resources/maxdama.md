# Max Dama on Automated Trading – Research Notes

**Progress**
- Pages processed: 57 / 57
- Last chunk reviewed: pages 1-57

## Key Insights
### Pages 1-15
- `p.2` Quant trading thrives when we treat code as the fastest path from idea to cash; build processes that let researchers iterate quickly instead of waiting on long product cycles.
- `p.14-18` Many “alpha” edges come from cleaning and transforming common data (normalize rates of change, apply heteroscedastic regressions, smooth chaos with EMAs) rather than exotic sources; focus our research backlog on rigorous feature engineering before chasing new datasets.
- `p.15-16` Traffic analysis techniques—monitoring sudden surges in message-board hype or SEC filing volume—can flag pump-and-dump penny stocks or fraud risks; wire these alternative-activity metrics into our regime monitors.

### Pages 16-25
- `p.17-18` Historical trivia (first-of-month effect, dispersion trades, weighted midpoint signals) illustrates that alpha spans multiple horizons; catalog these motifs in our idea tracker to spur new hypotheses.
- `p.21-22` Alpha toolbox/checklist highlights disciplined workflows: start from a hypothesis, define state, control for transaction costs, and stress test for structural breaks before scaling.
- `p.23-24` Simulation pitfalls: avoid survivorship bias (use delisted symbols), model adverse selection for limit orders, include realistic latency, and ensure data resolution matches the signal; our backtest harness must enforce these guards globally.
- `p.25-27` Parameter optimization should favor brute-force grids with visualization over clever hill-climbers/genetic algos; inspect profit-vs-parameter curves and reject isolated spikes to minimize overfitting.
- `p.27-28` Mike Dubno’s guidance: build a slow-but-correct backtester first, control every input (clock, random seeds), make systems unaware whether they’re in backtest/paper/live “worlds,” and treat data/market/portfolio/execution as separate services. Adopt these design rules in our toolchain docs.

### Pages 29-37
- `p.29-34` Portfolio allocation requires reliable covariance; shrink noisy sample correlations (regularization/factor models) and remember that even uncorrelated strategies converge to the common-correlation floor—keep adding truly independent edges.
- `p.31` Use sample-size thresholds to judge whether observed strategy correlations are statistically significant; don’t rebalance or decommission models on flimsy datasets.
- `p.33-34` Multi-strategy Kelly sizing ≈ mean-variance when returns are small; when data is scarce or skewed, temper Kelly fractions to avoid overbetting on fat-tailed edges.
- `p.36-37` Kelly’s log utility ignores higher moments; strategies with positive skew (lottery-like payoffs) break the quadratic approximation, so monitor skew/kurtosis before trusting Kelly outputs.

### Pages 38-45
- `p.38-40` Execution cost decomposes into liquidity impact (spread/depth, participation rate) and alpha decay; estimate each separately by analyzing no-trade signals vs executed trades, then minimize total shortfall by choosing an execution duration where curves intersect.
- `p.41-42` Back-of-envelope transaction-cost math (MSFT example) shows how per-share commissions, rebates, and spreads scale with volume; institutionalize similar “pen-and-envelope” reviews before pursuing medium-frequency ideas.
- `p.42-43` Strategy capacity is reached when the optimal execution time tends to “never trade”; use our impact models to derive AUM ceilings instead of guessing.
- `p.43-45` Measure impact empirically: bucket trades by size, classify buys/sells (Lee-Ready), and compute subsequent quote changes; integrate this diagnostic into our post-trade analytics to recalibrate slippage assumptions.

### Pages 46-57
- `p.46-48` Architectural design patterns—batch, scheduled, event-driven, augmented intelligence—map directly to strategy types; document which pattern each bot follows so supporting services (data feeds, monitoring) can be tailored correctly.
- `p.49-53` Pick programming environments based on developer skill and broker APIs: DSL/Excel for simple indicators, native APIs (Java/C++/.NET) for production systems; resist premature OS/hardware debates and focus on shipping version 1.
- `p.53-54` Hardware guidance: start on commodity machines or cloud, move to colocation only when latency/tick data becomes a binding constraint; capture these escalation criteria in our infra roadmap.
- `p.55-57` “Fix-it” and pit trading games underscore the need for robust accounting and position-tracking workflows; even simple trading simulations enforce that inventory must reconcile with trade logs before pnl is trusted.
