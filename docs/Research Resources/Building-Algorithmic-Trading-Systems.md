# Building Algorithmic Trading Systems – Trading Bot Learnings

**Progress**
- Pages processed: 284 / 284
- Last chunk reviewed: pages 261-284

## Key Insights
### Pages 1-20
- `p.15-16` Emotional trauma and distraction drove catastrophic discretionary bets (e.g., live cattle before mad cow news); codify a rule to disable trading when psychological capital is depleted so live bots don't take impulsive positions.
- `p.17` Mindset work cannot compensate for flawed research; treat disciplined system development/testing as the lever for performance, not motivational routines.
- `p.18` Even discretionary edges should be decomposed into statistically testable components (e.g., moving-average cross, stop logic) so they can undergo walk-forward analysis and gentle optimization before deploying.
- `p.19` No single “holy grail” strategy exists; plan for diversification across multiple uncorrelated systems as the closest thing to a reliable edge.

### Pages 21-40
- `p.24-25` Glossy marketing case studies (e.g., head-and-shoulders nostalgia) hide the abundance of false signals and hindsight bias; every pattern in the research set must be stress-tested on unseen data before assuming it carries edge.
- `p.27` Handfuls of manual backtests (10–20 trades) are meaningless; require hundreds of trades that include realistic slippage/commission modeling before funding a rule set.
- `p.28-29` “Reverse the system” thinking is just another untested hypothesis; never flip logic or adjust rules without fresh research, because trends that help the original rules will destroy the mirror image.
- `p.30-32` Scale-trading/averaging strategies boast high win rates but deliver poor risk-adjusted returns (10–20% with 20%+ drawdowns) and demand large capital buffers; our bots should avoid martingale-like pyramiding unless reserve capital and stop-loss rules bound tail risk.
- `p.33-34` Averaging down in leveraged futures quickly turned a manageable drawdown into a $70K loss plus forced margin top-ups; implement hard loss limits per strategy to prevent “capital infusion” spirals.
- `p.35` After reviewing every failed approach, only well-tested mechanical strategies showed promise; invest research time into robust walk-forward workflows and avoid live experiments with unverified ideas.
- `p.38` Before building a system, define the return, drawdown, and evaluation metrics (e.g., contest target 100% return with 75% max DD) to ensure optimization choices align with the mission.
- `p.39` Don’t pick instruments because they backtested best; select markets via forward-looking criteria and run correlation studies, otherwise you’re just optimizing on the portfolio mix.
- `p.40` Trend-following edge depends on capturing the few big moves; ensure capital/margin is sufficient to take every signal, or the system’s statistics collapse when the winning trade happens while you’re sidelined.

### Pages 41-70
- `p.41` Chasing leaderboard goals tempted the author to average down in coffee, reinforcing the rule: never break trade rules to hit arbitrary return targets because those lapses usually erase months of disciplined gains.
- `p.43-44` The 2006 contest win was helped by sticking to position sizing (one contract) even after tripling capital; resist the urge to scale up during winning streaks until the system proves stability across regimes.
- `p.47-53` Transitioning to full-time trading required more than good strategies—confidence, 3–5 years of living expenses, and family buy-in kept psychological drawdowns from forcing bad decisions.
- `p.48-51` Use realistic capitalization targets (ideally $2–3M for full-time futures) so the strategy doesn’t need 50–100% annual returns just to fund life; undercapitalized accounts guarantee ruin even with positive expectancy.
- `p.51-53` Maintain a strategy inventory: for every live strategy, have a vetted replacement plus a research backlog, since many systems behave like shooting stars and must be rotated out before performance collapses.
- `p.52` Spread risk across multiple brokers/clearing firms and keep redundant connectivity so a single failure (e.g., Refco, PFG Best) doesn’t shut your automation down.
- `p.53-54` Treat trading as a business with boundaries; overworking or losing motivation both hurt research throughput, so schedule time and build habits that preserve balance.
- `p.57-60` Most “too good to be true” equity curves come from flawed testing; credible pipelines require out-of-sample segments, walk-forward runs, and skepticism toward vendor claims (treat broker/CTA data as hypothetical unless it’s your own account).
- `p.62-66` Walk-forward analysis stitches multiple rolling in-/out-of-sample windows, producing more realistic performance estimates than a single optimized backtest; when history is sparse, fall back to carefully monitored real-time incubation.
- `p.69-70` Apply strict report triage: include commissions/slippage in every test, demand ~$5k–$10k annual net profit per contract, watch profit factor (>1.5 preferred), keep average trade >$50, ensure 30–100 trades per rule, and evaluate Tharp Expectancy (>0.1) to justify a strategy before sizing.

### Pages 71-90
- `p.71` Model slippage realistically—assume 1–2 ticks per round-trip for market/stop orders (even if mixed with limit orders) so optimizers don’t favor hyperactive systems that will implode live.
- `p.72-73` Read equity curves like diagnostics: steady lower-left-to-upper-right slopes with short flat spots and manageable drawdowns are tradable; highly “fuzzy” daily curves signal volatile PnL that complicates sizing and psychology.
- `p.75-83` Monte Carlo analysis quantifies risk better than eyeballing backtests; target <10% annual risk of ruin, <40% median max drawdown, and return/drawdown ratios above 2 to balance reward with inevitable pain.
- `p.80` Underfunded accounts show ruin probabilities exploding even with positive expectancy—size the base capital so the simulation stays inside acceptable risk bands before putting a bot live.
- `p.82` Traders usually tolerate only half the drawdown they believe they can endure (“half of what you think” rule), so bake that haircut into position sizing thresholds.
- `p.86-88` Use a gated research pipeline (idea → feasibility → walk-forward → Monte Carlo → incubation → deployment) and expect 100–200 raw ideas per production-ready strategy; skipping gates just curve-fits junk.
- `p.89-90` Avoid “scenario 3 luck” by insisting each strategy has a logical edge, simple rule set, and gentle optimization rather than randomly combining indicators until something backtests well.

### Pages 91-115
- `p.93-95` Define SMART (and SMARTER) goals for each new system—e.g., target instrument, return, max drawdown, win rate, development timeline—so you can evaluate whether a candidate truly meets mission requirements.
- `p.96` Keep a written “wish list” of softer preferences (markets, holding period, indicator count, overnight risk tolerance) to ensure the final bot fits your operating constraints and psychology.
- `p.97-100` Treat entry, exit, market, timeframe, programming, and data choices as separate design problems; entries matter most for short holds, while exits (stop/target/trailing) actually drive long-run performance and need as much research as entries.
- `p.101` Be wary of “one size fits all” multi-market optimizations—relaxing acceptance criteria or cherry-picking the top markets is just hidden curve fitting; either prove the rule set works everywhere or build per-market strategies intentionally.
- `p.102-104` Long-term bars usually outperform day-trading attempts because costs/randomness dominate lower timeframes; if you do use custom bar sizes or settlements, lock the session definitions and understand exchange settlement vs last trade behaviors.
- `p.106` Learning to program/test strategies yourself avoids leaking IP to contractors and helps you catch backtest engine artifacts before they reach production.
- `p.107-115` Data architecture is a first-class concern: use 10+ years of history where possible, align pit/electronic sessions, choose between raw vs (back-)adjusted continuous contracts carefully, never use ratios on back-adjusted prices, and model FX fills with realistic bid/ask assumptions (often by using market orders plus spread) to prevent phantom fills.

### Pages 116-130
- `p.117-118` Never test a new idea across the entire dataset—it “burns” the data and tempts hidden optimization; instead sample 1–2 random years for early feasibility checks so the remaining history stays untouched for walk-forward runs.
- `p.118-123` Vet entries and exits separately: for entries look at both win rate and average profit, expecting ≥70% of parameter iterations to be positive before continuing; for exits, compare against generic or random entries using MFE/MAE so you know the exit contributes edge.
- `p.122-124` When only 30–70% of limited-test iterations work, tweak once or twice at most; if <30% succeed, try reversing the logic (the “Costanza” test) to see if the opposite rules capture the true edge.
- `p.123-128` Run “monkey tests” by replacing your entry and/or exit with randomized logic tuned to trade count, side mix, and holding time; demand your system beat >90% of random runs when built, and rerun these tests on each 6–12 month live window to detect fading edges before losses pile up.
- `p.129-130` In-depth testing relies on walk-forward analysis; when a rule set has no tunable parameters, treat a single historical pass as the in-depth test and avoid sneaky tweaks afterwards—or consolidate multiple fixed-pattern systems into one parameterized strategy so optimization is transparent.

### Pages 131-150
- `p.131-134` Walk-forward analysis (e.g., 5-year in/1-year out, unanchored) mirrors live trading by optimizing on past windows and applying those parameters to the next slice; optimized backtests will always look better, but walk-forward curves predict future flatness or drawdowns far more accurately.
- `p.136-140` Choose walk-forward settings before testing: size in-periods so each input sees 25–50 trades, keep out-periods 10–50% of in-length, and pick a fitness metric (net profit, linearity, return/drawdown) aligned with your objectives while remembering some metrics (e.g., drawdown) aren’t additive when stitching periods.
- `p.140` Don’t chase better results by re-running different in/out combos on the same data; if you must compare, reserve a final holdout window to validate the selected pair so you’re not double-dipping.
- `p.141-142` Build a “walk-forward history” strategy whose parameters change by date so you can evaluate trades that span optimization windows and confirm no artifacts occur when rules shift mid-position.
- `p.133-146` After walk-forward success, rerun Monte Carlo and require return/drawdown ratios ~2+; then incubate the strategy 3–6 months (paper or tiny size) to bleed off emotional bias, catch implementation mistakes, and ensure fills/exit assumptions (e.g., limits, exotic bars) hold in real time.
- `p.147-150` Run your research like a system factory and diversify across uncorrelated strategies: multiple models reduce single-system failure risk, improve fills by keeping position sizes smaller, and smooth equity; validate diversification by checking equity-curve R², max drawdown, and Monte Carlo return/drawdown improvements for combined systems.

### Pages 151-160
- `p.151` Diversification lets you relax per-strategy hurdles; combining many “decent” but uncorrelated systems often beats chasing a single “holy grail,” because the ensemble lifts return/drawdown.
- `p.153-155` There is no universal optimal position-sizing model; risk and reward always travel together, and you can’t rescue a losing system (or guarantee a winner) just by tweaking bet sizing.
- `p.155-157` Ignore “trade 100 contracts” fantasies—capital, margin, and psychology make exponential scaling unrealistic; ramp size slowly so each increase feels normal.
- `p.156-158` Martingale-style approaches can win in the short term but guarantee ruin eventually; instead start live trading with minimum size, let the bot prove itself, and only scale using results-funded capital.
- `p.158-160` Use Monte Carlo outputs to pick fixed-fraction betting levels (per system and across the portfolio) that maximize return/drawdown while respecting max drawdown and risk-of-ruin caps; each system may get a different `x` fraction based on its own distribution.

### Pages 161-195
- `p.161-166` Treat strategy research like an engineering project: use consistent naming, record detailed entry/exit descriptions, log every testing phase (limited, walk-forward, Monte Carlo, incubation, diversification, sizing), and maintain an idea backlog so you never run out of hypotheses.
- `p.169-175` The euro day/night case study shows how to pair complementary strategies (night session mean reversion with high win rate, day session trend capture) under a SMART goal, test limited subsets first (2009 sample), and only move to walk-forward once entries/exits show ≥75% profitable optimizations.
- `p.176-185` Combine daily PnL streams before Monte Carlo to respect trade sequencing, and leverage diversification to lift return/drawdown from ~5.5 to 6.6; validate incubation via t-tests, histograms, and equity-curve overlays to ensure real-time behavior matches walk-forward.
- `p.186-188` Evaluate whether single-contract losses make a system impractical (e.g., $3k stop requires $35k account for acceptable drawdown) and use Monte Carlo to understand how often you’ll be profitable weekly/monthly/quarterly so expectations stay realistic.
- `p.188-189` This euro system relies on only a handful of large winners per year; missing even one signal can break the edge, so automate execution and be psychologically ready for long flat periods punctuated by big gains.
- `p.191-195` Before going live, write explicit quit points (e.g., average of 1.5× worst historical drawdown and 95th percentile Monte Carlo drawdown ≈ $5k/contract), fund the account with margin plus drawdown + cushion, start with one contract, and let profits—not hope—drive future position size increases.

### Pages 196-240
- `p.196-199` Use Monte Carlo to test various fixed-fraction bets and visualize the trade-off between median return, drawdown, and risk of ruin; pick a fraction (`ff≈0.175` in the case study) that meets your personal limits rather than blindly following standard 2% rules.
- `p.200-205` Trading psychology still matters in automation: define when to start (e.g., immediately after incubation or waiting for a pullback), decide if you’ll enter mid-trade, and pre-write quitting conditions so stress doesn’t force impulsive exits.
- `p.206-208` Discipline equals taking every signal exactly as tested; cherry-picking entries, jumping the gun, or deviating after a string of losses turns a researched strategy into random gambling.
- `p.209-215` Operational readiness matters: split strategies across brokers/accounts for bookkeeping and counterparty risk, understand your automation stack (attended vs unattended, VPS, backup connectivity), and know how you’ll roll futures without introducing phantom PnL.
- `p.217-230` Build dashboards (equity/drawdown curves, monthly summary sheets, daily performance bands) and Monte Carlo-derived expectation envelopes so you can quickly spot when live performance drifts beyond historical probabilities.
- `p.231-240` During live trading, document weekly reviews, compare actual vs expected PnL, and investigate variances (slippage assumptions, missed fills, automation bugs) before abandoning a system that’s still within its pre-defined risk envelope.

### Pages 241-260
- `p.243-245` Real-time logs show diversification across day/night components eventually paid off; patience plus rigorous reviews help you avoid killing a system before its fat-tailed winners arrive.
- `p.235-238` Plan semiannual “next best alternative” reviews so capital only stays with strategies that still beat your pipeline; even underperformers should get a predetermined evaluation window before being replaced.
- `p.236-240` Automation mishaps (stale limit orders, platform glitches) can erase weeks of alpha; implement safeguards that cancel orders after fills, confirm positions align with code, and treat every anomaly as a lesson with equal weight to “lucky” mistakes.
- `p.235-250` Cautionary tales remind us to ignore demo-only heroes, gurus who don’t trade, clairvoyant “predictors,” and overcomplicated snake oil—focus on verifiable edges, live track records, and simple, testable logic.
- `p.244-245` Closing guidance: psychology and position sizing can’t rescue a losing model; expect to test 100–200 ideas to find one tradable edge, and keep iterating because no strategy lasts forever.

### Pages 261-284
- `p.261-265` Appendix A provides TradeStation Easy Language templates for the baseline strategy and the three “monkey” variants (random entry, random exit, fully random) so you can replicate the randomness tests described earlier without rewriting code from scratch.
