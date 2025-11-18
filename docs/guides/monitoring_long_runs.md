# Monitoring Long-Running Optimizations

When running EA walk-forward optimization, you may want to monitor real-time progress instead of waiting for the entire process to complete. This guide explains how to run optimizations in a separate terminal tab on macOS.

## Problem

When Claude runs optimization commands, the output is buffered and you can't see real-time progress. The EA algorithm shows detailed progress including:
- Current generation (e.g., Gen 5/15)
- Current individual (e.g., Individual 12/20)
- Overall progress percentage
- Time estimates (elapsed and remaining)
- Best BPS scores per generation

But you can't monitor this when Claude runs it in the background.

## Solutions

### Option 1: Use the `--new-tab` Flag (Recommended)

The walk-forward CLI now supports a `--new-tab` flag that automatically launches the optimization in a new Terminal tab:

```bash
# Quick mode in new tab
python3 -m engines.optimization.walk_forward_cli --quick --new-tab

# Full optimization in new tab
python3 -m engines.optimization.walk_forward_cli --new-tab

# With custom parameters in new tab
python3 -m engines.optimization.walk_forward_cli \
    --train-months 18 \
    --test-months 12 \
    --population 25 \
    --generations 20 \
    --new-tab
```

**What happens:**
1. Command validates arguments
2. Opens a new Terminal tab
3. Activates virtual environment
4. Runs the optimization with real-time output visible
5. Original terminal returns immediately

**When Claude runs it:**
When I (Claude) run the command with `--new-tab`, you'll see a new Terminal tab open where you can monitor the progress in real-time, while I continue working in my terminal.

### Option 2: Use Helper Scripts

For convenience, there are pre-built scripts:

```bash
# Walk-forward optimization in new tab (quick mode)
./scripts/run_walk_forward_new_tab.sh

# Walk-forward optimization in new tab (full mode)
./scripts/run_walk_forward_new_tab.sh --full

# General purpose: any command in new tab
./scripts/run_in_new_tab.sh "your-command-here"
./scripts/run_in_new_tab.sh "python3 -m engines.optimization.walk_forward_cli --quick"
```

### Option 3: Manual Terminal Tab

You can also manually open a new tab yourself:

1. **⌘T** to open new Terminal tab
2. Navigate to project: `cd /Users/holden/PycharmProjects/PythonProject`
3. Activate venv: `source .venv/bin/activate`
4. Run optimization: `python3 -m engines.optimization.walk_forward_cli --quick`

## Progress Output Example

When running in a monitored tab, you'll see output like this:

```
================================================================================
EVOLUTIONARY OPTIMIZATION - PROGRESS TRACKING
================================================================================
Total backtests to run: 100
Population size: 10
Generations: 10
================================================================================

  Gen 1/10 | Individual 1/10 | Progress: 1.0% | BPS: 0.823
  Gen 1/10 | Individual 2/10 | Progress: 2.0% | BPS: 0.756
  Gen 1/10 | Individual 3/10 | Progress: 3.0% | BPS: 0.891
  ...
  Gen 1/10 | Individual 10/10 | Progress: 10.0% | BPS: 0.803

────────────────────────────────────────────────────────────────────────────────
GENERATION 1/10 COMPLETE
────────────────────────────────────────────────────────────────────────────────
  Time: 42.3s
  Best BPS: 0.8910
  Avg BPS: 0.7854
  Overall Progress: 10.0%
  Elapsed: 0.7 min | Remaining: 6.3 min
────────────────────────────────────────────────────────────────────────────────

  Gen 2/10 | Individual 1/10 | Progress: 11.0% | BPS: 0.887
  ...
```

## How It Works (Technical Details)

### macOS AppleScript Integration

The solution uses `osascript` to send AppleScript commands to Terminal.app:

```applescript
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "cd 'PROJECT_DIR' && source .venv/bin/activate && COMMAND" in front window
end tell
```

This:
1. Activates Terminal application
2. Sends ⌘T keystroke to open new tab
3. Waits 0.5 seconds for tab to open
4. Executes the command in the new tab

### Why This Works

The EA optimizer uses `flush=True` on all print statements to ensure real-time output:

```python
print(f"Progress: {progress_pct:.1f}%", flush=True)
```

When running in a visible terminal, you see this output immediately. When running through Claude's Bash tool, the output is buffered until the command completes.

## When to Use Each Option

| Scenario | Recommended Option |
|----------|-------------------|
| Claude is running optimization | Use `--new-tab` flag |
| You're running optimization manually | Use helper scripts or manual tab |
| Running on Linux/Windows | Use background monitoring (see below) |
| Multiple optimizations | Open multiple tabs with scripts |

## Alternative: Background Monitoring (All Platforms)

If you're not on macOS or prefer a different approach, you can use background execution:

```bash
# Start in background
python3 -m engines.optimization.walk_forward_cli --quick > /tmp/walk_forward.log 2>&1 &

# Get process ID
PROCESS_ID=$!

# Monitor in real-time
tail -f /tmp/walk_forward.log

# Check if still running
ps -p $PROCESS_ID
```

## Estimating Run Times

**Quick Mode** (`--quick`):
- Windows: Typically 2-3 (12-month train, 6-month test)
- Population: 10
- Generations: 10
- Backtests per window: 100 (10 × 10)
- **Total time: ~10-15 minutes** (varies by data size)

**Full Mode** (default):
- Windows: Typically 2-3 (18-month train, 12-month test)
- Population: 20
- Generations: 15
- Backtests per window: 300 (20 × 15)
- **Total time: ~30-60 minutes** (varies by data size)

Each backtest takes ~2-5 seconds depending on:
- Date range size
- Number of assets
- Model complexity
- Feature computation overhead

## Troubleshooting

### "Terminal" is not allowed to send keystrokes

macOS may block AppleScript from controlling Terminal. To fix:

1. Open **System Preferences** → **Security & Privacy** → **Accessibility**
2. Click the lock to make changes
3. Add **Terminal** to the list of apps that can control your computer
4. Try the command again

### New tab doesn't open

Make sure Terminal.app is running. The script will activate it, but if Terminal isn't installed or you're using a different terminal (iTerm2, etc.), you'll need to modify the AppleScript.

### Virtual environment not activating in new tab

Check that `.venv` exists in project root:

```bash
ls -la .venv/bin/activate
```

If missing, recreate:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Integration with Claude Code

When I (Claude) need to run a long optimization, I can use the `--new-tab` flag:

```bash
python3 -m engines.optimization.walk_forward_cli --quick --new-tab
```

This allows you to monitor progress in real-time while I continue working on other tasks or analyzing previous results.

## Future Enhancements

Potential improvements:

1. **iTerm2 support**: Add detection and support for iTerm2
2. **Linux/Windows**: Implement similar solutions for other platforms
3. **Progress dashboard**: Web-based real-time progress viewer
4. **Notifications**: macOS notifications when optimization completes
5. **Remote monitoring**: SSH tunnel for monitoring remote optimizations

## See Also

- [walk_forward.md](walk_forward.md) - Walk-forward methodology
- [walk_forward.md – Implementation Notes](walk_forward.md#implementation-notes) - Technical implementation
- [workflow_guide.md](workflow_guide.md) - General workflow patterns
