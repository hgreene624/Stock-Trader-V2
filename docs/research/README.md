# Trading Platform Research

Central repository for all trading strategy research, experiments, and findings.

## Quick Links

### Core Documentation
- [RESEARCH_SUMMARY.md](RESEARCH_SUMMARY.md) - Executive summary of all research
- [WHAT_WORKED.md](WHAT_WORKED.md) - Proven strategies and approaches
- [WHAT_FAILED.md](WHAT_FAILED.md) - Failed approaches to avoid
- [NEXT_STEPS.md](NEXT_STEPS.md) - Research roadmap and priorities

### Organized Sections

| Folder | Contents |
|--------|----------|
| [experiments/](experiments/) | Systematic experiments with full documentation |
| [agents/](agents/) | Agent workflows and context for AI-driven research |
| [reports/](reports/) | One-off analysis reports |
| [Personal Research/](Personal%20Research/) | Personal notes and ideas |

## Current Status

**Goal**: Beat SPY's 14.34% CAGR (2020-2024)

**Best Result**: SectorRotationVIX_v1 @ **14.11% CAGR** (within 0.23% of target)

**Next Action**: Paper trade VIX-based model with 1.5x base leverage

## Adding New Research

### For Experiments
Create a new folder in `experiments/` with:
```
experiments/
└── 00X_experiment_name/
    ├── README.md           # Main results
    └── [supporting files]
```

### For Reports
Add one-off analysis to `reports/`:
```
reports/
└── YYYY-MM-DD_report_name.md
```

### For Agent Docs
Add agent-related documentation to `agents/`
