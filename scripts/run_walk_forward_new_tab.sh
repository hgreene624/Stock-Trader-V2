#!/bin/bash
# Convenience script to run walk-forward optimization in a new terminal tab
#
# Usage:
#   ./scripts/run_walk_forward_new_tab.sh              # Quick mode
#   ./scripts/run_walk_forward_new_tab.sh --full       # Full optimization
#
# This opens the optimization in a new tab so you can monitor real-time
# progress output from the EA algorithm.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Default to quick mode
MODE="--quick"
if [ "$1" == "--full" ]; then
    MODE=""
fi

COMMAND="python3 -m engines.optimization.walk_forward_cli $MODE"

echo "🚀 Launching Walk-Forward Optimization in new terminal tab..."
echo "📊 Mode: $([ -z "$MODE" ] && echo "FULL" || echo "QUICK")"
echo ""

# Use osascript to open new tab
osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "cd '$PROJECT_DIR' && source .venv/bin/activate && echo '🔬 Walk-Forward Optimization Starting...' && echo '' && $COMMAND" in front window
end tell
EOF

echo "✅ Optimization launched in new Terminal tab!"
echo "💡 You can now monitor the real-time progress in the new tab"
echo "⏱️  Expected time:"
echo "    Quick mode (~10-15 min): 10 population × 10 generations × multiple windows"
echo "    Full mode (~30-60 min): 20 population × 15 generations × multiple windows"
