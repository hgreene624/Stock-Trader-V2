# Research Protocol v2.0

**Purpose**: Ensure all experiments are reproducible and results are never lost.

---

## Golden Rules

1. **NO RESULT WITHOUT METADATA** - If metadata.json wasn't saved, it didn't happen
2. **VERIFY BEFORE DOCUMENTING** - Run the test, don't guess results
3. **UPDATE BEST_RESULTS.md** - This is the source of truth
4. **COMMIT CLEAN** - Results with "UNCOMMITTED CHANGES" warning are unreliable

---

## Before Any Experiment

### 1. Check Current Best
```bash
cat docs/research/BEST_RESULTS.md | head -30
```
Know what you're trying to beat: **17.64% CAGR** (as of 2025-11-23)

### 2. Check What's Been Tried
```bash
cat docs/research/experiments/INDEX.md
```
Don't repeat failed approaches!

### 3. Commit Any Changes
```bash
git status
# If dirty:
git add -A && git commit -m "WIP before experiment"
```

---

## Running an Experiment

### Step 1: Create Experiment Structure
```bash
EXP_ID="008"
EXP_NAME="your_experiment_name"
EXP_DIR="docs/research/experiments/${EXP_ID}_${EXP_NAME}"

mkdir -p "$EXP_DIR"/{v1_test,v2_test}/{analysis,config,logs}
```

### Step 2: Add Profile to profiles.yaml
```yaml
# In configs/profiles.yaml
exp008_v1_test:
  description: Experiment 008 - V1 test description
  model: YourModel
  # ... full config
```

### Step 3: Run Backtest
```bash
source .venv/bin/activate
python3 -m backtest.analyze_cli --profile exp008_v1_test 2>&1 | tee /tmp/exp008_v1.log

# Note the output directory (e.g., results/analysis/20251123_160000/)
```

### Step 4: Move Results to Experiment Folder (CRITICAL!)
```bash
# Find latest results
LATEST=$(ls -td results/analysis/*/ | head -1)

# Move to experiment folder
mv "$LATEST"/* "$EXP_DIR/v1_test/analysis/"
cp /tmp/exp008_v1.log "$EXP_DIR/v1_test/logs/"
cp "$EXP_DIR/v1_test/analysis/metadata.json" "$EXP_DIR/v1_test/config/"
```

### Step 5: Document Results
Create `$EXP_DIR/v1_test/README.md`:
```markdown
# V1: Test Name

## Hypothesis
What you're testing

## Results
- **CAGR**: [from metadata.json]
- **Sharpe**: [from metadata.json]
- **Max DD**: [from metadata.json]

## Conclusion
PASSED/FAILED - Why
```

---

## After Experiment

### If Result Beats Current Champion

1. **Verify reproducibility** - Run again, same result?
2. **Update BEST_RESULTS.md** - New champion section
3. **Commit together**:
```bash
git add docs/research/BEST_RESULTS.md configs/profiles.yaml
git add docs/research/experiments/${EXP_ID}_${EXP_NAME}/
git commit -m "New champion: [Model] @ [CAGR]% from experiment ${EXP_ID}"
```

### If Result is Worse

1. **Still document it** - Failed approaches are valuable
2. **Add to Failed Approaches** in BEST_RESULTS.md if it's a general pattern
3. **Commit the experiment**:
```bash
git add docs/research/experiments/${EXP_ID}_${EXP_NAME}/
git commit -m "Experiment ${EXP_ID}: [summary] - FAILED"
```

---

## Validation Checklist

Before claiming any result, verify:

- [ ] metadata.json exists in analysis folder
- [ ] metadata.json has non-null metrics (cagr, sharpe, etc.)
- [ ] Profile exists in configs/profiles.yaml
- [ ] Result is reproducible (run twice, same output)
- [ ] Git is clean (no uncommitted changes warning)
- [ ] README documents hypothesis and conclusion

---

## Common Mistakes to Avoid

### 1. Documenting without running
**Wrong**: "V1 should give 17% CAGR based on theory"
**Right**: Run test, read metadata.json, document actual result

### 2. Leaving results in results/analysis/
**Wrong**: `results/analysis/20251123_123456/metadata.json`
**Right**: `docs/research/experiments/008_test/v1/analysis/metadata.json`

### 3. Not saving the profile
**Wrong**: Modify profile, run test, modify again
**Right**: Each test has its own profile saved in profiles.yaml

### 4. Trusting old documentation
**Wrong**: "README says 17.78% so that's the best"
**Right**: Run `python3 -m backtest.analyze_cli --profile X` to verify

---

## Quick Commands

### Find all results by CAGR
```bash
python3 << 'EOF'
import json
from pathlib import Path
results = []
for f in Path(".").rglob("**/analysis/**/metadata.json"):
    try:
        data = json.load(open(f))
        if data.get("metrics", {}).get("cagr"):
            m = data["metrics"]
            results.append((m["cagr"]*100, m["sharpe_ratio"],
                          data["model"], data.get("reproducibility",{}).get("profile_name","?")))
    except: pass
for r in sorted(results, reverse=True)[:10]:
    print(f"{r[0]:.2f}% | {r[1]:.3f} | {r[2]} | {r[3]}")
EOF
```

### Verify a documented result
```bash
python3 -m backtest.analyze_cli --profile [profile_name] 2>&1 | grep "CAGR\|Sharpe"
```

### Check for uncommitted changes
```bash
git status --short
```

---

## File Locations Summary

| What | Where |
|------|-------|
| **Current best results** | `docs/research/BEST_RESULTS.md` |
| **All profiles** | `configs/profiles.yaml` |
| **Experiment index** | `docs/research/experiments/INDEX.md` |
| **Experiment details** | `docs/research/experiments/XXX_name/` |
| **Quick start guide** | `CLAUDE.md` |

---

*Follow this protocol. No exceptions. Lost results are unacceptable.*
