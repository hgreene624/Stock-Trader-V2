# Model Versioning & Reproducibility Guide

## Why This Exists

On November 20, 2025, we achieved a **19.73% CAGR** result with SectorRotationAdaptive_v3 - significantly beating SPY's 14.34%. However, this code was:
1. Never committed to git
2. Modified before being committed
3. Lost forever

We cannot reproduce this result because the original code no longer exists. This guide ensures this never happens again.

---

## Core Principles

### 1. Never Modify Existing Models

When you need to change a model's behavior:

**WRONG:**
```python
# Editing models/sector_rotation_v1.py directly
# This destroys the original model's reproducibility
```

**RIGHT:**
```python
# Create models/sector_rotation_v2.py with changes
# Original v1 remains untouched and reproducible
```

### 2. Always Commit Before Testing

The backtest CLI will warn you:
```
⚠️  UNCOMMITTED CHANGES - Results may not be reproducible!
```

If you see this warning:
1. **STOP** - do not proceed with the test
2. Commit your changes: `git add . && git commit -m "Add model_v2"`
3. Then run the test

### 3. Every Result Must Be Reproducible

Each backtest automatically saves:
- `metadata.json` - Git commit, parameters, full config
- `model_source.py` - Complete model source code at time of test
- `temp_config.yaml` - Exact configuration used

---

## Step-by-Step: Creating a New Model Version

### Step 1: Copy the Existing Model

```bash
cp models/sector_rotation_v1.py models/sector_rotation_v2.py
```

### Step 2: Update the New Model

Edit `models/sector_rotation_v2.py`:

```python
"""
SectorRotationModel_v2

Changes from v1:
- Updated rebalancing from 7 days to 21 days (EXP-001)
"""

class SectorRotationModel_v2(BaseModel):
    def __init__(
        self,
        model_id: str = "SectorRotationModel_v2",  # Update default
        ...
    ):
        ...
        super().__init__(
            name=model_id,
            version="2.0.0",  # Update version
            universe=self.all_assets
        )
```

### Step 3: Register in analyze_cli.py

Add import:
```python
from models.sector_rotation_v2 import SectorRotationModel_v2
```

Add instantiation case:
```python
elif model_name == "SectorRotationModel_v2":
    return SectorRotationModel_v2(**parameters)
```

### Step 4: Create Test Profile

Add to `configs/profiles.yaml`:
```yaml
sector_rotation_v2_default:
  description: Sector rotation v2 with 21-day rebalancing
  model: SectorRotationModel_v2
  universe:
    - XLK
    - XLF
    # ... rest of universe
  start_date: '2020-01-01'
  end_date: '2024-12-31'
  parameters: {}
```

### Step 5: Commit Everything

```bash
git add models/sector_rotation_v2.py
git add backtest/analyze_cli.py
git add configs/profiles.yaml
git commit -m "Add SectorRotationModel_v2 with 21-day rebalancing"
```

### Step 6: Run Test

```bash
python3 -m backtest.analyze_cli --profile sector_rotation_v2_default
```

---

## What Gets Logged

Every backtest now saves full reproducibility info in `metadata.json`:

```json
{
  "model": "SectorRotationModel_v2",
  "metrics": { ... },
  "reproducibility": {
    "git_commit": "abc123...",
    "git_dirty": false,
    "profile_name": "sector_rotation_v2_default",
    "parameters": {
      "momentum_period": 126,
      "top_n": 3
    },
    "full_config": { ... }
  }
}
```

Plus `model_source.py` contains the exact model code used.

---

## Naming Conventions

### Model Files
```
models/{strategy}_{variant}_v{version}.py

Examples:
- sector_rotation_v1.py
- sector_rotation_bull_v1.py
- sector_rotation_adaptive_v3.py
```

### Version Increments
- **Major version (v1 → v2)**: Logic changes, parameter defaults, behavior changes
- **Same version, different params**: Use profiles, not new model files

### When to Create New Version vs Use Profile

**Create new version when:**
- Changing model logic (e.g., different momentum calculation)
- Changing rebalancing frequency in code
- Adding/removing features
- Changing default parameters

**Use profile parameters when:**
- Testing different parameter values
- Temporary experiments
- Comparing configurations

---

## Common Mistakes to Avoid

### Mistake 1: Editing an Existing Model
```bash
# BAD
vim models/sector_rotation_v1.py
python3 -m backtest.analyze_cli --profile sr_v1_test
# Result cannot be compared to previous v1 results
```

### Mistake 2: Testing Uncommitted Code
```bash
# BAD
vim models/sector_rotation_v2.py
python3 -m backtest.analyze_cli --profile sr_v2_test
# Warning: UNCOMMITTED CHANGES
# If results are good, you might lose this code
```

### Mistake 3: Not Registering New Models
```bash
# BAD
cp models/sr_v1.py models/sr_v2.py
vim models/sr_v2.py
# Forgot to register in analyze_cli.py
python3 -m backtest.analyze_cli --profile sr_v2_test
# Error: Unknown model: SectorRotationModel_v2
```

---

## Recovering Lost Results

If you have results but lost the code:

1. Check `results/analysis/{timestamp}/model_source.py` - contains full model code
2. Check `results/analysis/{timestamp}/metadata.json` - contains git commit
3. If commit exists: `git show {commit}:models/{model_file}.py`

If neither exists, the result is **not reproducible** and should be treated as unreliable.

---

## Checklist for Every Model Change

- [ ] Created new version file (not edited existing)
- [ ] Updated class name and model_id default
- [ ] Updated version number in `__init__`
- [ ] Updated docstring with changes from previous version
- [ ] Registered import in `backtest/analyze_cli.py`
- [ ] Added elif case in `instantiate_model()`
- [ ] Created test profile in `configs/profiles.yaml`
- [ ] Committed all changes to git
- [ ] Verified no "UNCOMMITTED CHANGES" warning when testing

---

## Summary

1. **Never modify existing models** - create new versions
2. **Always commit before testing** - heed the warning
3. **Results without reproducibility info are worthless**

Following these rules ensures every result can be recreated, every experiment can be verified, and no research is ever lost.
