#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Create Agent Script
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

# Check if agent type was provided
if [ $# -eq 0 ]; then
    echo "Error: Agent type required"
    echo "Usage: $0 <agent_type> [--capabilities <capabilities>] [--description <description>] [--start]"
    echo "Available agent types: manager, frontend, backend, data, testing"
    exit 1
fi

# Run the team CLI with the create-agent command, forwarding all arguments
python3 "$REPO_ROOT/src/cli/team_cli.py" create-agent "$@"