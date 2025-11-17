# Tasks: Multi-Model Algorithmic Trading Platform

**Input**: Design documents from `/specs/001-trading-platform/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md, this is a single Python project with structure:
- `data/` - Parquet data files
- `configs/` - YAML configuration
- `models/` - Strategy implementations
- `engines/` - Core engines (data, portfolio, risk, regime, execution, optimization)
- `backtest/` - Backtest CLI and tools
- `live/` - Paper/live trading runners
- `utils/` - Shared utilities
- `tests/` - Test suite
- `logs/` - JSON logs (gitignored)
- `results/` - DuckDB databases (gitignored)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure (data/, configs/, models/, engines/, backtest/, live/, utils/, logs/, results/, tests/)
- [x] T002 Initialize Python 3.9+ project with requirements.txt (pandas, numpy, pyarrow, pyyaml, pydantic, alpaca-py, ccxt, duckdb, pytest, python-json-logger)
- [x] T003 [P] Create .gitignore for logs/, results/, data/, .env, __pycache__
- [x] T004 [P] Create .env.example with API key placeholders (ALPACA_API_KEY, ALPACA_API_SECRET, BINANCE_API_KEY, BINANCE_API_SECRET, KRAKEN_API_KEY, KRAKEN_API_SECRET)
- [x] T005 [P] Create README.md with setup instructions and quickstart reference
- [x] T006 [P] Create setup.py for package installation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Utilities & Configuration

- [x] T007 [P] Implement structured JSON logger in utils/logging.py with separate streams (trades, orders, performance, errors)
- [x] T008 [P] Implement YAML config loader with merge semantics in utils/config.py
- [x] T009 [P] Implement time utilities in utils/time_utils.py (UTC normalization, H4 boundary detection, timezone conversion)
- [x] T010 [P] Implement performance metrics calculator in utils/metrics.py (Sharpe, CAGR, MaxDD, WinRate, BPS)

### Base Contracts & Interfaces

- [x] T011 [P] Copy Context dataclass from specs/001-trading-platform/contracts/context.py to models/base.py
- [x] T012 [P] Copy ExecutionInterface from specs/001-trading-platform/contracts/execution.py to engines/execution/interface.py
- [x] T013 [P] Create BaseModel abstract class in models/base.py (defines generate_target_weights interface)

### Configuration Files

- [x] T014 [P] Create base system config template in configs/base/system.yaml per contracts/config_schemas.yaml
- [x] T015 [P] Create base models config template in configs/base/models.yaml per contracts/config_schemas.yaml
- [x] T016 [P] Create regime budgets config template in configs/base/regime_budgets.yaml per contracts/config_schemas.yaml

### Data Pipeline Foundation

- [x] T017 Implement data validator in engines/data/validator.py (OHLC consistency, gap detection, timestamp validation)
- [x] T018 Implement time alignment module in engines/data/alignment.py (daily → H4 alignment, no look-ahead enforcement)
- [x] T019 Implement feature computation in engines/data/features.py (MA, RSI, ATR, Bollinger Bands, returns)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Backtest Single Strategy Model (Priority: P1) 🎯 MVP

**Goal**: Backtest a single trading strategy using historical data to validate performance before risking capital

**Independent Test**: Configure EquityTrendModel_v1 with YAML, run against 2+ years of historical H4 data, verify equity curve, trade log, and performance metrics without look-ahead bias

### Implementation for User Story 1

- [x] T020 [P] [US1] Implement data downloader for equities in engines/data/downloader.py (Yahoo Finance via yfinance, save to Parquet)
- [x] T021 [P] [US1] Create EquityTrendModel_v1 in models/equity_trend_v1.py (200D MA + momentum logic)
- [x] T022 [US1] Implement data pipeline loader in engines/data/pipeline.py (load Parquet, construct Context, enforce no look-ahead)
- [x] T023 [US1] Implement BacktestExecutor in backtest/executor.py (OHLC simulation, slippage, fees)
- [x] T024 [US1] Implement backtest runner in backtest/runner.py (orchestrate: load config → run model → log results)
- [x] T025 [US1] Implement backtest CLI in backtest/cli.py (argparse interface for running backtests)
- [x] T026 [US1] Create DuckDB schema for backtest results in results/schema.py (backtests table, trades table, nav_history, metrics)
- [x] T027 [US1] Implement equity curve generation in results/visualize.py (plot NAV, drawdown, monthly returns, trade distribution)
- [x] T028 [US1] Add validation: verify no look-ahead bias in tests/test_no_lookahead.py (6 comprehensive tests)
- [x] T029 [US1] Add integration test for full backtest run in tests/test_integration.py (complete workflow + model signal validation)

**Checkpoint**: At this point, User Story 1 should be fully functional - single model backtests work end-to-end

---

## Phase 4: User Story 2 - Run Multi-Model Portfolio (Priority: P1)

**Goal**: Run multiple strategy models simultaneously with independent budgets to diversify risk and combine complementary strategies

**Independent Test**: Configure 3 models (EquityTrendModel_v1, IndexMeanReversionModel_v1, CryptoMomentumModel_v1) with budgets 60%, 25%, 15%, run backtest, verify Portfolio Engine aggregates exposures correctly

### Implementation for User Story 2

- [X] T030 [P] [US2] Create IndexMeanReversionModel_v1 in models/index_mean_rev_v1.py (RSI + Bollinger Bands logic)
- [X] T031 [P] [US2] Create CryptoMomentumModel_v1 in models/crypto_momentum_v1.py (30-60D momentum + regime gating)
- [X] T032 [P] [US2] Implement data downloader for crypto in engines/data/downloader.py (Binance/Kraken via ccxt, save to Parquet)
- [X] T033 [US2] Implement Portfolio Engine in engines/portfolio/engine.py (convert model weights → NAV, aggregate, generate deltas)
- [X] T034 [US2] Implement attribution tracking in engines/portfolio/attribution.py (map exposures to source models)
- [X] T035 [US2] Update backtest runner in backtest/runner.py to support multi-model mode (load multiple models, aggregate outputs)
- [X] T036 [US2] Add per-model reporting in backtest/reporting.py (individual model equity curves, attribution breakdown)
- [X] T037 [US2] Add unit test for portfolio aggregation in tests/unit/test_portfolio_aggregation.py (verify budgets sum correctly)
- [X] T038 [US2] Add unit test for attribution accuracy in tests/unit/test_portfolio_aggregation.py (verify sum of attributions = position)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - multi-model portfolios aggregate correctly

---

## Phase 5: User Story 3 - Apply Risk Controls (Priority: P1)

**Goal**: Enforce hard limits on exposures, leverage, and drawdown so no strategy can exceed risk tolerances

**Independent Test**: Configure risk limits (40% per asset, 20% crypto, 1.2x leverage, 15% max drawdown), run backtests with models that exceed limits, verify Risk Engine scales down or halts

### Implementation for User Story 3

- [X] T039 [P] [US3] Implement Risk Engine in engines/risk/engine.py (enforce per-asset caps, asset-class caps, leverage limit, drawdown monitoring)
- [X] T040 [P] [US3] Implement regime-aware risk scaling in engines/risk/scaling.py (apply regime-based budget multipliers)
- [X] T041 [US3] Integrate Risk Engine into Portfolio Engine in engines/portfolio/engine.py (apply constraints before finalizing targets)
- [X] T042 [US3] Add drawdown auto-derisking logic in engines/risk/engine.py (50% reduction at 15%, halt at 20%)
- [X] T043 [US3] Update backtest runner to include risk enforcement in backtest/runner.py
- [X] T044 [US3] Add unit tests for risk limit enforcement in tests/unit/test_risk_enforcement.py (per-asset, class, leverage, drawdown)
- [X] T045 [US3] Add integration test for risk scenarios in tests/integration/test_backtest_e2e.py (models exceeding limits)

**Checkpoint**: All P1 user stories complete - core backtest platform with multi-model and risk controls functional

---

## Phase 6: User Story 4 - Classify Market Regimes (Priority: P2)

**Goal**: Automatically classify market conditions (equity trend, volatility, crypto sentiment, macro) so budgets and risk adapt to changing markets

**Independent Test**: Feed historical data for SPY, VIX, BTC, macro indicators into Regime Engine, verify correct classification (e.g., BULL when SPY > 200D MA), confirm Portfolio/Risk Engines adjust budgets based on regime

### Implementation for User Story 4

- [X] T046 [P] [US4] Implement Regime Engine in engines/regime/engine.py (orchestrate all regime classifiers, output RegimeState)
- [X] T047 [P] [US4] Implement equity regime classifier in engines/regime/classifiers.py (SPY vs 200D MA + momentum → BULL/BEAR/NEUTRAL)
- [X] T048 [P] [US4] Implement volatility regime classifier in engines/regime/classifiers.py (VIX thresholds: LOW <15, NORMAL 15-25, HIGH >25)
- [X] T049 [P] [US4] Implement crypto regime classifier in engines/regime/classifiers.py (BTC vs 200D MA + 60D momentum → RISK_ON/RISK_OFF)
- [X] T050 [P] [US4] Implement macro regime classifier in engines/regime/classifiers.py (PMI + yield curve → EXPANSION/SLOWDOWN/RECESSION)
- [X] T051 [P] [US4] Implement data downloader for macro data in engines/data/downloader.py (FRED API for PMI, yield curve)
- [X] T052 [US4] Integrate Regime Engine into data pipeline in engines/data/__init__.py (include regime in Context)
- [X] T053 [US4] Update Portfolio Engine to apply regime budget overrides in engines/portfolio/engine.py (read regime_budgets.yaml)
- [X] T054 [US4] Update backtest runner to log regime transitions in backtest/runner.py
- [X] T055 [US4] Add unit tests for regime classification in tests/unit/test_regime_classification.py (verify BULL/BEAR logic)
- [X] T056 [US4] Generate regime alignment reports in backtest/reporting.py (performance by regime periods)

**Checkpoint**: Regime-aware portfolio management functional - budgets adapt to market conditions

---

## Phase 7: User Story 5 - Optimize Strategy Parameters (Priority: P2)

**Goal**: Systematically search parameter spaces using grid/random search and evolutionary algorithms to find robust parameter sets

**Independent Test**: Define parameter grid in YAML experiment file (fast_ma: [20, 30, 50], slow_ma: [100, 150, 200]), run optimizer, verify 9 backtests execute, ranks by BPS, logs to database

### Implementation for User Story 5
063 [US5] Generate comparison reports in backtest/reporting.py (side-by-side metrics for experiments)
- [ ] T064 [US5] Add integration test for optimization pipeline in tests/integration/test_optimization_pipeline.py

**Checkpoint**: Parameter optimization functional - can search large parameter spaces efficiently

---

## Phase 8: User Story 6 - Download and Update Historical Data (Priority: P2)

**Goal**: Download and periodically update historical price data for all assets so backtests use current data

**Independent Test**: Run data download command for SPY (H4 + daily) and BTC (H4 + daily), verify Parquet files created, run update to append new bars

### Implementation for User Story 6

- [ ] T065 [P] [US6] Create data download CLI script in engines/data/cli.py (argparse interface for download/update commands)
- [ ] T066 [US6] Implement incremental update logic in engines/data/downloader.py (detect last timestamp, fetch only new bars, avoid duplicates)
- [ ] T067 [US6] Add timezone normalization for equity data in engines/data/downloader.py (Alpaca US/Eastern → UTC)
- [ ] T068 [US6] Add H4 bar alignment logic in engines/data/downloader.py (resample 1H → H4 at correct boundaries)
- [ ] T069 [US6] Add data validation after download in engines/data/cli.py (call validator, report gaps/errors)
- [ ] T070 [US6] Add error handling for API failures in engines/data/downloader.py (log error, continue with other symbols)
- [ ] T071 [US6] Update quickstart.md with data download instructions

**Checkpoint**: Data download and update workflow complete - platform is self-sufficient for data management

---

## Phase 9: User Story 7 - Manage Model Lifecycle Progression (Priority: P2)

**Goal**: Systematically promote models through lifecycle stages (research → candidate → paper → live) with clear criteria and tracking

**Independent Test**: Promote model from research through all stages, verify transitions tracked in results DB and config, confirm paper/live runners only execute appropriate models

### Implementation for User Story 7

- [ ] T072 [P] [US7] Add lifecycle_stage field to Model entity in models/base.py (research/candidate/paper/live)
- [ ] T073 [P] [US7] Create lifecycle promotion CLI in backtest/cli.py (promote/demote commands with reason logging)
- [ ] T074 [US7] Update DuckDB schema for lifecycle events in results/ (model_lifecycle_events table)
- [ ] T075 [US7] Add lifecycle transition validation in backtest/cli.py (check backtest criteria before promoting)
- [ ] T076 [US7] Add lifecycle filtering in live/paper_runner.py (only load candidate/paper models)
- [ ] T077 [US7] Add lifecycle filtering in live/live_runner.py (only load live models)
- [ ] T078 [US7] Add unit test for lifecycle transitions in tests/unit/test_model_lifecycle.py
- [ ] T079 [US7] Add integration test for lifecycle management in tests/integration/test_model_lifecycle.py

**Checkpoint**: Model lifecycle management complete - systematic path from research to live trading

---

## Phase 10: User Story 8 - Paper Trade Strategies (Priority: P3)

**Goal**: Run validated models in paper trading mode using live market data but simulated execution to verify real-world behavior

**Independent Test**: Configure model for paper mode, connect to broker paper endpoints (Alpaca paper, Binance testnet), run for several days, verify orders submitted and filled using live prices

### Implementation for User Story 8

- [ ] T080 [P] [US8] Implement Alpaca adapter in engines/execution/alpaca_adapter.py (paper endpoints, market/limit orders, position queries)
- [ ] T081 [P] [US8] Implement Crypto adapter in engines/execution/crypto_adapter.py (Binance/Kraken testnet, spot trading, symbol mapping, precision)
- [ ] T082 [US8] Implement H4 bar scheduler in live/scheduler.py (detect H4 bar close, trigger decision cycle)
- [ ] T083 [US8] Implement paper trading runner in live/paper_runner.py (fetch live data, run models, submit paper orders)
- [ ] T084 [US8] Implement position reconciliation in engines/execution/alpaca_adapter.py (compare internal vs broker positions, log discrepancies)
- [ ] T085 [US8] Add broker order validation in engines/execution/alpaca_adapter.py (min size, trading hours, precision checks)
- [ ] T086 [US8] Add retry logic with exponential backoff in engines/execution/alpaca_adapter.py (handle API failures)
- [ ] T087 [US8] Update logging to include broker order IDs in utils/logging.py
- [ ] T088 [US8] Add contract tests for Alpaca adapter in tests/contract/test_alpaca_adapter.py
- [ ] T089 [US8] Add contract tests for Crypto adapter in tests/contract/test_crypto_adapter.py

**Checkpoint**: Paper trading functional - models run on live data with simulated execution

---

## Phase 11: User Story 9 - Deploy Live Trading (Priority: P3)

**Goal**: Deploy validated, paper-tested models to live trading with real capital while maintaining full risk controls and monitoring

**Independent Test**: Promote paper-tested model to live, configure live credentials, activate kill switch, verify real orders placed, filled, and reconciled

### Implementation for User Story 9

- [ ] T090 [P] [US9] Implement live trading runner in live/live_runner.py (real broker APIs, position reconciliation, P&L tracking)
- [ ] T091 [P] [US9] Implement kill switch mechanism in live/live_runner.py (config flag + external command to halt orders)
- [ ] T092 [US9] Update Alpaca adapter for live endpoints in engines/execution/alpaca_adapter.py (paper=False mode)
- [ ] T093 [US9] Update Crypto adapter for live endpoints in engines/execution/crypto_adapter.py (mainnet URLs)
- [ ] T094 [US9] Add NAV mode detection in live/live_runner.py (query broker balance instead of config for live/paper)
- [ ] T095 [US9] Add position reconciliation for live mode in live/live_runner.py (ensure internal matches broker exactly)
- [ ] T096 [US9] Add global drawdown halt for live mode in engines/risk/engine.py (auto-exit at 20% threshold)
- [ ] T097 [US9] Add mutex lock to prevent overlapping live/backtest access in live/live_runner.py (file-based lock)
- [ ] T098 [US9] Create deployment documentation in docs/deployment.md (VPS setup, systemd service, monitoring)
- [ ] T099 [US9] Add integration test for kill switch in tests/integration/test_live_trading.py

**Checkpoint**: Live trading deployment ready - all safety controls in place for production use

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T100 [P] Add type hints to all public interfaces across codebase (mypy --strict compliance)
- [ ] T101 [P] Add docstrings to all public functions and classes
- [ ] T102 [P] Create architecture diagrams in docs/ (data flow, engine interactions)
- [ ] T103 [P] Update README.md with comprehensive setup, configuration, and usage guide
- [ ] T104 [P] Create YAML config validation using pydantic in utils/config.py
- [ ] T105 [P] Add performance benchmarks in tests/benchmark/ (H4 bar processing, backtest speed)
- [ ] T106 Code cleanup: remove dead code, consolidate duplicates
- [ ] T107 Security audit: ensure API keys from env only, no secrets in logs
- [ ] T108 Run full test suite and fix any failing tests
- [ ] T109 Validate quickstart.md by following steps from scratch
- [ ] T110 Create requirements-dev.txt for development dependencies (pytest, mypy, black, flake8)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - P1 priority (MVP)
- **User Story 2 (Phase 4)**: Depends on Foundational - P1 priority (can run parallel with US1 if staffed)
- **User Story 3 (Phase 5)**: Depends on Foundational + US2 (needs Portfolio Engine) - P1 priority
- **User Story 4 (Phase 6)**: Depends on Foundational - P2 priority
- **User Story 5 (Phase 7)**: Depends on US1 complete (needs backtest infrastructure) - P2 priority
- **User Story 6 (Phase 8)**: Depends on Foundational - P2 priority (can run parallel with other P2)
- **User Story 7 (Phase 9)**: Depends on Foundational - P2 priority (can run parallel with other P2)
- **User Story 8 (Phase 10)**: Depends on US1-3 complete (needs full backtest + risk) - P3 priority
- **User Story 9 (Phase 11)**: Depends on US8 complete (needs paper trading) - P3 priority
- **Polish (Phase 12)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - Extends US1 but independently testable
- **User Story 3 (P1)**: Depends on US2 Portfolio Engine - Integrates with multi-model aggregation
- **User Story 4 (P2)**: Can start after Foundational - Integrates with US2/US3 but independently testable
- **User Story 5 (P2)**: Depends on US1 - Needs backtest runner to optimize
- **User Story 6 (P2)**: Can start after Foundational - Independent data management
- **User Story 7 (P2)**: Can start after Foundational - Independent lifecycle tracking
- **User Story 8 (P3)**: Depends on US1-3 - Needs full platform functionality
- **User Story 9 (P3)**: Depends on US8 - Paper trading must precede live

### Within Each User Story

- Data downloaders before models (models need data)
- Models before engines (engines orchestrate models)
- Engines before runners (runners use engines)
- Core implementation before integration tests
- Story complete and tested before moving to next priority

### Parallel Opportunities

**Setup Phase**:
- T003, T004, T005, T006 can all run in parallel

**Foundational Phase**:
- T007, T008, T009, T010 (utilities) can run in parallel
- T011, T012, T013 (contracts) can run in parallel
- T014, T015, T016 (configs) can run in parallel

**User Story 1**:
- T020, T021 can run in parallel (data downloader + model)

**User Story 2**:
- T030, T031, T032 can run in parallel (all 3 are independent models/downloaders)

**User Story 3**:
- T039, T040 can run in parallel (risk engine + scaling are separate files)

**User Story 4**:
- T046, T047, T048, T049, T050, T051 can run in parallel (all regime-related, different files)

**User Story 5**:
- T057, T058, T059, T060 can run in parallel (optimization components)

**User Story 6**:
- T065 can start immediately after T066-T070 (CLI depends on implementation)

**User Story 7**:
- T072, T073, T074 can run in parallel (different aspects of lifecycle)

**User Story 8**:
- T080, T081 can run in parallel (different broker adapters)

**User Story 9**:
- T090, T091 can run in parallel (runner + kill switch)

**Polish Phase**:
- T100, T101, T102, T103, T104, T105 can all run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch parallelizable tasks for User Story 1 together:
Task T020: "Implement data downloader for equities in engines/data/downloader.py"
Task T021: "Create EquityTrendModel_v1 in models/equity_trend_v1.py"
# These can run simultaneously - different files, no dependencies
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (single model backtest)
4. Complete Phase 4: User Story 2 (multi-model portfolio)
5. Complete Phase 5: User Story 3 (risk controls)
6. **STOP and VALIDATE**: Test all P1 stories independently
7. Deploy/demo backtest platform - **MVP COMPLETE**

This delivers a fully functional backtesting platform with multi-model support and risk controls - immediate research value.

### Incremental Delivery (Add P2 Features)

After MVP validation:

8. Add User Story 4: Regime classification (enhance portfolio management)
9. Add User Story 5: Parameter optimization (systematic strategy improvement)
10. Add User Story 6: Data management (operational efficiency)
11. Add User Story 7: Model lifecycle (governance and tracking)
12. Each P2 story adds value without breaking existing functionality

### Production Deployment (Add P3 Features)

After P2 features validated:

13. Add User Story 8: Paper trading (bridge to live)
14. Add User Story 9: Live trading (full production deployment)
15. Complete Phase 12: Polish and documentation

### Parallel Team Strategy

With multiple developers:

1. **Week 1-2**: Team completes Setup + Foundational together
2. **Week 3-4**: Once Foundational done:
   - Developer A: User Story 1 (T020-T029)
   - Developer B: User Story 2 (T030-T038) - can start in parallel
   - Developer C: User Story 6 (T065-T071) - can start in parallel
3. **Week 5**:
   - Developer A: User Story 3 (T039-T045) - needs US2 Portfolio Engine
   - Developer B: User Story 4 (T046-T056)
   - Developer C: User Story 7 (T072-T079)
4. **Week 6**: Developer A+B: User Story 5 (T057-T064)
5. **Week 7-8**: Developer A: User Story 8 (T080-T089)
6. **Week 9-10**: Developer A: User Story 9 (T090-T099)
7. **Week 11**: All: Polish (T100-T110)

---

## Task Summary

### Total Tasks: 110

### Tasks per User Story:
- **Setup (Phase 1)**: 6 tasks
- **Foundational (Phase 2)**: 13 tasks
- **User Story 1 (P1)**: 10 tasks (T020-T029)
- **User Story 2 (P1)**: 9 tasks (T030-T038)
- **User Story 3 (P1)**: 7 tasks (T039-T045)
- **User Story 4 (P2)**: 11 tasks (T046-T056)
- **User Story 5 (P2)**: 8 tasks (T057-T064)
- **User Story 6 (P2)**: 7 tasks (T065-T071)
- **User Story 7 (P2)**: 8 tasks (T072-T079)
- **User Story 8 (P3)**: 10 tasks (T080-T089)
- **User Story 9 (P3)**: 10 tasks (T090-T099)
- **Polish (Phase 12)**: 11 tasks (T100-T110)

### Parallel Opportunities: 47 tasks marked [P]
These can be executed simultaneously by different developers or in parallel tool calls.

### MVP Scope (P1 stories only): 45 tasks
- Phase 1: 6 tasks
- Phase 2: 13 tasks
- User Story 1: 10 tasks
- User Story 2: 9 tasks
- User Story 3: 7 tasks

**MVP Delivery**: A fully functional multi-model backtesting platform with risk controls, ready for research use.

---

## Independent Test Criteria

### User Story 1
✓ Configure EquityTrendModel_v1 via YAML
✓ Run backtest on 2+ years H4 data
✓ Generate equity curve, trade log, metrics
✓ Verify no look-ahead bias (automated test)

### User Story 2
✓ Configure 3 models with budgets 60%, 25%, 15%
✓ Verify total exposure = 100% NAV when all target same asset
✓ Verify attribution sums match positions
✓ Generate per-model performance reports

### User Story 3
✓ Configure risk limits (40% per asset, 20% crypto, 1.2x leverage, 15% drawdown)
✓ Run scenarios where models exceed limits
✓ Verify Risk Engine scales down or halts
✓ Verify 100% enforcement in test suite

### User Story 4
✓ Feed historical SPY, VIX, BTC, macro data
✓ Verify regime classifications match manual labels (>90% agreement)
✓ Verify budgets adjust per regime_budgets.yaml
✓ Generate regime alignment reports

### User Story 5
✓ Define parameter grid in experiment YAML
✓ Run grid search, verify all combinations tested
✓ Verify results ranked by BPS
✓ Verify results stored in DuckDB with full metadata

### User Story 6
✓ Run download command for SPY and BTC (H4 + daily)
✓ Verify Parquet files created in correct directories
✓ Run update command, verify new bars appended
✓ Verify no duplicates, gaps detected

### User Story 7
✓ Promote model research → candidate → paper → live
✓ Verify each transition logged in results DB
✓ Verify paper runner only loads candidate/paper models
✓ Verify live runner only loads live models

### User Story 8
✓ Configure model for paper mode
✓ Connect to Alpaca paper and Binance testnet
✓ Run for multiple H4 bars, verify orders submitted
✓ Verify positions match broker paper account

### User Story 9
✓ Promote paper-tested model to live
✓ Configure live broker credentials
✓ Test kill switch halts orders in <1 second
✓ Verify real orders placed and reconciled

---

## Format Validation

✅ All tasks follow format: `- [ ] [ID] [P?] [Story?] Description with file path`
✅ All user story tasks include [Story] label (US1-US9)
✅ All parallelizable tasks marked with [P]
✅ All tasks include specific file paths
✅ Sequential task IDs (T001-T110)

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths reference repository root structure from plan.md
- Configuration-driven: all behavior controlled via YAML
- No tests are included in this task list (none were explicitly requested in spec)
