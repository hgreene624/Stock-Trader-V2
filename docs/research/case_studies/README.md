# Case Studies

Documented failures and lessons learned from trading strategy research.

## Index

| Case Study | Date | Key Finding |
|------------|------|-------------|
| [Single Year Validation Failure](CASE_STUDY_SINGLE_YEAR_VALIDATION_FAILURE.md) | 2025-11-24 | Bull market validation (2024) gives false confidence |
| [Momentum Bear Market Failure](CASE_STUDY_MOMENTUM_BEAR_MARKET_FAILURE.md) | 2025-11-24 | Momentum strategies fundamentally fail in bear markets |

## Key Lessons

1. **Bear market validation is essential** - Single-year bull market validation is insufficient
2. **Strategy architecture > parameter optimization** - Can't fix broken strategies with EA tuning
3. **Leverage amplifies but doesn't cause problems** - No leverage was worse (232% vs 185%)
4. **Regime detection must change behavior** - Not just parameters, but strategy entirely
