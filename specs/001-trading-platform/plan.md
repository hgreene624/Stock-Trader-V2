# Implementation Plan: Multi-Model Algorithmic Trading Platform

**Branch**: `001-trading-platform` | **Date**: 2025-11-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-trading-platform/spec.md`

## Summary

Build a multi-model, multi-asset algorithmic trading platform that combines multiple strategy models (equity trend, index mean-reversion, crypto momentum) with regime-aware portfolio management and risk controls. The system supports research, backtesting, paper trading, and live trading modes using a unified execution abstraction. Core differentiators: (1) multi-model coordination with attribution tracking, (2) regime-aware budget allocation, (3) no-look-ahead bias enforcement, (4) progression from research to live with model lifecycle management.

**Technical Approach**: Clean architecture with Python 3.9+, Parquet for data storage, YAML for configuration, and structured JSON logging. Primary decision frequency is H4 (4-hour) bars with daily data as slow features. Broker integration via adapters (Alpaca for equities, Binance/Kraken for crypto). Optimization using hybrid grid/random search + evolutionary algorithms targeting Balanced Performance Score.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**:
- Data: pandas, pyarrow (Parquet), yfinance (equity data), ccxt or exchange SDKs (crypto data)
- Numerics: numpy, scipy (for indicators, optimization)
- Config: PyYAML, pydantic (validation)
- Database: DuckDB or SQLite3
- Broker APIs: alpaca-py (Alpaca), python-binance/ccxt (crypto)
- Testing: pytest, pytest-cov

**Storage**:
- Historical data: Parquet files (asset-per-file per timeframe, ~1-10 GB for 5 years)
- Results: SQLite/DuckDB (~100MB-1GB for extensive optimization runs)
- Logs: JSON lines files (trades.log, orders.log, performance.log, errors.log)

**Testing**: pytest with unit tests (core logic), integration tests (end-to-end backtests), contract tests (broker adapters)

**Target Platform**:
- Research/backtest: Local (macOS/Linux, Python 3.9+ venv)
- Paper/live: Cloud VPS (Ubuntu 22.04 LTS, persistent environment, stable network)

**Project Type**: Single project (CLI-driven, no web/mobile UI in v1)

**Performance Goals**:
- H4 bar processing: <1 second for 5-10 asset universe
- Feature computation: vectorized operations on 5 years of H4 data
- Backtest execution: 5 years of H4 data in <5 minutes
- Parameter optimization: 100 grid combinations in <10 minutes (parallelized)

**Constraints**:
- No look-ahead bias (strictly enforced via time alignment)
- Risk limits (per-asset 40% NAV, crypto class 20%, leverage 1.2x, drawdown 15%)
- Reproducibility (bit-for-bit identical backtest results from same config + data)
- Paper/live order submission latency: <5 seconds from H4 bar close

**Scale/Scope**:
- Initial universe: 4 assets (SPY, QQQ, BTC, ETH)
- Models: 3 v1 strategies
- Timeframes: H4 primary (6 bars/day), daily secondary
- Historical data: 5+ years per asset
- Optimization runs: 100-1000 parameter combinations per experiment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Alignment with Fundamental Principles

| Principle | Status | Implementation Plan |
|-----------|--------|---------------------|
| 1. Modularity & Separation of Concerns | ✅ PASS | Clean architecture: `data/`, `models/`, `engines/`, `backtest/`, `live/` with clear interfaces. Models receive Context, never access data directly |
| 2. Configuration-Driven Architecture | ✅ PASS | All behavior (model params, budgets, risk limits, regime thresholds) in YAML. Experiment overrides via YAML merge. Zero hardcoded magic numbers |
| 3. No Look-Ahead Bias | ✅ PASS | Time alignment enforced in data pipeline. At timestamp T, only data ≤ T accessible. Daily features aligned to H4 bars. Forward-fill for missing data |
| 4. Risk-First Design | ✅ PASS | Risk Engine as final arbiter. Hard limits enforced before execution. Global drawdown triggers auto de-risk/halt. Models express intent, not orders |
| 5. Model Isolation & Intent-Based Interface | ✅ PASS | Models receive Context (features, regime, budget), output target weights (0-1 of budget). No knowledge of other models or brokers |
| 6. Regime-Aware Adaptation | ✅ PASS | Regime Engine classifies market state (equity/vol/crypto/macro). Budgets adjust via `regime_budgets` YAML config. Centralized, transparent logic |
| 7. Unified Execution Abstraction | ✅ PASS | Single interface (`submit_target_weights()`, `get_positions()`, etc.) works in backtest/paper/live. Broker adapters implement this interface |
| 8. Reproducibility & Traceability | ✅ PASS | Parquet data + YAML configs + semantic model versions → identical backtest results. All trades/decisions logged with timestamps. Results in SQLite/DuckDB |
| 9. Multi-Timeframe Architecture | ✅ PASS | H4 primary clock (UTC 00:00/04:00/08:00/12:00/16:00/20:00). Daily data as slow features. Decisions at H4 bar close/open |
| 10. Fail-Safe & Safety-First Operations | ✅ PASS | Drawdown auto de-risk/halt at 15% threshold. Broker order validation (min size, hours, precision). Kill switch via config. No overlapping live/backtest access |

### ✅ Architectural Constraints Compliance

| Constraint | Compliance | Notes |
|------------|------------|-------|
| Data Layer: Parquet, asset-per-file | ✅ PASS | `data/equities/SPY_h4.parquet`, `data/crypto/BTC_h4.parquet`, etc. |
| Model Layer: Context → weights | ✅ PASS | Standard interface. Optional hints (confidence, urgency, horizon) |
| Portfolio Engine: Aggregation + attribution | ✅ PASS | W_total = Σ_m (B_m × w_m). Attribution mapping maintained |
| Risk Engine: Hard limits | ✅ PASS | Per-asset (40%), asset-class (crypto 20%), leverage (1.2x), drawdown (15%) |
| Execution: Unified interface | ✅ PASS | Broker adapters (Alpaca, Binance/Kraken) implement `submit_target_weights()` |
| Optimization: BPS metric | ✅ PASS | BPS = 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD |

### ✅ Non-Negotiable Requirements Verification

1. ✅ **No look-ahead bias**: Data pipeline enforces timestamp ≤ T rule
2. ✅ **Risk Engine enforces limits**: Final arbiter before execution
3. ✅ **YAML configs**: Zero hardcoded parameters in production code
4. ✅ **Semantic versioning**: Models tagged (e.g., `EquityTrendModel_v1.0.0`)
5. ✅ **Unified execution**: Same interface for backtest/paper/live
6. ✅ **Structured logging**: JSON lines with fixed schema (timestamp, component, level, message, context)
7. ✅ **Reproducibility**: Config + data → identical results
8. ✅ **Model isolation**: Models cannot access other models or broker APIs

**GATE RESULT**: ✅ **PASSED** - No constitutional violations. All principles, constraints, and non-negotiable requirements satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/001-trading-platform/
├── spec.md              # Business requirements (64 FRs, 9 user stories, 12 success criteria)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0: Technology decisions and patterns
├── data-model.md        # Phase 1: Entities, schemas, state machines
├── quickstart.md        # Phase 1: Setup and first backtest guide
├── contracts/           # Phase 1: API contracts and interfaces
│   ├── context.py       # Context dataclass (model input)
│   ├── execution.py     # Execution interface (broker abstraction)
│   └── config_schemas.yaml  # YAML config schemas with examples
└── tasks.md             # Phase 2: NOT created by /speckit.plan (use /speckit.tasks)
```

### Source Code (repository root)

```text
project/
├── data/                      # Historical & derived data (Parquet)
│   ├── equities/              # SPY_h4.parquet, SPY_daily.parquet, QQQ_h4.parquet, QQQ_daily.parquet
│   ├── crypto/                # BTC_h4.parquet, BTC_daily.parquet, ETH_h4.parquet, ETH_daily.parquet
│   └── macro/                 # yield_curve.parquet, pmi.parquet (FRED data)
│
├── configs/                   # YAML configuration files
│   ├── base/                  # Default system config
│   │   ├── system.yaml        # Model budgets, risk limits, execution mode
│   │   ├── models.yaml        # Model parameters (fast_ma, slow_ma, rsi_period, etc.)
│   │   └── regime_budgets.yaml  # Budget overrides per regime (equity_bull, equity_bear, etc.)
│   └── experiments/           # Experiment override files
│       └── trend_sweep.yaml   # Example: fast_ma: [20, 30, 50], slow_ma: [100, 150, 200]
│
├── models/                    # Strategy model implementations
│   ├── __init__.py
│   ├── base.py                # BaseModel abstract class (Context → weights interface)
│   ├── equity_trend_v1.py     # EquityTrendModel_v1 (200D MA + momentum)
│   ├── index_mean_rev_v1.py   # IndexMeanReversionModel_v1 (RSI + Bollinger)
│   └── crypto_momentum_v1.py  # CryptoMomentumModel_v1 (30-60D momentum + regime gating)
│
├── engines/                   # Core engine implementations
│   ├── data/                  # Data & feature pipeline
│   │   ├── __init__.py
│   │   ├── downloader.py      # Fetch data from Yahoo/Binance/FRED → Parquet
│   │   ├── validator.py       # Check completeness, OHLC relationships
│   │   ├── features.py        # Compute indicators (MA, RSI, ATR, Bollinger, returns)
│   │   └── alignment.py       # Align daily features to H4 bars, enforce no look-ahead
│   │
│   ├── portfolio/             # Portfolio aggregation & attribution
│   │   ├── __init__.py
│   │   ├── engine.py          # Convert model weights → NAV, aggregate, generate deltas
│   │   └── attribution.py     # Track which model contributed each exposure
│   │
│   ├── risk/                  # Risk enforcement
│   │   ├── __init__.py
│   │   ├── engine.py          # Enforce caps (per-asset, class, leverage), monitor drawdown
│   │   └── scaling.py         # Regime-aware risk scaling logic
│   │
│   ├── regime/                # Market regime classification
│   │   ├── __init__.py
│   │   ├── engine.py          # Classify equity/vol/crypto/macro regimes
│   │   └── classifiers.py     # Equity (200D MA + momentum), Vol (VIX thresholds), Crypto (BTC 200D + momentum), Macro (PMI + yield curve)
│   │
│   ├── execution/             # Execution abstraction & broker adapters
│   │   ├── __init__.py
│   │   ├── interface.py       # ExecutionInterface (submit_target_weights, get_positions, get_cash, get_nav)
│   │   ├── backtest.py        # BacktestExecutor (OHLC simulation, slippage, fees)
│   │   ├── alpaca_adapter.py  # AlpacaAdapter (equities, market/limit orders, paper/live endpoints)
│   │   └── crypto_adapter.py  # CryptoAdapter (Binance/Kraken, spot trading, symbol mapping, precision)
│   │
│   └── optimization/          # Parameter optimization
│       ├── __init__.py
│       ├── grid_search.py     # Grid/random search over YAML-defined parameter spaces
│       ├── evolutionary.py    # EA (selection, crossover, mutation) using top performers as seeds
│       └── scoring.py         # Balanced Performance Score (BPS) calculation
│
├── backtest/                  # CLI tools for research & backtests
│   ├── __init__.py
│   ├── cli.py                 # Main backtest CLI (argparse/click)
│   ├── runner.py              # Orchestrate: load config → run models → log results
│   └── reporting.py           # Generate equity curves, drawdown plots, per-model reports
│
├── live/                      # Paper & live trading runners
│   ├── __init__.py
│   ├── paper_runner.py        # Paper trading mode (broker paper endpoints, simulated fills)
│   ├── live_runner.py         # Live trading mode (real broker APIs, position reconciliation)
│   └── scheduler.py           # H4 bar close detection, trigger decision cycle
│
├── utils/                     # Shared helpers
│   ├── __init__.py
│   ├── logging.py             # Structured JSON logger (trades, orders, performance, errors streams)
│   ├── config.py              # YAML loader with merge semantics for experiment overrides
│   ├── metrics.py             # Sharpe, CAGR, MaxDD, WinRate, BPS calculations
│   └── time_utils.py          # UTC normalization, H4 bar boundary detection, timezone conversion
│
├── logs/                      # Structured JSON logs (gitignore'd)
│   ├── trades.log             # Executed trades and fills
│   ├── orders.log             # Orders sent to broker/backtest engine
│   ├── performance.log        # Periodic performance snapshots
│   └── errors.log             # Errors and exceptions
│
├── results/                   # SQLite/DuckDB databases (gitignore'd)
│   └── backtests.db           # Experiment metadata, portfolio metrics, per-model metrics
│
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests for core logic
│   │   ├── test_data_alignment.py       # No look-ahead bias tests
│   │   ├── test_portfolio_aggregation.py  # Model weight aggregation correctness
│   │   ├── test_risk_enforcement.py     # Cap enforcement (per-asset, class, leverage, drawdown)
│   │   └── test_regime_classification.py  # Regime logic validation
│   │
│   ├── integration/           # Integration tests
│   │   ├── test_backtest_e2e.py         # Full backtest run (config → results)
│   │   ├── test_optimization_pipeline.py  # Grid search → EA refinement → BPS ranking
│   │   └── test_model_lifecycle.py      # Promote research → candidate → paper → live
│   │
│   └── contract/              # Contract tests for broker adapters
│       ├── test_alpaca_adapter.py       # Alpaca paper endpoint validation
│       └── test_crypto_adapter.py       # Binance/Kraken symbol mapping, precision
│
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── .env.example               # Environment variables (API keys) - NOT committed
└── README.md                  # Setup instructions, quickstart guide
```

**Structure Decision**: Single project (CLI-driven) using clean architecture. The `data/`, `configs/`, `models/`, `engines/`, `backtest/`, `live/`, `utils/`, `logs/`, `results/` separation ensures:
1. **Modularity**: Each engine is independent and replaceable
2. **Testability**: Unit tests for engines, integration tests for end-to-end flows
3. **Deployment**: Same codebase for research (local) and paper/live (cloud VPS), differentiated by config only

No web frontend or mobile app in v1 (out of scope per FR-056 note), so backend-only structure is appropriate.

## Complexity Tracking

**No constitutional violations requiring justification.** All design decisions align with principles and constraints.

The multi-engine architecture (Data, Model, Portfolio, Risk, Regime, Execution, Optimization) is justified by:
- **Domain complexity**: Algorithmic trading requires independent concerns (data integrity, risk management, order execution)
- **Modularity**: Each engine has a single responsibility and can be tested/replaced independently
- **Safety**: Risk and execution engines must be isolated to prevent bugs in models from bypassing safety checks

This is not over-engineering; it's appropriate separation for a safety-critical financial system.

## Phase 0: Research & Technology Decisions

See [research.md](./research.md) for detailed technology evaluations and pattern decisions.

### Key Research Areas

1. **Parquet library selection**: pyarrow vs fastparquet (performance, compatibility, features)
2. **Broker API libraries**: alpaca-py vs alpaca-trade-api (maintenance, features), python-binance vs ccxt (multi-exchange support)
3. **Time series alignment patterns**: pandas resample vs manual UTC alignment (correctness, performance)
4. **YAML merge semantics**: ruamel.yaml vs PyYAML + custom merge (experiment override behavior)
5. **Evolutionary algorithm library**: DEAP vs custom implementation (flexibility, optimization metrics)
6. **DuckDB vs SQLite**: Query performance on backtest results (aggregations, joins), storage efficiency
7. **Structured logging**: python-json-logger vs custom formatter (schema enforcement, stream separation)
8. **Type validation**: pydantic for config/Context validation (runtime safety, YAML schema generation)

## Phase 1: Design Artifacts

### Generated Artifacts

1. **[data-model.md](./data-model.md)**: Entities (Asset, Model, Context, PortfolioState, RegimeState, Trade, BacktestResult), state transitions (model lifecycle), validation rules
2. **[contracts/](./contracts/)**: Python interfaces and dataclasses for Context, ExecutionInterface, config schemas
3. **[quickstart.md](./quickstart.md)**: Setup environment, download sample data, run first backtest, interpret results

### Design Highlights

- **Context dataclass**: Immutable snapshot (timestamp, per-asset features as DataFrames, regime dict, model budget tuple, current exposures dict)
- **ExecutionInterface protocol**: Abstract base class with `submit_target_weights()`, `get_positions()`, `get_cash()`, `get_nav()`, `get_broker_metadata()`
- **Config schemas**: Pydantic models for system.yaml (ModelConfig, RiskConfig, RegimeBudgets), models.yaml (EquityTrendParams, IndexMeanRevParams, CryptoMomentumParams), validated on load
- **Model lifecycle state machine**: research → candidate → paper → live (transitions logged with operator + timestamp + reason)

## Implementation Phases (Post-Planning)

**Note**: The following phases are executed via `/speckit.tasks` and implementation, not part of `/speckit.plan` output.

### Phase 2: Core Infrastructure (Weeks 1-4)

**Objective**: Backtest single model with no-look-ahead bias enforcement

**Deliverables**:
- Data pipeline (download, validate, store Parquet)
- Centralized feature computation (MA, RSI, ATR, Bollinger, returns)
- Time alignment module (daily → H4, no look-ahead enforcement)
- Base model interface and EquityTrendModel_v1 implementation
- Backtest execution engine (OHLC simulation, slippage, fees)
- Structured logging (trades, orders, performance, errors)
- Config loader (YAML with validation)
- CLI for single model backtest

**Success Criteria** (maps to spec SC-001, SC-002):
- Single model backtest of 5 years H4 data completes in <5 minutes
- 100% of trades use only data available at decision time (verified by tests)

### Phase 3: Multi-Model & Risk (Weeks 5-7)

**Objective**: Run 3 models simultaneously with portfolio aggregation and risk enforcement

**Deliverables**:
- IndexMeanReversionModel_v1 and CryptoMomentumModel_v1 implementations
- Portfolio Engine (weight conversion, aggregation, attribution)
- Risk Engine (per-asset caps, asset-class caps, leverage limit, drawdown monitoring)
- Multi-model backtest support in CLI
- Attribution reporting

**Success Criteria** (maps to spec SC-003, SC-004, SC-011):
- Multi-model aggregation correct (budgets 60%, 25%, 15% → total 100% NAV when all target same asset)
- Risk limits enforced 100% of time (per-asset 40%, crypto 20%, leverage 1.2x, drawdown 15%)
- Attribution accuracy within floating-point tolerance (1e-6)

### Phase 4: Regime & Optimization (Weeks 8-10)

**Objective**: Regime-aware budget allocation and parameter optimization

**Deliverables**:
- Regime Engine (equity, vol, crypto, macro classification)
- Regime-based budget overrides (YAML regime_budgets)
- Grid/random search optimization
- Evolutionary algorithm refinement
- BPS calculation and ranking
- Results database (SQLite/DuckDB)
- Comparison reports

**Success Criteria** (maps to spec SC-005, SC-006, SC-012):
- Regime classification >90% agreement with manual classification
- Grid search (100 combinations) completes in <10 minutes
- Per-model performance reports generated in <30 seconds

### Phase 5: Paper Trading (Weeks 11-13)

**Objective**: Deploy to paper trading with broker integration

**Deliverables**:
- Alpaca adapter (paper endpoints, market/limit orders)
- Crypto adapter (Binance/Kraken, spot trading, symbol mapping, precision)
- Paper runner (H4 bar scheduling, live data fetch, order submission)
- Position reconciliation (internal vs broker)
- Model lifecycle management (candidate/paper filtering)
- Cloud deployment setup (VPS, systemd service)

**Success Criteria** (maps to spec SC-007):
- Paper orders submitted with <5 second latency from H4 bar close
- Internal positions match broker paper account state

### Phase 6: Live Trading (Weeks 14-16)

**Objective**: Production-ready live trading with safety controls

**Deliverables**:
- Live runner (real broker APIs, position reconciliation)
- Kill switch (config flag + external command)
- Live model filtering (lifecycle_stage = live only)
- Enhanced error logging (errors.log monitoring)
- Drawdown auto de-risk/halt in live mode
- Deployment documentation

**Success Criteria** (maps to spec SC-008, SC-009, SC-010):
- Experiments reproducible (same config + data → identical results)
- Kill switch halts orders in <1 second
- 100% of trades/orders/snapshots logged in JSON

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Look-ahead bias in feature computation | High (invalid backtests) | Medium | Extensive unit tests for time alignment, daily → H4 alignment validation, automated timestamp checks |
| Broker API rate limits | High (live trading halt) | Medium | Respect documented rate limits, exponential backoff retry logic, cache position/balance queries |
| Data source downtime (Yahoo, Binance, FRED) | Medium (stale data) | Medium | Fallback to cached data (forward-fill), alert on data gaps >48 hours, manual data source switching |
| Floating-point precision in NAV calculations | Medium (attribution errors) | Low | Use Decimal for monetary amounts, tolerance-based equality checks (1e-6), extensive rounding tests |
| Regime classification false signals | Medium (wrong budget allocation) | Medium | Conservative default regimes (NEUTRAL/NORMAL), stale data fallback, regime transition hysteresis (require N consecutive bars) |
| Broker order rejection (min size, hours) | Medium (missed trades) | Low | Pre-validate all orders against broker constraints, log rejection reasons, retry with adjusted quantity if applicable |
| Kill switch failure in live mode | High (runaway trading) | Low | Dual mechanism (config flag + external command), test kill switch in paper mode before live, manual broker account halt procedure |
| Experiment config corruption | Low (reproducibility loss) | Low | Git version control for all YAML configs, config validation on load (pydantic), backup to results DB on each run |

## Success Metrics (Implementation Phase)

**Code Quality**:
- Test coverage: >80% (pytest-cov)
- Type hint coverage: 100% for public interfaces (mypy --strict)
- Documentation: All public functions/classes have docstrings

**Performance** (measured via pytest-benchmark):
- H4 bar processing: <1 second for 10 assets
- Backtest (5 years H4): <5 minutes for 3 models
- Feature computation: <10 seconds for 5 years daily data per asset

**Correctness** (verified via test suite):
- No look-ahead bias: 100% of trades verified with timestamp checks
- Risk limits: 100% enforcement in >1000 backtest scenarios
- Attribution: Sum of model contributions = final portfolio (within 1e-6)
- Reproducibility: 10 re-runs of same config produce bit-identical equity curves

## Next Steps

1. ✅ **Phase 0 Complete**: Run `/speckit.plan` to generate research.md, data-model.md, contracts/, quickstart.md
2. ⏭️ **Phase 1 Next**: Review generated artifacts, validate design against spec
3. ⏭️ **Phase 2 Next**: Run `/speckit.tasks` to generate implementation tasks from plan.md
4. ⏭️ **Implementation**: Execute tasks in priority order (P1 → P2 → P3)

**Command to proceed**: `/speckit.tasks` (generates tasks.md with dependency-ordered implementation tasks)
