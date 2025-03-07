#!/bin/bash
# Delete all tasks from the system

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "Deleting all tasks from the system..."
python3 "$REPO_ROOT/src/cli/state_cli.py" delete_all_tasks

echo "All tasks deleted successfully."
