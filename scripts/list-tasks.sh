#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - List Tasks Script
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

# Run the team CLI with the list-tasks command
python3 "$REPO_ROOT/src/cli/team_cli.py" list-tasks