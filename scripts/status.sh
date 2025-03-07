#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Status Script
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"  # Navigate to repository root

# Run the team CLI with the status command
python3 "$REPO_ROOT/src/cli/team_cli.py" status