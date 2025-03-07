#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Debug Context Script
# =============================================================================
# This script helps diagnose issues with agent context and task processing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "==== Multi-Agent Claude System - Context Debugging ===="

# Check if state file exists
if [ ! -f "$REPO_ROOT/claude_state.json" ]; then
  echo "[ERROR] State file not found at $REPO_ROOT/claude_state.json"
  echo "Run ./scripts/start.sh to initialize the system."
  exit 1
fi

# Check state file size
STATE_SIZE=$(wc -c < "$REPO_ROOT/claude_state.json")
echo "State file size: $STATE_SIZE bytes"

if [ "$STATE_SIZE" -lt 100 ]; then
  echo "[WARNING] State file is very small (possibly empty or corrupt)"
  echo "Fixing state file with default structure..."
  echo "{\"tasks\": {}, \"branches\": {}, \"messages\": [], \"pull_requests\": {}, \"reasoning_logs\": {}, \"agents\": {}}" > "$REPO_ROOT/claude_state.json"
  echo "State file reset with default structure."
fi

# Check for TMUX sessions
echo "---- Checking for TMUX sessions ----"
tmux ls 2>/dev/null || echo "No TMUX sessions running"

# Check for available data files
echo "---- Available Data Files ----"
if [ -d "$REPO_ROOT/data" ]; then
  find "$REPO_ROOT/data" -type f | while read -r file; do
    echo "Found data file: $file ($(wc -l < "$file") lines)"
    # Show CSV headers if applicable
    if [[ "$file" == *.csv ]]; then
      echo "  Header: $(head -n 1 "$file")"
    fi
  done
else
  echo "No data directory found. Creating one..."
  mkdir -p "$REPO_ROOT/data"
fi

# Check active tasks
echo "---- Active Tasks ----"
"$SCRIPT_DIR/list-tasks.sh" 

# Add a test task with clear context if no tasks exist
TASK_COUNT=$(python3 -c "import json; print(len(json.load(open('$REPO_ROOT/claude_state.json'))['tasks']))" 2>/dev/null || echo "0")

if [ "$TASK_COUNT" = "0" ]; then
  echo "No tasks found. Creating a test task with clear context..."
  "$SCRIPT_DIR/add-data-task.sh"
fi

echo "==== Debug Complete ===="
echo "If agents are still having context issues:"
echo "1. Stop the system: ./scripts/stop.sh"
echo "2. Start the system: ./scripts/start.sh"
echo "3. Create a new task with explicit context: ./scripts/add-data-task.sh" 