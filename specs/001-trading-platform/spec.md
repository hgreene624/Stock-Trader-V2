# Feature Specification: Multi-Model Algorithmic Trading Platform

**Feature Branch**: `001-trading-platform`
**Created**: 2025-11-16
**Status**: Draft
**Input**: User description: "Create a multi-model, multi-asset algorithmic trading platform based on the master system specification in setup_files/master_system_spec_v1.0.md. This platform should support: Core Architecture with multiple strategy models, multi-asset support (equities via Alpaca, crypto via Binance/Kraken), primary timeframe of 4-hour (H4) bars with daily data as slow features, and regime-aware portfolio management with risk controls."

## Clarifications

### Session 2025-11-16

- Q: How should the initial portfolio NAV be specified for backtest and live/paper trading modes? → A: Separate NAV config per mode (backtest_initial_nav, paper mode uses broker account balance, live mode uses broker account balance)
- Q: What VIX threshold values should distinguish between LOW/NORMAL/HIGH volatility regimes? → A: VIX: LOW <15, NORMAL 15-25, HIGH >25
- Q: How should the system alert operators when critical failures occur in paper/live trading modes? → A: Log to errors.log only (operators monitor via external tools)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backtest Single Strategy Model (Priority: P1)

As a quantitative researcher, I want to backtest a single trading strategy using historical data so that I can validate its performance before risking capital.

**Why this priority**: This is the foundation of the platform. Without the ability to backtest a single model with historical data, no other functionality can be validated. This delivers immediate value by allowing researchers to test strategy ideas.

**Independent Test**: Can be fully tested by configuring one model (e.g., EquityTrendModel_v1) with a YAML file, running it against 2+ years of historical H4 data, and verifying that it produces an equity curve, trade log, and performance metrics without look-ahead bias.

**Acceptance Scenarios**:

1. **Given** historical H4 data is available for SPY and QQQ from 2020-2025, **When** I configure EquityTrendModel_v1 with specific parameters in YAML and run a backtest, **Then** the system produces an equity curve, trade log, and performance metrics (Sharpe, CAGR, max drawdown, win rate)
2. **Given** a backtest configuration with a specific start/end date range, **When** I execute the backtest, **Then** the system only uses data within that range and enforces no look-ahead bias (future data not visible at decision time)
3. **Given** a completed backtest run, **When** I review the results, **Then** all trades, portfolio snapshots, and model decisions are logged with timestamps and can be reproduced by re-running with the same config

---

### User Story 2 - Run Multi-Model Portfolio (Priority: P1)

As a portfolio manager, I want to run multiple strategy models simultaneously with independent budgets so that I can diversify risk and combine complementary strategies.

**Why this priority**: This is a core differentiator of the platform. Multi-model coordination is essential for achieving the platform's goal of combining trend, mean-reversion, and momentum strategies.

**Independent Test**: Can be fully tested by configuring 3 models (EquityTrendModel_v1, IndexMeanReversionModel_v1, CryptoMomentumModel_v1) with different budgets (e.g., 60%, 25%, 15%), running a backtest, and verifying that the Portfolio Engine correctly aggregates exposures and respects individual model budgets.

**Acceptance Scenarios**:

1. **Given** 3 models configured with budgets of 60%, 25%, and 15% respectively, **When** all models signal long positions in the same asset (e.g., SPY), **Then** the Portfolio Engine aggregates the exposures correctly (e.g., if each wants 100% of their budget in SPY, total exposure = 60% + 25% + 15% = 100% of NAV)
2. **Given** conflicting signals from different models (one wants long, another wants flat), **When** the Portfolio Engine aggregates, **Then** exposures are netted appropriately and attribution to each model is maintained
3. **Given** a multi-model portfolio with defined budgets, **When** models generate target weights, **Then** the system converts model-relative weights to NAV-relative weights correctly before aggregation

---

### User Story 3 - Apply Risk Controls (Priority: P1)

As a risk manager, I want the system to enforce hard limits on exposures, leverage, and drawdown so that no single strategy or combination of strategies can exceed risk tolerances.

**Why this priority**: Risk controls are non-negotiable. Without them, the platform could expose capital to unacceptable losses. This is a foundational safety feature that must work from day one.

**Independent Test**: Can be fully tested by configuring risk limits (e.g., max 40% per asset, max 20% crypto, max 1.2x leverage, 15% max drawdown), running backtests with models that attempt to exceed these limits, and verifying that the Risk Engine scales down or halts as configured.

**Acceptance Scenarios**:

1. **Given** a risk limit of 40% NAV per asset, **When** models collectively want to allocate 60% to SPY, **Then** the Risk Engine scales the SPY position down to 40% before execution
2. **Given** a max drawdown limit of 15%, **When** the portfolio experiences a 15% peak-to-trough drawdown, **Then** the Risk Engine automatically reduces all exposures by 50% or enters capital preservation mode (no new entries)
3. **Given** a leverage limit of 1.2x, **When** models want gross exposure of 1.5x NAV, **Then** the Risk Engine proportionally scales all positions to achieve 1.2x gross exposure
4. **Given** an asset class limit (crypto ≤ 20% NAV), **When** crypto models want 30% exposure, **Then** the Risk Engine caps total crypto exposure at 20%

---

### User Story 4 - Classify Market Regimes (Priority: P2)

As a systematic trader, I want the system to automatically classify market conditions (equity trend, volatility, crypto sentiment, macro environment) so that model budgets and risk tolerances can adapt to changing markets.

**Why this priority**: Regime awareness significantly improves robustness by avoiding one-size-fits-all strategies. While not essential for initial backtest functionality, it's critical for achieving production-grade performance.

**Independent Test**: Can be fully tested by feeding historical daily data for SPY, VIX, BTC, and macro indicators into the Regime Engine, verifying it classifies regimes correctly (e.g., BULL when SPY > 200D MA and momentum positive), and confirming that Portfolio/Risk Engines adjust budgets based on regime state.

**Acceptance Scenarios**:

1. **Given** daily SPY price above 200D MA with positive 6-12M momentum, **When** the Regime Engine updates, **Then** equity_regime is classified as BULL
2. **Given** BTC below 200D MA or negative 60D momentum, **When** the Regime Engine updates, **Then** crypto_regime is classified as RISK_OFF
3. **Given** equity_regime transitions from BULL to BEAR, **When** the Portfolio Engine rebalances, **Then** equity model budgets are automatically reduced per regime_budgets config (e.g., EquityTrend from 60% to 20%)
4. **Given** vol_regime is HIGH (VIX above threshold), **When** risk calculations occur, **Then** position sizes are reduced or risk limits are tightened

---

### User Story 5 - Optimize Strategy Parameters (Priority: P2)

As a quant researcher, I want to systematically search parameter spaces using grid/random search and evolutionary algorithms so that I can find robust parameter sets that maximize a balanced performance score.

**Why this priority**: Parameter optimization is essential for moving from initial strategy ideas to production-ready models. It's a key value-add of the platform but can be built after core backtest infrastructure exists.

**Independent Test**: Can be fully tested by defining a parameter grid in a YAML experiment file (e.g., fast_ma: [20, 30, 50], slow_ma: [100, 150, 200]), running the optimizer, and verifying it tests all combinations, ranks by Balanced Performance Score (0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD), and logs results to the database.

**Acceptance Scenarios**:

1. **Given** a grid search config with 3 values for fast_ma and 3 for slow_ma (9 total combinations), **When** I run the optimizer, **Then** the system runs 9 backtests and stores results with all parameter values and metrics
2. **Given** completed grid search results ranked by BPS, **When** I request evolutionary algorithm refinement, **Then** the top N parameter sets are used as seeds for crossover and mutation to explore nearby parameter space
3. **Given** multiple optimization runs, **When** I query the results database, **Then** I can retrieve and compare all runs by experiment name, date, model version, parameters, and performance metrics

---

### User Story 6 - Download and Update Historical Data (Priority: P2)

As a researcher, I want to download and periodically update historical price data for all assets in my universe so that backtests use current data.

**Why this priority**: Data is the foundation. Without a clear process to acquire and refresh data, the system cannot function. Essential for making the platform self-sufficient.

**Independent Test**: Can be tested by running a data download command for SPY (H4 + daily) and BTC (H4 + daily), verifying Parquet files are created in correct directory structure, and running an update command to append new bars.

**Acceptance Scenarios**:

1. **Given** no existing data, **When** I run data download for SPY with date range 2020-2025, **Then** SPY_h4.parquet and SPY_daily.parquet are created with complete OHLCV data
2. **Given** existing SPY data through 2024-12-31, **When** I run data update command, **Then** new bars from 2025-01-01 to present are appended without duplicates
3. **Given** data download fails for a symbol (API error), **When** the command completes, **Then** the error is logged and other symbols continue downloading
4. **Given** downloaded data, **When** validation runs, **Then** gaps larger than configured threshold (e.g., 5 consecutive missing bars) are detected and reported

---

### User Story 7 - Manage Model Lifecycle Progression (Priority: P2)

As a strategy director, I want to systematically promote models through lifecycle stages (research → candidate → paper → live) with clear criteria and tracking so that only validated strategies reach live trading.

**Why this priority**: Essential for production governance. Ensures systematic validation before risking capital. Without this, there's no controlled path from research to live trading.

**Independent Test**: Can be tested by promoting a model from research through all stages, verifying that each stage transition is tracked in results DB and config, and confirming that paper/live runners only execute models with appropriate lifecycle stage.

**Acceptance Scenarios**:

1. **Given** a model in research stage with successful backtest results, **When** I promote it to candidate status, **Then** the model's lifecycle_stage is updated in config and results DB with timestamp and operator
2. **Given** a candidate model deployed to paper trading, **When** it meets performance criteria over 30+ days, **When** I promote to live status, **Then** only live runner can execute this model with real capital
3. **Given** a live model experiencing degraded performance, **When** I demote it to paper or research, **Then** live runner stops executing and model reverts to lower lifecycle stage
4. **Given** a paper trading runner starting up, **When** it loads models from config, **Then** it only activates models with lifecycle_stage = candidate or paper (skips research and live)

---

### User Story 8 - Paper Trade Strategies (Priority: P3)

As a strategy developer, I want to run validated models in paper trading mode using live market data but simulated execution so that I can verify real-world behavior before deploying capital.

**Why this priority**: Paper trading is the bridge between research and live trading. Essential for production deployment but not needed until core models and backtesting are mature.

**Independent Test**: Can be fully tested by configuring a model for paper mode, connecting to broker paper endpoints (Alpaca paper, Binance testnet), running the strategy for several days, and verifying that orders are submitted and filled using live prices without real capital movement.

**Acceptance Scenarios**:

1. **Given** a model configured for paper trading mode, **When** the system runs on H4 bar close, **Then** it fetches current market data, makes decisions, and submits paper orders to Alpaca/Binance paper endpoints
2. **Given** paper orders submitted, **When** fills occur, **Then** positions and NAV are updated in the system and match broker paper account state
3. **Given** paper trading results over 30+ days, **When** I compare to backtest expectations, **Then** performance is within reasonable bounds (accounting for slippage/fees differences)

---

### User Story 9 - Deploy Live Trading (Priority: P3)

As a fund manager, I want to deploy validated, paper-tested models to live trading with real capital while maintaining full risk controls and monitoring so that I can generate returns from systematic strategies.

**Why this priority**: This is the ultimate goal but must come last after all validation steps. Requires maximum maturity in all components.

**Independent Test**: Can be fully tested by promoting a paper-tested model to live mode, configuring live broker credentials, activating the kill switch mechanism, and verifying that real orders are placed, filled, and reconciled with actual positions and P&L.

**Acceptance Scenarios**:

1. **Given** a model promoted to live trading status, **When** the live runner executes on H4 bar close, **Then** real orders are submitted to Alpaca/Binance live APIs and capital is deployed
2. **Given** live trading is active, **When** I trigger the kill switch (via config or command), **Then** all new order submissions halt immediately and existing positions can be managed manually
3. **Given** live fills occur, **When** the system reconciles, **Then** internal positions and broker positions match exactly (within rounding tolerance)
4. **Given** a global drawdown limit breach in live mode, **When** the Risk Engine detects it, **Then** exposure is automatically reduced by configured factor or trading halts entirely

---

### Edge Cases

- **What happens when data is missing for a symbol at decision time?** System applies forward-fill by default or follows model-specific policy configured in YAML. If no valid data exists, asset is skipped for that decision cycle.
- **How does system handle broker API failures or network outages during live trading?** Execution adapters implement retry logic with exponential backoff. If retries fail, system logs error to errors.log and does not assume order was filled. Operators are responsible for monitoring errors.log via external tools.
- **What if regime classification inputs are delayed or unavailable?** Regime Engine uses last known valid regime state and logs a warning. If stale beyond configured threshold (e.g., 48 hours), enters conservative default regime (e.g., NEUTRAL/NORMAL).
- **How are corporate actions (splits, dividends) handled in backtests?** Data pipeline uses adjusted prices for backtests. Dividends are assumed reinvested. Real-time data for paper/live uses unadjusted prices with explicit corporate action handling.
- **What if two models want opposite positions in the same asset?** Portfolio Engine nets the exposures at the portfolio level (long + short = net exposure) and maintains attribution to each model.
- **How does system handle min order size constraints from brokers?** Execution Engine validates all orders against broker constraints before submission. If target delta is below min size, order is not placed and reason is logged.
- **What happens if a model version is updated mid-backtest?** Not allowed. Backtest runs are locked to specific model versions defined in config. New version requires new backtest run.
- **How does system handle timezone differences between Alpaca (US/Eastern) and Binance/Kraken (UTC)?** All timestamps are normalized to UTC internally. Equity data from Alpaca is converted from ET to UTC. H4 bar boundaries are defined in UTC (00:00, 04:00, 08:00, 12:00, 16:00, 20:00). Market hour filtering is applied per exchange (equities only trade during US market hours 9:30-16:00 ET; crypto 24/7).

## Requirements *(mandatory)*

### Functional Requirements

#### Data & Feature Layer

- **FR-001**: System MUST store all historical price data (OHLCV) in Parquet format with one file per asset per timeframe (e.g., SPY_h4.parquet, SPY_daily.parquet)
- **FR-002**: System MUST provide a centralized feature pipeline that computes indicators (moving averages, RSI, ATR, Bollinger Bands, returns) from raw OHLCV data
- **FR-003**: System MUST enforce strict no-look-ahead bias: at any decision timestamp T, only data with timestamp ≤ T is accessible to models
- **FR-004**: System MUST align daily features to H4 timestamps such that the daily feature value at H4 timestamp T uses only daily data available at or before T
- **FR-005**: System MUST handle missing data via forward-fill or model-configurable policies and log when data is missing
- **FR-006**: System MUST provide data download capability that fetches historical OHLCV data from configured sources (Yahoo Finance for equities, Binance/Kraken for crypto, FRED for macro)
- **FR-007**: System MUST store downloaded data in Parquet format with one file per asset per timeframe (e.g., SPY_h4.parquet, SPY_daily.parquet) in the correct directory structure (data/equities/, data/crypto/, data/macro/)
- **FR-008**: System MUST support incremental data updates that append new bars to existing Parquet files without duplicates
- **FR-009**: System MUST validate downloaded data for completeness (no gaps > configured threshold, e.g., 5 consecutive missing bars) and correctness (OHLC relationships: High ≥ Close ≥ Low, High ≥ Open ≥ Low, positive volume)
- **FR-010**: System MUST normalize all timestamps to UTC internally regardless of data source timezone (Alpaca uses US/Eastern, Binance/Kraken use UTC)
- **FR-011**: System MUST define H4 bar boundaries at UTC midnight and 4-hour intervals (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)
- **FR-012**: System MUST apply market hour filtering per asset class (equities only during US market hours 9:30-16:00 ET converted to UTC; crypto 24/7)

#### Model Layer

- **FR-013**: System MUST support pluggable model architecture where each model receives Context (market state, features, regime, budget) and outputs target weight vector
- **FR-014**: System MUST implement EquityTrendModel_v1 that uses daily 200D MA and momentum to generate long-only target weights for SPY/QQQ
- **FR-015**: System MUST implement IndexMeanReversionModel_v1 that uses H4 RSI and Bollinger Bands to generate short-duration long positions in SPY/QQQ
- **FR-016**: System MUST implement CryptoMomentumModel_v1 that uses 30-60D momentum to generate long-only target weights in BTC/ETH with regime gating
- **FR-017**: Each model MUST be versioned using semantic versioning (MAJOR.MINOR.PATCH) and version tracked in all results
- **FR-018**: Models MUST express target weights relative to their assigned budget fraction (0-1) and MUST NOT directly access broker APIs or know about other models. Models MAY optionally output per-asset hints including confidence scores (0-1), urgency flags (high/normal/low), and expected holding horizon (hours/days) to inform portfolio construction

#### Model Lifecycle Management

- **FR-019**: System MUST track model lifecycle stage (research/candidate/paper/live) in both YAML config and results database
- **FR-020**: System MUST restrict paper trading runner to execute only models with lifecycle_stage = candidate or paper
- **FR-021**: System MUST restrict live trading runner to execute only models with lifecycle_stage = live
- **FR-022**: System MUST log all model lifecycle transitions (promotions/demotions) with timestamp, operator identifier, and reason for change

#### Portfolio Engine

- **FR-023**: System MUST convert each model's budget-relative target weights to NAV-relative weights by multiplying by the model's budget fraction
- **FR-024**: System MUST aggregate NAV-relative target weights across all active models per asset (summing contributions)
- **FR-025**: System MUST maintain attribution mapping that tracks which portion of each asset's exposure came from which model
- **FR-026**: System MUST generate execution instructions (deltas) by comparing target portfolio weights to current weights
- **FR-027**: System MUST coordinate with Risk Engine to apply global constraints before finalizing target portfolio

#### Risk Engine

- **FR-028**: System MUST enforce per-asset exposure caps (e.g., max 40% NAV per asset) by scaling down positions that exceed limits
- **FR-029**: System MUST enforce per-asset-class caps (e.g., crypto ≤ 20% NAV total) by scaling down all assets in the class proportionally
- **FR-030**: System MUST enforce gross leverage limit (e.g., max 1.2x NAV) by scaling all positions proportionally if exceeded
- **FR-031**: System MUST monitor peak-to-trough drawdown and trigger automatic de-risking (e.g., 50% exposure reduction) or halt when threshold (e.g., 15%) is breached
- **FR-032**: System MUST support regime-aware risk scaling where budgets and limits adjust based on regime state (configured in YAML)

#### Regime Engine

- **FR-033**: System MUST classify equity regime (BULL/BEAR/NEUTRAL) based on SPY price vs 200D MA and 6-12M momentum
- **FR-034**: System MUST classify volatility regime as: LOW when VIX <15, NORMAL when VIX 15-25, HIGH when VIX >25 (or equivalent thresholds for realized volatility if VIX unavailable)
- **FR-035**: System MUST classify crypto regime (RISK_ON/RISK_OFF) based on BTC price vs 200D MA and 60D momentum
- **FR-036**: System MUST classify lightweight macro regime (EXPANSION/SLOWDOWN/RECESSION) based on PMI and yield curve slope indicators
- **FR-037**: System MUST provide current regime state as structured output (JSON-like) to Portfolio Engine, Risk Engine, and models

#### Execution / Backtest Engine

- **FR-038**: System MUST provide unified execution interface (submit_target_weights, get_positions, get_cash, get_nav) that works identically in backtest, paper, and live modes
- **FR-039**: System MUST implement backtest execution using bar-based OHLC simulation with configurable order timing (bar close or bar open)
- **FR-040**: System MUST apply configurable slippage and fee models per asset class in backtests (e.g., X bps per trade)
- **FR-041**: System MUST implement broker adapter for Alpaca (equities) supporting market/limit orders in paper and live modes
- **FR-042**: System MUST implement broker adapter for Binance or Kraken (crypto) supporting spot trading with proper symbol mapping and precision handling
- **FR-043**: System MUST validate all orders against broker constraints (min order size, trading hours, precision) before submission
- **FR-044**: System MUST reconcile internal positions with broker positions after fills and log discrepancies

#### Optimization Layer

- **FR-045**: System MUST support parameter optimization via grid search where parameter grids are defined in YAML experiment files
- **FR-046**: System MUST support parameter optimization via random search where parameter distributions are defined in YAML
- **FR-047**: System MUST compute Balanced Performance Score (BPS) = 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDrawdown for each backtest run
- **FR-048**: System MUST support evolutionary algorithm (EA) refinement where top-performing parameter sets (by BPS) are used as seeds for selection, crossover, and mutation
- **FR-049**: System MUST log all optimization run metadata (experiment name, date, model version, parameters tested, BPS scores) to results database

#### Configuration & Deployment

- **FR-050**: System MUST load all configuration (model selection, parameters, budgets, risk limits, regime thresholds) from YAML files
- **FR-051**: System MUST support separate NAV configuration per execution mode: backtest mode uses backtest_initial_nav from config (e.g., $100,000 or $1,000,000 for standardized comparison), while paper and live modes query and use actual broker account balance as NAV
- **FR-052**: System MUST support experiment YAML files that override base config fields using merge semantics
- **FR-053**: System MUST support regime-based budget overrides where model budgets change automatically based on current regime state. Configuration uses regime_budgets section in YAML with keys for each regime combination (e.g., equity_bull, equity_bear) and values specifying model budget fractions. Example: When equity_regime transitions from BULL to BEAR, equity_trend budget automatically reduces from 0.7 to 0.2 as defined in regime_budgets.equity_bear configuration
- **FR-054**: System MUST provide a kill switch mechanism (via config flag or external command) that immediately halts all new order submissions in paper/live modes
- **FR-055**: System MUST prevent overlapping access to the same broker account from live and backtest/research processes

#### Logging & Reporting

- **FR-056**: System MUST log all events using structured JSON format with fixed fields (timestamp, component, level, message, context)
- **FR-057**: System MUST maintain separate log streams for trades (trades.log), orders (orders.log), performance snapshots (performance.log), and errors (errors.log)
- **FR-058**: System MUST store all backtest results in SQLite or DuckDB database including experiment metadata, portfolio metrics, per-model metrics, and references to generated plots
- **FR-059**: System MUST generate equity curve, drawdown curve, per-model return series, and turnover statistics for each backtest run
- **FR-060**: System MUST ensure all experiments are fully reproducible: given same config YAML and same historical data, re-running produces identical results
- **FR-061**: System MUST generate per-model performance reports showing individual model equity curves, return series, Sharpe, CAGR, drawdown, and turnover
- **FR-062**: System MUST support attribution queries that show for any given portfolio position: which models contributed, their individual target weights, and final aggregated weight after risk constraints
- **FR-063**: System MUST generate regime alignment reports showing portfolio and per-model performance broken down by regime periods (e.g., returns during BULL vs BEAR equity regimes)
- **FR-064**: System MUST support querying results database to compare multiple experiment runs by experiment name, date range, or model version
- **FR-065**: System MUST generate comparison reports showing side-by-side metrics (Sharpe, CAGR, MaxDD, BPS) for selected experiments

### Key Entities

- **Asset**: Represents a tradeable instrument (e.g., SPY, BTC). Attributes: symbol, asset_class (equity/crypto), data_source, timeframe availability, broker constraints (min order size, precision)
- **Model**: Represents a strategy/alpha engine (e.g., EquityTrendModel_v1.0.0). Attributes: name, version, universe (list of assets), budget_fraction, parameters, lifecycle_stage (research/candidate/paper/live)
- **Context**: Market state snapshot provided to models at each decision cycle. Attributes: timestamp, asset features (current bar + history window), regime state, model budget (fraction and dollar value), current model-attributed exposures
- **Portfolio State**: Current positions and cash. Attributes: timestamp, per-asset positions (shares/coins), per-asset market values, cash, NAV, per-model attribution
- **Regime State**: Market condition classification. Attributes: timestamp, equity_regime, vol_regime, crypto_regime, macro_regime (each with enum values)
- **Trade**: Record of an executed order. Attributes: timestamp, symbol, side (buy/sell), quantity, price, fees, model_attribution (which model generated this trade)
- **Backtest Result**: Summary of a backtest run. Attributes: experiment_id, config_snapshot, start_date, end_date, model_versions, performance_metrics (Sharpe, CAGR, MaxDD, WinRate, BPS), equity_curve_path, log_file_path
- **Risk Limit**: Configuration for risk constraints. Attributes: limit_type (per_asset/asset_class/leverage/drawdown), threshold, scaling_action (scale_down/halt)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Researchers can backtest a single model strategy against 5 years of H4 historical data and receive results (equity curve, metrics, trade log) in under 5 minutes
- **SC-002**: System enforces no-look-ahead bias such that 100% of backtest trades use only data available at decision time (verified by manual inspection and automated tests)
- **SC-003**: Multi-model portfolios correctly aggregate exposures such that when 3 models with budgets 60%, 25%, 15% all target 100% allocation to the same asset, total exposure equals 100% NAV (not 100% × 3)
- **SC-004**: Risk Engine prevents portfolio from exceeding any configured hard limit (per-asset 40%, crypto class 20%, leverage 1.2x, drawdown 15%) in 100% of backtest scenarios where limits are tested
- **SC-005**: Regime Engine correctly classifies market conditions with >90% agreement with manual classification on historical data (e.g., SPY > 200D MA with positive momentum correctly flagged as BULL)
- **SC-006**: Parameter optimization using grid search of 100 combinations completes in under 10 minutes (1 hour of compute with parallelization)
- **SC-007**: Paper trading mode successfully submits and fills simulated orders using live market data with <5 second latency from H4 bar close to order submission
- **SC-008**: All backtest experiments are reproducible: re-running same config + data produces identical equity curves and trade logs (bit-for-bit identical results or within floating-point tolerance)
- **SC-009**: Live trading mode executes the kill switch (halt all new orders) in <1 second from command issuance
- **SC-010**: System logs 100% of trades, orders, and portfolio snapshots in structured JSON format enabling full audit trail and debugging
- **SC-011**: Attribution tracking maintains 100% accuracy: sum of all model contributions to an asset position equals final portfolio position (within floating-point tolerance of 1e-6)
- **SC-012**: Per-model performance reports can be generated for any completed backtest run in under 30 seconds

## Assumptions

- Historical data sources (Yahoo Finance, Binance/Kraken APIs, FRED) remain accessible and provide sufficient data quality for H4 and daily timeframes
- Initial deployment will use local Python environment for research/backtest and cloud VPS for paper/live trading
- Broker APIs (Alpaca, Binance, Kraken) maintain stable endpoints and sufficient rate limits for H4 frequency trading
- Users have basic familiarity with YAML configuration and command-line tools
- Initial asset universe is limited to SPY, QQQ (equities) and BTC, ETH (crypto); expansion to more assets is future work
- Model complexity in v1 is limited to technical indicators and regime logic; ML-based models are out of scope for v1
- Performance reporting focuses on standard metrics (Sharpe, CAGR, MaxDD, WinRate); advanced analytics (Greeks, factor attribution) are future enhancements
- Operators are responsible for monitoring errors.log in paper/live environments using external tools (e.g., log aggregators, file watchers); v1 does not include built-in email/SMS/webhook alerting

## Out of Scope

- Machine learning or deep learning based models (v1 uses only technical indicators and rule-based logic)
- Real-time tick data or sub-H4 timeframes (e.g., 1-minute bars)
- Options, futures, or margin trading (v1 is spot-only for equities and crypto)
- Multi-account or multi-broker aggregation (v1 assumes one Alpaca account and one crypto exchange account)
- Web-based UI or dashboard (v1 is CLI and config-file driven)
- Advanced order types beyond market and limit (e.g., stop-loss orders, trailing stops)
- Social/copy trading features
- Tax reporting or compliance integrations
- Mobile app or notifications (monitoring is manual or via log analysis)

## Dependencies

- **External APIs**: Yahoo Finance (or equivalent) for equity historical data, Binance/Kraken public APIs for crypto historical data, FRED for macro data
- **Broker APIs**: Alpaca for equity trading (paper and live), Binance or Kraken for crypto spot trading
- **Data Storage**: Local filesystem with sufficient space for Parquet files (estimated ~1-10 GB for 5 years of H4 data across 10 assets)
- **Results Database**: SQLite or DuckDB (bundled, no external server required)
- **Configuration**: Project constitution at `.specify/constitution.md` defines architectural principles and constraints
- **Deployment Environment**: Python 3.9+ with required packages (pandas, numpy, PyYAML, pyarrow for Parquet, broker SDKs)

## Notes

- This specification intentionally avoids implementation details (specific Python libraries, class names, API endpoints) to focus on WHAT the system must do, not HOW
- Model logic descriptions (e.g., "use 200D MA and momentum") are conceptual and will be refined during planning phase
- All configuration-driven behavior (budgets, risk limits, regime thresholds) must be modifiable via YAML without code changes
- The platform is designed for progression: research (backtest only) → paper (simulated execution) → live (real capital), with increasing maturity requirements at each stage
- Semantic versioning of models is critical for reproducibility and auditability, especially when transitioning from research to live trading
- **Overnight positions**: The system allows positions to be held overnight by default. No automatic end-of-day flattening or special overnight risk reduction in v1. Models decide holding periods via their logic and configured timeframes
