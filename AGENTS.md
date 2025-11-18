# Repository Guidelines

## Project Structure & Module Organization
- `engines/` bundles the reusable subsystems (data, portfolio, risk, regime, optimization, execution) and CLIs; most workflows start here.
- `models/` mixes the shared contracts in `base.py` with shipped strategies such as `sector_rotation_v1.py`; reusable helpers live in `utils/`.
- `backtest/` runs sims, `live/` handles paper/live, and configs (`base/`, `experiments/`, `profiles.yaml`) sit in `configs/`; inputs stay in `data/` and artifacts in `results/`/`logs/`.

## Build, Test, and Development Commands
- `python -m engines.data.cli download --symbols SPY,QQQ --start-date 2020-01-01 --timeframe 1D` refreshes equity data before model work.
- `python -m backtest.cli list-profiles` and `python -m backtest.cli create-profile --name sector_rotation_fast --model SectorRotationModel_v1 --params "momentum_period=60,top_n=4"` manage scenarios without editing YAML.
- `python -m backtest.cli run --profile sector_rotation_default --format json --start 2020-01-01 --end 2024-12-31` is the main evaluation loop; JSON output powers `/analyze`.
- Keep gates green with `python validate_pipeline.py`, `pytest tests/unit`, `pytest tests/integration -k backtest`, then log hypotheses/results via `python -m utils.experiment_tracker log ...`.

## Coding Style & Naming Conventions
- Follow 4-space indentation, explicit type hints, and dataclasses as modeled in `models/base.py`; keep side effects corralled.
- Use `snake_case` files/configs/functions, `CapWords` classes, `UPPER_SNAKE` constants, and `exp_<###>_<slug>.yaml` names while logging through `utils/logging.py`.
- Generate new strategies with `python -m backtest.cli create-model --template <template> --name <Model>` so naming and registration remain consistent.

## Testing Guidelines
- Every change needs unit coverage plus the relevant integration path (e.g., `tests/integration/test_backtest_workflow.py`).
- Write tests as `test_<component>_<condition>_<result>`, reuse fixtures to satisfy indicator lookbacks, and ensure data windows exceed the longest MA or momentum period.
- Before review, rerun pytest, `python validate_pipeline.py`, and one representative `backtest.cli run`, then log Sharpe, CAGR, drawdown, and SPY alpha (target: >14.63% CAGR, Sharpe >1.5) in `results/` or the tracker.

## Commit & Pull Request Guidelines
- Keep commit subjects short, lower-case, and imperative (`sub agents created`, `phase 8 done`) and list touched subsystems, configs, and deltas in the body.
- PRs must state motivation, link specs/issues, attach validation artifacts (CLI output, JSON, screenshots), and explain how the work narrows the “beat SPY in absolute + risk-adjusted terms” gap.
- Document dependencies on new profiles, templates, or data downloads so `/test` and `/optimize` agents can reproduce quickly.

## Agent Workflow Tips
- Default to CLI helpers (`list-profiles`, `create-profile`, `create-model`, JSON output`) instead of manual edits so metadata stays consistent across agents.
- Log each run with the experiment tracker and revisit `AGENT_README.md`/`AGENT_FEATURES.md`/`SUB_AGENTS.md` when switching roles (`/test`, `/analyze`, `/research`).
