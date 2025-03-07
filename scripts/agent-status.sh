#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Agent Status Script
# =============================================================================
# This script shows what each agent is currently working on

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "==== Multi-Agent Claude System - Agent Status ===="

# Check if agents are running
echo "---- Active TMUX Sessions ----"
tmux ls 2>/dev/null || echo "No TMUX sessions running"

# Check active agents
echo "---- Active Agents ----"
python3 "$REPO_ROOT/src/cli/state_cli.py" list-agents --status active

# Check tasks 
echo "---- Current Tasks ----"
python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks

# Show agent messaging statistics
echo "---- Agent Communication ----"
messages=$(grep -r "\[@FROM" "$REPO_ROOT/claude_state.json" | wc -l)
echo "Total messages exchanged: $messages"

# Check context windows for agents (if they exist)
echo "---- Agent Context Files ----"
find "$REPO_ROOT/agents" -name "agent_context.json" | while read -r context_file; do
  agent_dir=$(dirname "$(dirname "$context_file")")
  agent_name=$(basename "$agent_dir")
  
  # Count tasks and messages in context
  task_count=$(grep -c "task_" "$context_file" 2>/dev/null || echo "0")
  message_count=$(grep -c "\[@FROM" "$context_file" 2>/dev/null || echo "0")
  
  echo "Agent $agent_name: $task_count tasks, $message_count messages in context"
done

echo "==== Status Check Complete ====" 