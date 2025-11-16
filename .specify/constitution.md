# Project Constitution

## Core Identity

This is a **multi-model, multi-asset algorithmic trading platform** designed for research, backtesting, paper trading, and live trading across equities and cryptocurrencies with regime-aware, risk-controlled execution.

## Fundamental Principles

### 1. Modularity & Separation of Concerns

**Principle:** Each component is independent, self-contained, and replaceable.

- Models (alpha engines) are pluggable and do not know about other models or broker details
- Engines (Portfolio, Risk, Regime, Execution) have clearly defined interfaces and responsibilities
- Broker adapters conform to a unified abstraction layer
- No component directly accesses raw data files; all data flows through the Data & Feature Layer

**Rationale:** Enables independent development, testing, and replacement of components without cascading changes.

### 2. Configuration-Driven Architecture

**Principle:** All system behavior is controlled via YAML configuration files.

- Model selection, parameters, and budgets defined in YAML
- Regime-based budget shifts configured, not hardcoded
- Experiment overrides use YAML merge semantics
- No magic numbers or hardcoded thresholds in production code

**Rationale:** Supports reproducibility, experimentation, and Speckit-friendly workflows without code changes.

### 3. No Look-Ahead Bias

**Principle:** Data integrity is paramount. Only past and current bar data is accessible at decision time.

- Time alignment strictly enforced in data pipeline
- Feature computation respects causality
- Daily features aligned to H4 bars use only prior/current daily data
- Missing data handled via forward-fill or explicit model policies

**Rationale:** Ensures backtest validity and prevents overfitting to future information.

### 4. Risk-First Design

**Principle:** Risk controls are system-wide, non-negotiable, and enforced before execution.

- Risk Engine acts as the final arbiter of all exposures
- Per-asset, per-class, and gross exposure caps are hard limits
- Global drawdown triggers automatic de-risking or halt
- Models express intent; Portfolio + Risk Engines decide final allocations

**Rationale:** Protects capital and ensures the system cannot exceed risk tolerances regardless of model outputs.

### 5. Model Isolation & Intent-Based Interface

**Principle:** Models are "trading brains" that express desired exposures, not execution instructions.

- Models receive Context (market state, features, regime, budget)
- Models output target weight vectors relative to their budget
- Models do not submit orders or know about other models
- Portfolio Engine aggregates and reconciles model intents

**Rationale:** Simplifies model development, enables multi-model coordination, and maintains clean abstraction boundaries.

### 6. Regime-Aware Adaptation

**Principle:** System behavior adapts to market conditions via explicit regime classification.

- Regime Engine provides structured market state (equity, vol, crypto, macro regimes)
- Model budgets, risk tolerances, and position sizing adjust by regime
- Regime logic is centralized, transparent, and configurable
- Models can use regime gating but are not required to

**Rationale:** Improves robustness by avoiding one-size-fits-all strategies and explicitly encoding market context.

### 7. Unified Execution Abstraction

**Principle:** Broker interaction is abstracted behind a simple, mode-agnostic interface.

- Same code runs in backtest, paper, and live modes
- Broker adapters (Alpaca, Binance, Kraken) implement common interface
- Execution Engine translates portfolio deltas into broker-specific orders
- No direct broker API calls outside adapter layer

**Rationale:** Enables seamless progression from research to live trading and supports multi-broker execution.

### 8. Reproducibility & Traceability

**Principle:** Every experiment and trade is fully reproducible and traceable.

- All data stored in Parquet with consistent schema
- Experiment configs versioned and stored with results
- Backtest results stored in SQLite/DuckDB with full metadata
- Structured JSON logs with fixed schema for all events
- Model versions use semantic versioning

**Rationale:** Enables debugging, performance analysis, regulatory compliance, and scientific rigor.

### 9. Multi-Timeframe Architecture

**Principle:** System operates on H4 (4-hour) bars as primary clock with daily data as slow features.

- Strategy decisions occur at H4 bar close/open
- Daily indicators (200D MA, daily momentum) treated as slow-moving features
- Time alignment rules ensure daily features are properly aligned to H4 bars
- Regime classifications use daily data, applied at H4 resolution

**Rationale:** Balances signal responsiveness with sufficient data history and practical execution frequency.

### 10. Fail-Safe & Safety-First Operations

**Principle:** System must fail gracefully and prevent catastrophic errors.

- Global drawdown limit triggers automatic exposure reduction or halt
- Broker adapters validate all orders against constraints (min size, trading hours)
- No overlapping live and backtest access to same account
- Kill switch available via config or external command
- Error handling with retries and fallbacks at adapter layer

**Rationale:** Protects against software bugs, API failures, and runaway strategies.

## Architectural Constraints

### Data Layer

- **Format:** Parquet for all historical and derived data
- **Structure:** Asset-per-file per timeframe (e.g., `SPY_h4.parquet`)
- **Access:** Models receive Context objects, never load files directly
- **Features:** Centralized feature pipeline runs before models

### Model Layer

- **Interface:** Receive Context, output target weight vector
- **Budgets:** Expressed as fraction of NAV (0-1)
- **Outputs:** Relative weights (0-1 of model budget), not absolute dollar amounts
- **Hints:** Optional confidence/urgency/horizon metadata

### Portfolio Engine

- **Aggregation:** Sum NAV-relative contributions from all models per asset
- **Netting:** Conflicting signals are netted at portfolio level
- **Constraints:** Applied in coordination with Risk Engine
- **Attribution:** Maintains mapping of exposure to source model

### Risk Engine

- **Hard Limits:** Per-asset (e.g., 40% NAV), per-class (e.g., crypto ≤ 20%), gross leverage (e.g., 1.2x)
- **Drawdown:** Automatic scaling or halt at threshold (e.g., 15-20% peak-to-trough)
- **Regime Scaling:** Budget adjustments based on regime state

### Execution Engine

- **Modes:** Backtest (offline), paper, live
- **Simulation:** Bar-based OHLC with configurable slippage and fees
- **Orders:** Market at next bar open by default; stops/limits within bar OHLC
- **Broker Adapters:** Alpaca (equities), Binance/Kraken (crypto)

### Optimization

- **Methods:** Grid/random search + evolutionary algorithm refinement
- **Metric:** Balanced Performance Score (BPS) = 0.4×Sharpe + 0.3×CAGR + 0.2×WinRate - 0.1×MaxDD
- **Config:** Parameter grids/distributions in YAML experiment files

## Technology Stack

- **Language:** Python
- **Data Storage:** Parquet (historical), SQLite/DuckDB (results)
- **Configuration:** YAML
- **Logging:** Structured JSON lines
- **Data Sources:**
  - Equities: Yahoo Finance (yfinance) or equivalent
  - Crypto: Binance/Kraken public APIs
  - Macro: FRED or equivalent
- **Brokers:**
  - Equities: Alpaca (paper + live)
  - Crypto: Binance/Kraken spot trading

## Code Organization

```
project/
  data/              # Parquet data (equities, crypto, macro)
  configs/           # YAML configs (base + experiments)
  models/            # Model implementations
  engines/           # Portfolio, Risk, Regime, Execution, Data, Optimization
  backtest/          # CLI/tools for backtests
  live/              # Paper/live trading runners
  utils/             # Shared helpers
  logs/              # Structured logs
  results/           # SQLite/DuckDB results
```

## Decision-Making Guidelines

### When Adding New Models

1. Must implement standard Context → target weights interface
2. Must declare universe, version, and configurable parameters in YAML
3. Must be testable in isolation (no dependencies on other models)
4. Should include version number and changelog

### When Modifying Engines

1. Must maintain backward compatibility with existing interfaces
2. Must not break model isolation or unified execution abstraction
3. Changes to risk constraints must be configurable via YAML
4. Performance impact must be measured and acceptable

### When Adding New Assets

1. Must have reliable data source with H4 and daily timeframes
2. Must have corresponding broker adapter implementation
3. Must define asset class and default risk constraints
4. Symbol mapping and precision handling in adapter layer

### When Changing Time Alignment

1. Must preserve no-look-ahead guarantee
2. Must document alignment rules in code and config
3. Must validate with backtest comparison tests
4. Daily features must align correctly to H4 bars

### When Optimizing Parameters

1. Must use Balanced Performance Score (BPS) unless explicitly overridden
2. Must use train/validation/test splits or walk-forward analysis
3. Must log full experiment config and results to database
4. Must version control experiment YAML files

## Non-Negotiable Requirements

1. **No look-ahead bias** in any data access or feature computation
2. **Risk Engine must enforce all limits** before execution
3. **All configs must be in YAML**, no hardcoded parameters in production
4. **All models use semantic versioning** and are traceable in results
5. **Unified execution interface** must work in backtest, paper, and live modes
6. **Structured logging** for all trades, orders, and performance events
7. **Reproducibility:** experiments must be fully reproducible from config + data
8. **Model isolation:** models cannot access other models or broker APIs directly

## Quality Standards

### Code Quality

- Type hints for all function signatures
- Docstrings for all public interfaces
- Unit tests for core logic (data alignment, risk constraints, portfolio aggregation)
- Integration tests for end-to-end backtest runs

### Performance

- H4 bar processing must complete in < 1 second for typical universe (5-10 assets)
- Feature computation should be vectorized where possible
- Backtest of 5 years of H4 data should complete in < 5 minutes

### Documentation

- Architecture diagrams for major components
- README with setup instructions
- Config file templates with comments
- Model documentation with logic descriptions

## Evolution Path

### Phase 1: Core Infrastructure (Current)

- Data pipeline and feature computation
- Model interface and v1 models
- Portfolio and Risk Engines
- Backtest execution
- YAML configuration

### Phase 2: Regime & Optimization

- Regime Engine implementation
- Grid/random search optimization
- Evolutionary algorithm refinement
- Results database and reporting

### Phase 3: Paper Trading

- Broker adapters (Alpaca, Binance/Kraken)
- Paper trading runner
- Live reconciliation and monitoring
- Cloud deployment setup

### Phase 4: Live Trading

- Live trading runner with kill switch
- Enhanced monitoring and alerting
- Performance tracking vs expectations
- Model promotion/demotion workflow

## Conclusion

This constitution defines the foundational principles, constraints, and standards for the algorithmic trading platform. All implementation decisions should be evaluated against these principles. When in doubt, prioritize:

1. **Safety** (risk controls, fail-safes)
2. **Reproducibility** (configs, versioning, logging)
3. **Modularity** (clean interfaces, independence)
4. **Simplicity** (clear abstractions, minimal coupling)

Deviations from this constitution must be explicitly justified and documented.
