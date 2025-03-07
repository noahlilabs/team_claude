#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Reset and Regenerate Script
# =============================================================================
# This script fully resets the system and starts it again with proper context

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "==== Regenerating Multi-Agent Claude System ===="

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

# Create a sample data task with context
echo "Creating sample data task..."
"$SCRIPT_DIR/add-data-task.sh"

echo "System regenerated successfully!"
echo "Check agent status with: ./scripts/agent-status.sh"
echo "Check task status with: ./scripts/list-tasks.sh" 