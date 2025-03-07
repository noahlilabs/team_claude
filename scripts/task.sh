#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Create Task Script
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

# Check if a task description was provided
if [ $# -eq 0 ]; then
    echo "Error: Task description required"
    echo "Usage: $0 \"Task description\" [--priority <priority>] [--capabilities <capabilities>]"
    exit 1
fi

# Run the team CLI with the task command, forwarding all arguments
python3 "$REPO_ROOT/src/cli/team_cli.py" task "$@"