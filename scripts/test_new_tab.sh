#!/bin/bash
# Quick test to verify the new tab launching works
# This runs a simple echo command in a new tab

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🧪 Testing new tab functionality..."
echo "📂 Project dir: $PROJECT_DIR"
echo ""

# Simple test command
TEST_COMMAND="echo '✅ New tab works!' && echo 'Press any key to close...' && read -n 1"

osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "cd '$PROJECT_DIR' && echo '🔬 Test Tab Opened' && echo '' && $TEST_COMMAND" in front window
end tell
EOF

echo "✅ Test tab launched!"
echo "💡 Check the new Terminal tab - it should show '✅ New tab works!'"
echo ""
echo "If you see the message in a new tab, the feature is working correctly."
