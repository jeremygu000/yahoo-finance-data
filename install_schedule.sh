#!/bin/bash
set -euo pipefail

PLIST_NAME="com.market-data.fetch.plist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_PLIST="${SCRIPT_DIR}/${PLIST_NAME}"
TARGET_DIR="${HOME}/Library/LaunchAgents"
TARGET_PLIST="${TARGET_DIR}/${PLIST_NAME}"
LOG_DIR="${HOME}/.market_data/logs"

echo "=== Market Data Fetch — LaunchAgent Installer ==="
echo ""

# 1. Create log directory
mkdir -p "${LOG_DIR}"
echo "✓ Log directory: ${LOG_DIR}"

# 2. Unload existing agent if present
if launchctl list | grep -q "com.market-data.fetch"; then
    echo "  Unloading existing agent..."
    launchctl unload "${TARGET_PLIST}" 2>/dev/null || true
fi

# 3. Copy plist
mkdir -p "${TARGET_DIR}"
cp "${SOURCE_PLIST}" "${TARGET_PLIST}"
echo "✓ Plist installed: ${TARGET_PLIST}"

# 4. Load agent
launchctl load "${TARGET_PLIST}"
echo "✓ Agent loaded"

# 5. Verify
echo ""
echo "--- Status ---"
launchctl list | grep "com.market-data.fetch" || echo "⚠ Agent not found in launchctl list"
echo ""
echo "Schedule: Mon-Fri at 20:35 UTC (≈ 16:35 ET)"
echo "Logs:     ${LOG_DIR}/fetch.log"
echo "Errors:   ${LOG_DIR}/fetch.err"
echo ""
echo "Manual trigger:  launchctl start com.market-data.fetch"
echo "Uninstall:       launchctl unload ${TARGET_PLIST} && rm ${TARGET_PLIST}"
