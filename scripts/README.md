# Scripts Directory

> **Last Updated**: 2025-11-26

Utility scripts for the trading platform.

## Available Scripts

### 🔬 Walk-Forward Optimization Monitoring

Run EA walk-forward optimization in a new Terminal tab for real-time progress monitoring.

```bash
# Quick mode (recommended for testing) - ~10-15 minutes
./scripts/run_walk_forward_new_tab.sh

# Full mode (production) - ~30-60 minutes
./scripts/run_walk_forward_new_tab.sh --full
```

**What you'll see:**
- New Terminal tab opens automatically
- Real-time progress updates every backtest
- Time estimates (elapsed and remaining)
- Best BPS scores per generation
- Final summary with recommended parameters

### 🚀 General New Tab Launcher

Run any command in a new Terminal tab:

```bash
./scripts/run_in_new_tab.sh "your-command-here"

# Examples:
./scripts/run_in_new_tab.sh "python3 -m backtest.cli run --profile my_test_1"
./scripts/run_in_new_tab.sh "pytest tests/ -v"
./scripts/run_in_new_tab.sh "python3 -m engines.optimization.cli run --experiment configs/experiments/exp_001.yaml"
```

### 🧪 Test New Tab Functionality

Verify the new tab feature works on your system:

```bash
./scripts/test_new_tab.sh
```

**Expected result:** New Terminal tab opens with message "✅ New tab works!"

## Direct CLI Usage (Alternative)

You can also use the `--new-tab` flag directly with the walk-forward CLI:

```bash
# Quick mode
python3 -m engines.optimization.walk_forward_cli --quick --new-tab

# Full mode
python3 -m engines.optimization.walk_forward_cli --new-tab

# With custom parameters
python3 -m engines.optimization.walk_forward_cli \
    --train-months 24 \
    --test-months 12 \
    --population 30 \
    --generations 20 \
    --new-tab
```

## How It Works

All scripts use AppleScript to control Terminal.app on macOS:

1. Opens new Terminal tab (⌘T)
2. Changes to project directory
3. Activates Python virtual environment
4. Runs your command with real-time output

## Requirements

- **Platform**: macOS (Terminal.app)
- **Python**: Virtual environment at `.venv/`
- **Permissions**: Terminal.app needs Accessibility permissions (System Preferences → Security & Privacy → Accessibility)

## Troubleshooting

### "Terminal is not allowed to send keystrokes"

**Fix**: Grant Terminal.app Accessibility permissions
1. System Preferences → Security & Privacy → Accessibility
2. Click lock to make changes
3. Add Terminal.app
4. Try again

### "command not found: python3"

**Fix**: Ensure virtual environment is activated
```bash
source .venv/bin/activate
```

### Scripts not executable

**Fix**: Add execute permissions
```bash
chmod +x scripts/*.sh
```

### Using iTerm2 instead of Terminal.app

Scripts currently support Terminal.app only. For iTerm2, modify the AppleScript syntax in the scripts.

## See Also

- [docs/guides/monitoring_long_runs.md](../docs/guides/monitoring_long_runs.md) - Detailed monitoring guide
- [MONITORING_IMPLEMENTATION_SUMMARY.md](../MONITORING_IMPLEMENTATION_SUMMARY.md) - Technical implementation details
- [walk_forward.md](../docs/guides/walk_forward.md) - Walk-forward methodology
