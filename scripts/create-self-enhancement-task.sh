#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Create Self-Enhancement Task Script
# =============================================================================
# This script creates a task for developing self-enhancement tools with special format

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

# Delete all existing tasks
"$SCRIPT_DIR/delete-all-tasks.sh"

# Create the task with specific prefix that the team lead will recognize
echo "Creating self-enhancement toolkit task..."

python3 "$REPO_ROOT/src/cli/state_cli.py" add_task "master" "[SELF_ENHANCEMENT_TOOLKIT] I want you to create tools for yourself to further enhance your own capabilities, these include 1. A way to search on the internet to get up to date information 2. A coding sandbox environment to run coding tests before you deploy it into the main file. 3. A way to browser the internet" "team_lead" --priority "high" --capabilities "api,python,integration"

echo "Self-enhancement toolkit task created successfully."
echo "Wait a moment for the team_lead to break it down, then check: ./scripts/list-tasks.sh" 