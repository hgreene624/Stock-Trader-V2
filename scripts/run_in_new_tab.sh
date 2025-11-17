#!/bin/bash
# Helper script to run commands in a new Terminal tab on macOS
#
# Usage: ./scripts/run_in_new_tab.sh "your command here"
#
# This allows monitoring of long-running processes like EA optimization
# in a separate terminal tab while keeping the main terminal free.

if [ $# -eq 0 ]; then
    echo "Usage: $0 'command to run'"
    echo "Example: $0 'python3 -m engines.optimization.walk_forward_cli --quick'"
    exit 1
fi

COMMAND="$1"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Create AppleScript to open new tab and run command
osascript <<EOF
tell application "Terminal"
    activate
    tell application "System Events" to keystroke "t" using command down
    delay 0.5
    do script "cd '$PROJECT_DIR' && source .venv/bin/activate && $COMMAND" in front window
end tell
EOF

echo "✅ Command launched in new Terminal tab"
echo "📊 You can now monitor the progress in the new tab"
