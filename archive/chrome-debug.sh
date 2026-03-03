#!/usr/bin/env bash
# chrome-debug.sh
#
# Launches Chrome with remote debugging enabled and a persistent profile.
# MCP chrome-devtools connects to this via --browserUrl=http://127.0.0.1:9222
#
# First run: Log into LinkedIn Sales Navigator in the browser window.
# Sessions persist in ~/.chrome-debug-profile/ across restarts.
#
# Usage:
#   bash ~/work/hashicorp/obsidian-notes/.claude/skills/sales-research/chrome-debug.sh
#
# Or add an alias to ~/.zshrc:
#   alias chrome:debug="bash ~/work/hashicorp/obsidian-notes/.claude/skills/sales-research/chrome-debug.sh"

set -e

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="$HOME/.chrome-debug-profile"
PORT=9222

# Check if debug Chrome is already running on this port
if curl -s "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo "✅ Debug Chrome is already running on port $PORT"
    curl -s "http://127.0.0.1:$PORT/json/version" | python3 -c "import sys,json; v=json.load(sys.stdin); print(f'   Browser: {v.get(\"Browser\",\"unknown\")}'); print(f'   WebSocket: {v.get(\"webSocketDebuggerUrl\",\"unknown\")}')" 2>/dev/null || true
    exit 0
fi

echo "=== Launching Chrome with Remote Debugging ==="
echo "  Port: $PORT"
echo "  Profile: $USER_DATA_DIR"
echo ""

if [ ! -d "$USER_DATA_DIR" ]; then
    echo "  First run — Chrome will create a fresh profile."
    echo "  Log into LinkedIn Sales Navigator in the browser window."
    echo ""
fi

"$CHROME" \
    --remote-debugging-port=$PORT \
    --user-data-dir="$USER_DATA_DIR" \
    > /dev/null 2>&1 &

# Wait for Chrome to start
echo -n "  Waiting for Chrome"
for i in $(seq 1 20); do
    if curl -s "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
        echo " ✓"
        echo ""
        echo "✅ Debug Chrome is running on port $PORT"
        echo "   MCP chrome-devtools will connect via --browserUrl=http://127.0.0.1:$PORT"
        exit 0
    fi
    printf "."
    sleep 0.5
done

echo ""
echo "⚠️  Chrome started but port $PORT is not responding."
echo "   Close any other Chrome instances and try again."
exit 1
