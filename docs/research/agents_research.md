# Agents Research Digest

## Sources
1. **Building Winning Algorithmic Trading Systems – Kevin J. Davey (2014)**  – working notes in `Research Resources/Building-Algorithmic-Trading-Systems.md`.
2. **Max Dama on Automated Trading (2008-2011)** – compiled blog notes in `Research Resources/maxdama.md`.

## Key Insights
### 1. Strategy Research Workflow
- Treat testing as a gated pipeline: idea ➝ limited sample test ➝ walk-forward ➝ Monte Carlo ➝ incubation before capital deployment (pp. 71-152).
- Limited tests should cover ~2 random years with ≥70% profitable parameter iterations before advancing (p.104); discard or reverse-engineer concepts below 30%.
- Walk-forward settings must be chosen upfront (in-sample 25–50 trades per parameter, out-sample 10–50% of in-window) to avoid hidden optimization (pp. 116-141).
- Maintain documentation (naming, wish lists, test logs) so future agents can audit every assumption (pp.147-152).

### 2. Data Integrity & Execution Modeling
- Align pit/electronic sessions, avoid ratio math on back-adjusted contracts, and model FX fills with bid/ask-aware market orders to prevent phantom edge (pp.100-115).
- Always bake slippage/commissions into optimizations (≥$5 RT, 1–2 ticks), otherwise optimizers will over-trade and collapse live (pp.57-59).
- Limit-order fills in backtests should require penetration; treat “touch fills” as upside variance and track actual vs expected slippage during live reviews (pp.226-227).

### 3. Risk, Capital, and Position Sizing
- Under-capitalization guarantees ruin—even solid systems need base equity covering margin + historical drawdown + safety buffer (pp.34-36, 177-183).
- Use Monte Carlo to size: target risk-of-ruin <10%, median max drawdown <40%, return/DD >2; adjust fixed-fraction `x` per system and for the combined portfolio (pp.64-70, 144-159, 165-169).
- Diversification is the closest thing to a “holy grail”; measure it via equity linearity (R²), combined drawdowns, and Monte Carlo return/DD improvements before allocating capital (pp.133-152, 165-169).

### 4. Operational Discipline
- Predefine start/stop criteria (e.g., average of 1.5× worst historical DD and 95th percentile Monte Carlo DD) and stick to them regardless of short-term PnL swings (pp.188-195, 222-224).
- Separate broker accounts per system, maintain backups (PC, Internet, broker desk), and understand where orders rest to handle outages or automation bugs quickly (pp.195-205).
- Track monthly and daily performance against expectation envelopes (mean ±σ or Monte Carlo percentiles) to detect drift early without overreacting (pp.205-230).

### 5. Psychology & Governance
- Emotional capital matters even for bots: codify “do not trade” states after life shocks and enforce “take every signal” rules to avoid discretionary sabotage (pp.15-18, 187-194).
- Log real-time reviews (weekly/monthly) so future agents can study whether deviations stem from market regime shifts, tooling issues, or model decay (pp.219-245).
- Ignore demo heroes and gurus without audited live returns; focus on verifiable edges, continuous experimentation (expect 100–200 failed ideas per winner), and long-run discipline (pp.235-245).

### 6. Max Dama on Automated Trading (2008-2011)
- Alpha generation often boils down to cleaning and transforming common data (normalize rates of change, smooth chaotic signals) plus creative traffic-analysis proxies (message-board surges, SEC filing bursts) to flag hype or fraud regimes (`maxdama.md`, pp.14-18).
- Simulation discipline: guard against survivorship bias, adverse selection, unrealistic latency, and sloppy optimization; favor brute-force parameter sweeps with visual profit-vs-parameter plots and follow Mike Dubno’s advice (slow-then-fast backtesters, identical “worlds” for backtest/paper/live) (`maxdama.md`, pp.23-28).
- Multi-strategy allocation should shrink noisy covariance estimates, monitor statistical significance of correlations, and temper Kelly sizing when returns are skewed; Kelly≈Markowitz only when higher moments are negligible (`maxdama.md`, pp.29-37).
- Execution modeling = liquidity impact + alpha decay; estimate each via no-trade baselines vs executed trades, minimize total shortfall, and derive capacity when the optimal slice time becomes “never trade” (`maxdama.md`, pp.38-45).
- Architecture choices depend on strategy pattern (batch, scheduled, event-driven, augmented intelligence); pick tooling/OS based on broker APIs, start on commodity hardware/cloud, and escalate to colocation only when latency/tick data demand it (`maxdama.md`, pp.46-54).
