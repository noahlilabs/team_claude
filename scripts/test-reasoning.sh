#!/bin/bash
# Test Claude's reasoning capabilities

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

echo "Testing Claude's reasoning capabilities..."
echo "Using claude-3-7-sonnet-20250219 model"

python3 "$REPO_ROOT/src/utils/reasoning_example.py" 