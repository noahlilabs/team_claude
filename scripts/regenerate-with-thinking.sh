#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Reset and Regenerate with Extended Thinking
# =============================================================================
# This script fully resets the system and starts it again with extended thinking enabled

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "==== Regenerating Multi-Agent Claude System with Extended Thinking ===="

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

# Update .env file to enable extended thinking
echo "Updating .env to enable extended thinking..."
if [ -f "$REPO_ROOT/.env" ]; then
  # Check if ENABLE_EXTENDED_THINKING exists in .env
  if grep -q "ENABLE_EXTENDED_THINKING" "$REPO_ROOT/.env"; then
    # Update the existing variable
    sed -i '' 's/ENABLE_EXTENDED_THINKING=.*/ENABLE_EXTENDED_THINKING=true/' "$REPO_ROOT/.env"
  else
    # Add the variable
    echo "ENABLE_EXTENDED_THINKING=true" >> "$REPO_ROOT/.env"
  fi
else
  # Create new .env file
  echo "# Anthropic API Key (Required)" > "$REPO_ROOT/.env"
  echo "ANTHROPIC_API_KEY=
  echo "TMUX_SESSION_NAME=claude-team" >> "$REPO_ROOT/.env"
  echo "MAX_AGENTS=4" >> "$REPO_ROOT/.env"
  echo "ENABLE_SEPARATE_CONTEXTS=true" >> "$REPO_ROOT/.env"
  echo "ENABLE_EXTENDED_THINKING=true" >> "$REPO_ROOT/.env"
fi

# Start fresh system
echo "Starting fresh multi-agent system with extended thinking..."
"$SCRIPT_DIR/start.sh"

# Create a sample data task with context
echo "Creating sample data task..."
"$SCRIPT_DIR/add-data-task.sh"

echo "System regenerated successfully with extended thinking enabled!"
echo "Check agent status with: ./scripts/agent-status.sh"
echo "Check task status with: ./scripts/list-tasks.sh" 