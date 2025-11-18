# Documentation Change Log

A running log of notable doc updates so future agents know where major changes landed.

## 2025-11-17 – Platform Review
- Synced CLAUDE.md, README.md, and AGENT_README.md to the latest performance numbers (SectorRotationModel_v1 @ 13.01% CAGR vs SPY 14.34%).
- Added full walk-forward coverage: methodology guide, implementation notes, CLI usage, and decision rules for promotion vs rejection.
- Logged the walk-forward and `hold_current` breakthroughs plus recent session highlights so agents can trace why leverage + stability controls matter.

## 2024-11-17 – Workflow Refresh
- `docs/guides/quickstart.md` gained the 10-minute “Express” path, troubleshooting updates, and better links into `docs/guides/workflow_guide.md`.
- CLAUDE.md flipped to a profile-first workflow, refreshed configuration references, and introduced the profile catalog + workflow guide cross-links.
- Documented the config/profile refactor and ensured both guides reference the new iteration loop, auto-download behavior, and `show-last` command.
