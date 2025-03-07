#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Manual Task Breakdown Script
# =============================================================================
# This script manually breaks down the self-enhancement toolkit task and assigns subtasks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "==== Manual Task Breakdown for Self-Enhancement Toolkit ===="

# Get the ID of the self-enhancement task
TASK_ID="task_1741345002_1"  # This should be the ID of your self-enhancement task

# Make sure task exists and is still pending
TASK_STATUS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --id "$TASK_ID" | grep -o "\[.*\]" | tr -d "[]" || echo "not_found")

if [ "$TASK_STATUS" != "pending" ] && [ "$TASK_STATUS" != "in-progress" ]; then
    echo "Error: Task $TASK_ID not found or not in pending/in-progress state (current status: $TASK_STATUS)"
    exit 1
fi

echo "Found task $TASK_ID, current status: $TASK_STATUS"

# Update task status to in-progress
python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$TASK_ID" "in-progress" --message "Manual breakdown started"

# Create subtasks for the self-enhancement toolkit
echo "Creating subtasks for self-enhancement toolkit..."

# Subtask 1: Web Search Tool
echo "Creating subtask for Web Search Tool..."
SUBTASK1=$(python3 "$REPO_ROOT/src/cli/state_cli.py" create_subtask "$TASK_ID" "Develop a web search tool that allows Claude to search the internet for up-to-date information using search APIs" "agent3" "api,python,integration")
echo "Created subtask: $SUBTASK1"

# Subtask 2: Code Sandbox Environment
echo "Creating subtask for Code Sandbox Environment..."
SUBTASK2=$(python3 "$REPO_ROOT/src/cli/state_cli.py" create_subtask "$TASK_ID" "Create a code sandbox environment that allows Claude to test code before deploying it to main files, including execution and validation features" "agent3" "python,api")
echo "Created subtask: $SUBTASK2"

# Subtask 3: Web Browser Interface
echo "Creating subtask for Web Browser Interface..."
SUBTASK3=$(python3 "$REPO_ROOT/src/cli/state_cli.py" create_subtask "$TASK_ID" "Implement a web browsing interface that allows Claude to navigate websites, extract content, and interact with web pages" "agent2" "javascript,visualization")
echo "Created subtask: $SUBTASK3"

# Subtask 4: Integration and UI
echo "Creating subtask for Integration and UI..."
SUBTASK4=$(python3 "$REPO_ROOT/src/cli/state_cli.py" create_subtask "$TASK_ID" "Create a unified user interface that integrates all enhancement tools with a clean, intuitive frontend" "agent1" "css,javascript")
echo "Created subtask: $SUBTASK4"

# Log manually created breakdown
python3 "$REPO_ROOT/src/cli/state_cli.py" log_reasoning "team_lead" "$TASK_ID" "Task manually broken down into web search, code sandbox, web browser, and integration components." "task_breakdown"

# Update task status to reflect breakdown
python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$TASK_ID" "in-progress" --message "Task broken down manually"

# Broadcast to all agents
echo "Broadcasting task breakdown to all agents..."
TEAM_LEAD_MSG="[@FROM:team_lead] [@BROADCAST] [@TAG:task_breakdown] I've broken down the self-enhancement toolkit task into subtasks. Each agent should check their assigned tasks."
for agent_id in "agent1" "agent2" "agent3"; do
    python3 "$REPO_ROOT/src/cli/state_cli.py" send_message "team_lead" "$agent_id" "$TEAM_LEAD_MSG" --channel "broadcast" --priority "high"
done

echo "==== Manual Task Breakdown Complete ===="
echo "You can now monitor task progress with: ./scripts/list-tasks.sh" 