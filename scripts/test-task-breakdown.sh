#!/bin/bash

# Test script to validate task breakdown pipeline

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

echo "Running task breakdown test from $REPO_ROOT"

# 1. Create a test self-enhancement task
echo "Creating test self-enhancement task..."

# Create task and extract just the ID
TASK_RESULT=$(python3 "$REPO_ROOT/src/cli/state_cli.py" add_task "master" "Create a self-enhancement toolkit with web search capabilities and coding sandbox" "team_lead" --priority "high")
TASK_ID=$(echo "$TASK_RESULT" | sed 's/Added task //')

if [ -z "$TASK_ID" ]; then
    echo "Failed to create test task"
    exit 1
fi

echo "Created test task with ID: $TASK_ID"

# 2. Get the full task details
echo "Getting full task details..."
python3 "$REPO_ROOT/src/cli/state_cli.py" get_task "$TASK_ID"

# 3. Test the task analyzer directly
echo "Testing task analyzer directly..."
python3 "$REPO_ROOT/src/utils/task_analyzer.py" "$TASK_ID" "Create a self-enhancement toolkit with web search capabilities and coding sandbox"

# 4. Test the task breakdown function by sourcing agent_common.sh and calling directly
echo "Testing break_down_task function directly..."

# Source the agent_common.sh file to get the function definitions
source "$REPO_ROOT/src/agents/templates/agent_common.sh"

# Initialize the agent to set up environment
CLAUDE_AGENT_NAME="Test Agent" 
CLAUDE_AGENT_TYPE="test"
CLAUDE_AGENT_CAPABILITIES="testing,debugging"

init_agent

# Call the break_down_task function directly
break_down_task "$TASK_ID" "Create a self-enhancement toolkit with web search capabilities and coding sandbox"

# 5. Check the results
echo "Checking subtasks created..."
python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --parent "$TASK_ID"

echo "Test completed."