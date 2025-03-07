#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Fix API and Restart
# =============================================================================
# This script fixes the API issue and restarts the system

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "==== Fixing API and Restarting Multi-Agent Claude System ===="

# First stop any running system
echo "Stopping existing system..."
"$SCRIPT_DIR/stop.sh"

# Remove state file and regenerate it
echo "Resetting state file..."
if [ -f "$REPO_ROOT/claude_state.json" ]; then
  rm "$REPO_ROOT/claude_state.json"
  echo "State file removed"
fi

# Reset agent contexts
echo "Removing agent context files..."
find "$REPO_ROOT/agents" -name "agent_context.json" -delete 2>/dev/null
find "$REPO_ROOT/agents" -name "context" -type d -exec rm -rf {} \; 2>/dev/null

# Make sure data files have proper permissions
echo "Setting up data directory..."
mkdir -p "$REPO_ROOT/data"
chmod -R 755 "$REPO_ROOT/data"

# Create new state file with empty structure
echo "Creating new state file..."
echo '{"tasks": {}, "branches": {}, "messages": [], "pull_requests": {}, "reasoning_logs": {}, "agents": {}}' > "$REPO_ROOT/claude_state.json"

# Start fresh system
echo "Starting fresh multi-agent system..."
"$SCRIPT_DIR/start.sh"

# Create our self-enhancement task
echo "Creating self-enhancement toolkit task..."
"$SCRIPT_DIR/task.sh" "I want you to create tools for yourself to further enhance your own capabilities, these include 1. A way to search on the internet to get up to date information 2. A coding sandbox environment to run coding tests before you deploy it into the main file. 3. A way to browser the internet" --capabilities "api,python,integration"

echo "System restarted with fixed API!"
echo "Check agent status with: ./scripts/agent-status.sh"
echo "Check task status with: ./scripts/list-tasks.sh"
echo "The team_lead agent should now be able to break down tasks and distribute them to other agents." 