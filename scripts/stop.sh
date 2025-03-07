#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Stop Script
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

echo "Stopping multi-agent Claude system..."

# Run the team CLI with the stop command
python3 "$REPO_ROOT/src/cli/team_cli.py" stop