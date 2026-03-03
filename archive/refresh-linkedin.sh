#!/usr/bin/env bash
# refresh-linkedin.sh
#
# Refreshes LinkedIn cookies for MCP Chrome with the CORRECT ordering:
#   1. Quit Claude Desktop (Chrome shuts down + flushes SQLite)
#   2. Wait for Chrome to fully exit
#   3. Inject cookies into clean SQLite DB
#   4. Relaunch Claude Desktop (Chrome starts + reads our cookies)
#
# Usage: Run this from Terminal whenever LinkedIn auth is needed.
#   bash ~/work/hashicorp/obsidian-notes/.claude/skills/sales-research/refresh-linkedin.sh

set -e

INJECT_SCRIPT="$(cd "$(dirname "$0")" && pwd)/inject_cookies.py"
PROFILE_DIR="$HOME/.cache/chrome-devtools-mcp/chrome-profile"
CLAUDE_APP="/Applications/Claude.app"

echo "=== LinkedIn Session Refresh for MCP Chrome ==="
echo ""

# ── Step 1: Quit Claude Desktop if running ─────────────────────────────────
if pgrep -x "Claude" >/dev/null 2>&1 || osascript -e 'tell application "System Events" to (name of processes) contains "Claude"' 2>/dev/null | grep -q true; then
    echo "Stopping Claude Desktop..."
    osascript -e 'tell application "Claude" to quit' 2>/dev/null || \
    osascript -e 'quit app "Claude"' 2>/dev/null || \
    pkill -f "Claude.app" 2>/dev/null || true

    echo -n "Waiting for Chrome to exit"
    for i in $(seq 1 40); do
        if ! pgrep -f "$PROFILE_DIR" >/dev/null 2>&1; then
            echo " ✓"
            break
        fi
        printf "."
        sleep 0.5
        if [ "$i" -eq 40 ]; then
            echo ""
            echo "ERROR: Chrome is still running after 20s. Please quit Claude Desktop manually and re-run this script."
            exit 1
        fi
    done
    # Extra safety buffer for SQLite flush
    sleep 1
else
    echo "Claude Desktop is not running — Chrome is stopped ✓"
fi

# ── Step 2: Force-kill any orphaned Chrome processes ──────────────────────
if pgrep -f "$PROFILE_DIR" >/dev/null 2>&1; then
    echo "Cleaning up orphaned Chrome processes..."
    pgrep -f "$PROFILE_DIR" | xargs kill 2>&1 || true
    sleep 1
    echo "  ✓ Orphaned processes killed"
fi
echo ""

# ── Step 3: Inject cookies into clean SQLite DB ─────────────────────────────
echo "Injecting LinkedIn cookies..."
if command -v uv >/dev/null 2>&1; then
    uv run "$INJECT_SCRIPT"
elif [ -x "$(dirname "$0")/.venv/bin/python" ]; then
    "$(dirname "$0")/.venv/bin/python" "$INJECT_SCRIPT"
else
    echo "ERROR: uv not found and venv missing."
    echo "Install uv with: brew install uv"
    echo "Or create venv: python3 -m venv $(dirname "$0")/.venv && $(dirname "$0")/.venv/bin/pip install pycookiecheat pycryptodome cryptography"
    exit 1
fi
echo ""

# ── Step 4: Relaunch Claude Desktop ─────────────────────────────────────────
if [ -d "$CLAUDE_APP" ]; then
    echo "Launching Claude Desktop..."
    open "$CLAUDE_APP"
    echo ""
    echo "✅ Done! Chrome will start with your LinkedIn session loaded."
    echo "   Once Claude Desktop opens, say: 'continue with the AMP research'"
else
    echo "✅ Cookies injected. Please open Claude Desktop manually."
    echo "   Once it's open, say: 'continue with the AMP research'"
fi
