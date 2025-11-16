# Master System Specification (v1.0)

## 0. Overview

This document specifies the architecture for a **multi-model, multi-asset algorithmic trading platform** designed to:

- Combine multiple strategy models (equities trend, index mean reversion, crypto momentum)
- Run regime-aware, risk-controlled portfolios
- Support research, backtesting, paper trading, and live trading
- Be controlled via **YAML configs** and be **Speckit-friendly**

Key design choices:

- **Timeframes:**  
  - Primary clock: **4-hour (H4)** bars  
  - Secondary: **Daily** data as slow features and regime inputs
- **Assets:**  
  - Equities: ETFs (e.g., SPY, QQQ) via **Alpaca**  
  - Crypto: BTC, ETH (and possibly more) via **Binance/Kraken**
- **Models v1:**  
  - `EquityTrendModel_v1`  
  - `IndexMeanReversionModel_v1`  
  - `CryptoMomentumModel_v1`
- **Core abstractions:**  
  - **Data & Feature Layer**  
  - **Models (alpha engines)**  
  - **Portfolio Engine**  
  - **Risk Engine**  
  - **Regime Engine**  
  - **Execution / Backtest Engine**  
  - **Experiment & Optimization Layer**  
  - **Logging & Reporting**

---

## 1. Directory Layout

Project uses a **classic clean architecture**:

```text
project/
  data/              # all historical & derived data (Parquet)
    equities/
    crypto/
    macro/
  configs/           # YAML configs (base + experiments)
    base/
    experiments/
  models/            # model implementations (trend, mean-rev, crypto, etc.)
  engines/
    portfolio/
    risk/
    regime/
    execution/
    data/            # data & feature pipeline
    optimization/    # grid/random/EA optimizer components
  backtest/          # CLI/tools for backtests & research
  live/              # paper/live trading runners
  utils/             # shared helpers (logging, serialization, metrics)
  logs/              # structured JSON logs
  results/           # SQLite/DuckDB databases for backtest results
```

---

## 2. Data & Feature Layer

### 2.1. Data Sources (v1)

- **Equities (daily, H4):**  
  - Source: Yahoo Finance (via `yfinance`) or equivalent free API  
- **Crypto (H4, daily):**  
  - Source: public exchange APIs (Binance/Kraken)  
- **Macro:**  
  - Source: FRED or similar free APIs (e.g., yield curve, PMI or analogous business condition indicator)

All historical data is downloaded and stored **locally**.

### 2.2. Storage Format & Layout

- Use **Parquet** as the canonical on-disk format.
- **Asset-per-file structure** per timeframe, e.g.:

```text
data/
  equities/
    SPY_daily.parquet
    SPY_h4.parquet
    QQQ_daily.parquet
    QQQ_h4.parquet
  crypto/
    BTC_h4.parquet
    ETH_h4.parquet
  macro/
    yield_curve.parquet
    pmi.parquet
```

### 2.3. Time Handling

- **Primary clock:** H4 bars.  
- **Daily data:** downsampled or joined as features at the relevant H4 timestamps:
  - Daily indicators (e.g., 200D MA, daily momentum) are treated as slow-moving features.
  - Regime flags are usually computed from daily data.

### 2.4. Feature Pipeline (Centralized)

The feature pipeline is centralized and runs **before** models:

- For each asset/timeframe, compute standard features:
  - Returns (1, 4, 20 bars etc.)
  - Moving averages (e.g., 20, 50, 100, 200 periods)
  - Volatility (ATR, rolling std dev)
  - RSI, Bollinger Bands, etc.
- For macro series:
  - Derived indicators (yield curve slope, PMI trend, etc.)
- For regimes:
  - Inputs and thresholds for Regime Engine.

All features are stored in Parquet or derived in-memory from Parquet base series.

### 2.5. Data Access for Models

Models **never** load raw files directly. They receive a **Context** object that includes:

- Current H4 bar for each asset in its universe
- Recent historical window (e.g., last N bars) as feature arrays/objects
- Daily features aligned to current H4 bar
- Regime snapshot
- Model-attributed exposure summary
- Budget information

Time alignment rules:

- No look-ahead: only past and current bars/values.
- Missing data handled via forward-fill or model-configurable policies.

---

## 3. Model Layer (Alpha Engines)

### 3.1. Model Concept

A **Model** is a pluggable, self-contained “trading brain” that:

- Receives market state, features, regime, and its budget
- Does **not** know about other models or broker details
- Outputs a **desired exposure vector in target weights**, relative to its budget

Models do not submit raw orders; they express **intent** in terms of target weights.

### 3.2. Model Interface (Conceptual)

Per decision step (each H4 bar):

**Inputs (via Context):**

- `timestamp`
- For each asset in the model’s universe:
  - Current bar features (prices, indicators)
  - Recent history slice (for internal logic)
- Regime snapshot:
  ```json
  {
    "equity_regime": "BULL" | "BEAR" | "NEUTRAL",
    "vol_regime": "LOW" | "NORMAL" | "HIGH",
    "crypto_regime": "RISK_ON" | "RISK_OFF",
    "macro_regime": "EXPANSION" | "SLOWDOWN" | "RECESSION" | ...
  }
  ```
- Model budget:
  - `budget_fraction` (e.g., 0.6 = 60% of NAV)
  - `budget_value` (computed from NAV)
- Current model-attributed exposures (per asset in its universe)

**Outputs:**

- **Desired exposure vector (relative to model budget)**, e.g.:
  ```json
  {
    "SPY": 0.40,
    "QQQ": 0.20
  }
  ```
  - Unspecified assets are implicitly 0 (or “no opinion” per convention).
- Optional hints:
  - Confidence / urgency scores per asset
  - Expected holding horizon

### 3.3. v1 Models

#### 3.3.1. EquityTrendModel_v1

- **Universe:** SPY, QQQ (initially)
- **Objective:** Capture sustained uptrends in broad equities; reduce exposure in downtrends.
- **Core logic (conceptual):**
  - Use daily 200D MA and daily momentum to define trend & regime gate.
  - Example rule:
    - Trend “on” when price > 200D MA and 3–12 month momentum > 0.
    - Allocate to SPY/QQQ based on relative strength.
- **Output:** Long-only target weights (relative to model budget).

#### 3.3.2. IndexMeanReversionModel_v1

- **Universe:** SPY, QQQ
- **Objective:** Exploit short-term overbought/oversold in highly liquid indices.
- **Core logic (conceptual):**
  - Use H4 features: RSI(2–5), Bollinger Bands, recent returns.
  - Identify oversold dips, enter small long positions, exit on mean reversion or time stop.
- **Output:** Small, short-duration long positions in SPY/QQQ (relative to model budget).

#### 3.3.3. CryptoMomentumModel_v1

- **Universe:** BTC, ETH (expandable later)
- **Objective:** Weekly momentum rotation across strong crypto assets during risk-on crypto regimes.
- **Core logic (conceptual):**
  - Weekly schedule based on daily momentum (e.g., 30–60D returns).
  - Crypto regime gating (BTC > 200D MA and positive momentum → RISK_ON).
  - Allocate evenly across top N momentum coins.
- **Output:** Long-only target weights in selected cryptos (relative to model budget). Flat when `crypto_regime = RISK_OFF`.

---

## 4. Portfolio Engine

### 4.1. Purpose

The Portfolio Engine:

- Receives desired exposure vectors from all models (relative to their budgets)
- Converts them to NAV-relative targets
- Aggregates across models
- Applies global constraints (in coordination with Risk Engine)
- Produces a **single target portfolio**
- Generates delta-based trade instructions for Execution Engine
- Maintains attribution mapping (which exposure came from which model)

### 4.2. Inputs

- Global state:
  - Total NAV
  - Current portfolio positions and cash
- Models registry:
  - Active models, their budgets, their parameters & version
- Model desired exposure vectors (per model)
- Regime snapshot
- Risk Engine constraints and outputs

### 4.3. Algorithm (Conceptual)

1. **Normalize model outputs to NAV terms:**

   For each model `m`:
   - For each asset `a`, desired weight `w_m(a)` (0–1 of model budget)
   - Model budget fraction `B_m` (0–1 of NAV)
   - Contribution to NAV for asset `a`:
     ```
     W_m_NAV(a) = B_m * w_m(a)
     ```

2. **Aggregate across models:**

   For each asset `a`:
   ```
   W_total_raw(a) = Σ_m W_m_NAV(a)
   ```

   Conflicting signals are allowed; exposures are **netted** at the portfolio level.

3. **Apply global constraints (with Risk Engine):**

   - Per-asset caps (e.g., max 40% NAV in SPY)
   - Per-asset class caps (e.g., crypto ≤ 20% NAV)
   - Max gross/net leverage (e.g., 1.2x)
   - Regime-based budget adjustments:
     - E.g., in equity BEAR regime, automatically reduce equity model budgets.

4. **Compute final target portfolio:**

   - Possibly scaled version of `W_total_raw(a)` after risk adjustments:
     ```
     W_target(a)
     ```

   - Unallocated weight is **cash**.

5. **Generate execution instructions:**

   - Compare `W_target(a)` vs current weights:
     - Delta = `W_target(a) - W_current(a)`
   - Convert deltas into high-level trade instructions:
     - “Increase SPY by x% of NAV”
     - “Reduce BTC to 0”
   - Send instructions to Execution Engine via unified abstraction.

---

## 5. Risk Engine

### 5.1. Purpose (v1: Core Risk Only)

Risk Engine acts as the **system-wide enforcer** of basic risk controls.

### 5.2. Inputs

- Proposed aggregated portfolio weights from Portfolio Engine
- Current portfolio positions, NAV, P&L, drawdown
- Model budgets and contributions
- Global risk settings (from config)
- Regime snapshot (for regime-aware scaling)

### 5.3. Controls (v1)

- **Per-trade risk cap:**  
  - Max % of NAV risked per position based on stop estimate.
- **Per-asset exposure cap:**  
  - Max fraction of NAV per asset (e.g., 40%).
- **Asset class caps:**  
  - E.g., crypto ≤ 20% NAV.
- **Max leverage:**  
  - E.g., gross notional ≤ 1.2 × NAV.
- **Global drawdown limit:**  
  - If peak-to-trough drawdown exceeds threshold (e.g., 15–20%):
    - Reduce all exposures by a factor (e.g., 50%) OR
    - Enter “capital preservation” mode (no new entries).

### 5.4. Outputs

- Adjusted target weights `W_target(a)` that satisfy all constraints
- Flags or status to Master Strategy:
  - E.g., `risk_mode = NORMAL | REDUCED | HALT`
- Diagnostic metrics for logging and reporting.

---

## 6. Regime Engine

### 6.1. Purpose

Regime Engine classifies **market conditions** so the rest of the system can adapt:

- Equity regime
- Volatility regime
- Crypto regime
- Lightweight macro regime

It does not trade directly.

### 6.2. Inputs

- Daily equity index data (e.g., SPY)
  - Price vs 200D MA
  - Multi-month momentum
- Volatility data:
  - VIX or realized volatility
- Crypto data:
  - BTC daily price vs 200D MA
  - BTC momentum
- Macro data (lightweight):
  - Yield curve slope (e.g., 10Y–2Y)
  - PMI (or similar business condition indicator)

### 6.3. Regime Classification (Example Logic)

- **Equity Regime:**
  - BULL: SPY price > 200D MA and 6–12M momentum positive
  - BEAR: SPY price < 200D MA or 6–12M momentum negative
  - NEUTRAL: Otherwise

- **Volatility Regime:**
  - HIGH: VIX > threshold
  - LOW/NORMAL: VIX below threshold

- **Crypto Regime:**
  - RISK_ON: BTC > 200D MA and 60D momentum positive
  - RISK_OFF: otherwise

- **Macro Regime (lightweight):**
  - EXPANSION: PMI > 50 and yield curve slope normal/positive
  - SLOWDOWN/RECESSION: PMI <= 50 and/or persistent inverted yield curve

### 6.4. Outputs

- Structured **regime state**:
  ```json
  {
    "equity_regime": "BULL",
    "vol_regime": "NORMAL",
    "crypto_regime": "RISK_ON",
    "macro_regime": "EXPANSION"
  }
  ```

Used by:

- Portfolio Engine (budget shifts, risk scaling)
- Risk Engine (extra conservatism in bad regimes)
- Models (if they choose to use regime gating explicitly)

---

## 7. Execution / Backtest Engine

### 7.1. Purpose

- Handle **order translation**, **simulation**, and **broker integration**.
- Support three modes:
  - Research backtest (offline)
  - Paper trading
  - Live trading

### 7.2. Unified Abstraction Layer

Expose a simple, broker-agnostic interface:

- `submit_target_weights({symbol: target_weight})`
- `get_positions()`
- `get_cash()`
- `get_nav()`
- `get_broker_metadata()`

Broker-specific **adapters** implement this over:

- **Alpaca** (equities)
- **Binance/Kraken** (crypto)

### 7.3. Backtest Execution Model (v1)

- **Bar-based intrabar simulation using OHLC:**
  - Strategy decisions occur at bar close or bar open (configurable).
  - Orders can be simulated as:
    - Market at next bar's open
    - Triggered by price reaching stops/limits within bar’s OHLC
  - Simple, deterministic slippage and fee models:
    - E.g., fixed bps per trade per asset class.

### 7.4. Live & Paper Trading

- **Paper:**
  - Use brokers’ paper endpoints where available (e.g., Alpaca paper).
  - For crypto, simulate filling but use live order book data where possible.

- **Live:**
  - Same abstraction, but orders go to real broker APIs.
  - Positions and P&L continuously reconciled with broker.

### 7.5. Overnight Handling

- **Default:** positions may be held overnight; no special de-risk logic in v1.

---

## 8. Experiment, Optimization & Configuration

### 8.1. Configuration Format

- All system and experiment configs use **YAML**.

Base config example (conceptual):

```yaml
universe:
  equities: [SPY, QQQ]
  crypto: [BTC, ETH]

models:
  equity_trend:
    version: 1.0.0
    budget: 0.6
    parameters:
      fast_ma: 50
      slow_ma: 200
  index_mean_reversion:
    version: 1.0.0
    budget: 0.25
    parameters:
      rsi_period: 2
  crypto_momentum:
    version: 1.0.0
    budget: 0.15
    parameters:
      momentum_lookback_days: 60

regime_budgets:
  # example: budgets by regime
  equity_bull:
    equity_trend: 0.7
    index_mean_reversion: 0.2
    crypto_momentum: 0.1
  equity_bear:
    equity_trend: 0.2
    index_mean_reversion: 0.4
    crypto_momentum: 0.05
```

### 8.2. Experiment & Override Files

- Base YAML describes the default system.
- **Experiment YAML** files override specific fields:

```yaml
# configs/experiments/trend_sweep.yaml
models:
  equity_trend:
    parameters:
      fast_ma: [20, 30, 50]
      slow_ma: [100, 150, 200]
```

The system merges base configs with experiment overrides.

### 8.3. Optimization & HPO

- v1 supports a **hybrid optimization pipeline**:

  1. **Grid / Random Search:**
     - Parameter grids or distributions defined in YAML.
     - Multiple runs across combinations or random samples.
  2. **Evolutionary Algorithm (EA) Refinement:**
     - Use top-performing parameter sets (by score) as seeds.
     - Apply EA (selection, crossover, mutation) to refine parameters.

### 8.4. Objective Metric: Balanced Performance Score (BPS)

Optimization maximizes:

```text
Score = 0.40 * Sharpe
      + 0.30 * CAGR
      + 0.20 * WinRate
      - 0.10 * MaxDrawdown
```

Where:

- Sharpe: annualized Sharpe ratio
- CAGR: compound annual growth rate
- WinRate: fraction of winning trades
- MaxDrawdown: % maximum drawdown (higher is worse)

---

## 9. Logging, Metrics & Reporting

### 9.1. Storage of Backtest Results

- Primary store: **SQLite or DuckDB** databases under `results/`.
- Each experiment run inserts:
  - Experiment metadata (config, date, models, versions)
  - Portfolio-level performance metrics
  - Per-model performance metrics
  - References to generated plots (if any)

### 9.2. Logging

- **Structured logging** preferred:
  - JSON lines with fixed fields:
    - Timestamp
    - Component (engine/model)
    - Level (info/warn/error)
    - Message
    - Additional context (symbols, P&L, etc.)

- Separate log streams:
  - `trades.log` – executed trades and fills
  - `orders.log` – orders sent to broker/backtest engine
  - `performance.log` – periodic performance snapshots
  - `errors.log` – errors/exceptions

### 9.3. Reporting (Expanded)

For each run:

- Equity curve (portfolio and per-model)
- Drawdown curve
- Per-model return series
- Per-asset return contribution (optional)
- Rolling Sharpe/Sortino (optional)
- Turnover statistics
- Regime alignment metrics (e.g., performance in BULL vs BEAR)

---

## 10. Broker Integration & Deployment

### 10.1. Broker Adapters

- **Alpaca Adapter:**
  - For U.S. equities (SPY, QQQ, etc.)
  - Supports:
    - Market/limit orders
    - Paper and live endpoints
    - Account/positions/NAV queries

- **Binance/Kraken Adapter:**
  - For crypto assets (BTC, ETH, others as added)
  - Handles:
    - Spot trading
    - Fees and min order sizes
    - Symbol mapping & precision

Adapters conform to the unified execution interface.

### 10.2. Deployment Model

- **Local environment:** research + backtests
  - Run historical simulations and experiments locally.
- **Cloud environment (VPS/VM):** paper + live trading
  - Stable internet connection
  - Persistent environment
  - Same codebase, different config mode (`paper` vs `live`).

Environment-specific config is controlled via YAML.

---

## 11. Model Lifecycle & Versioning

### 11.1. Semantic Versioning

Each model uses **semantic versioning**:

- `MAJOR.MINOR.PATCH`, e.g.:
  - `EquityTrendModel_v1.0.0`
  - `EquityTrendModel_v1.1.0` (non-breaking enhancement)
  - `EquityTrendModel_v2.0.0` (breaking change)

### 11.2. Lifecycle Stages

1. **Research:**  
   - Develop and test models locally via backtests + optimization.
2. **Candidate:**  
   - Selected parameter sets and versions promoted to candidate.
3. **Paper Trading:**  
   - Candidate models run in paper mode on cloud.
   - Performance evaluated vs expectations.
4. **Live Trading:**  
   - Models that satisfy risk and performance criteria are allowed to trade real capital.

Promotion/demotion is controlled manually via YAML configs and tagging in results DB.

---

## 12. Safety & Failsafes

- Global drawdown limit triggers exposure scaling or halt.
- Broker adapters must:
  - Validate orders against broker constraints (min size, trading hours, etc.).
  - Handle errors and retries safely.
- System must:
  - Avoid overlapping conflicting live + backtest accesses to the same account.
  - Provide a “kill switch” in config or external command to stop trading.

---

## 13. Summary

This system is designed to be:

- **Modular:** Models, engines, and adapters are independent components.
- **Multi-model:** Supports multiple strategies simultaneously (trend, mean-reversion, crypto).
- **Multi-asset:** Equities via Alpaca, crypto via Binance/Kraken.
- **Regime-aware:** Uses technical + lightweight macro regimes to adapt budgets and risk.
- **Optimizable:** Built-in grid/random + evolutionary parameter search using a composite performance score.
- **Reproducible:** YAML configs + Parquet data + SQLite/DuckDB results + structured logs.
- **Deployable:** Local research + cloud paper/live, all using the same abstractions.

This specification is the basis for:

- Implementation tasks and code generation.
- The Speckit System Spec Prompt.
- The Speckit Plan Prompt (implementation roadmap).

# End of Master System Specification v1.0
