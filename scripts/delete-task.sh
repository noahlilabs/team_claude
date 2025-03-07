#!/bin/bash
# Delete a specific task from the system

if [ -z "$1" ]; then
    echo "Error: Task ID is required"
    echo "Usage: $0 <task_id>"
    exit 1
fi

TASK_ID="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

echo "Deleting task $TASK_ID..."
python3 "$REPO_ROOT/src/cli/state_cli.py" delete_task "$TASK_ID"
echo "Task deletion complete."
