#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Start Script
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

# Ensure required directories exist
mkdir -p "$REPO_ROOT/data"
mkdir -p "$REPO_ROOT/logs"
mkdir -p "$REPO_ROOT/agents"

# Ensure data files have proper permissions 
if [ -d "$REPO_ROOT/data" ]; then
  chmod -R 755 "$REPO_ROOT/data"
  echo "Ensured data directory has proper permissions"
fi

# Initialize empty state file if it doesn't exist
if [ ! -f "$REPO_ROOT/claude_state.json" ]; then
  echo "{\"tasks\": {}, \"branches\": {}, \"messages\": [], \"pull_requests\": {}, \"reasoning_logs\": {}, \"agents\": {}}" > "$REPO_ROOT/claude_state.json"
  echo "Initialized empty state file"
fi

# Default number of agents
NUM_AGENTS=${1:-4}

echo "Starting multi-agent Claude system with $NUM_AGENTS agents..."

# Run the team CLI with the start command
python3 "$REPO_ROOT/src/cli/team_cli.py" start --agents "$NUM_AGENTS"

# Print additional information
echo
echo "System started. You can:"
echo "- Attach to session: ./scripts/attach.sh"
echo "- View status: ./scripts/status.sh"
echo "- Create a task: ./scripts/task.sh \"Task description\""
echo "- Stop the system: ./scripts/stop.sh"