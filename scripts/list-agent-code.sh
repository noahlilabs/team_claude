#!/bin/bash
# Script to list and sync code from agent directories

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

# Optional agent name to filter
AGENT_NAME="$1"

# Define directories
SHARED_CODE_DIR="$REPO_ROOT/shared_code"
AGENTS_DIR="$REPO_ROOT/agents"

# Display usage if --help flag is provided
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: $(basename "$0") [agent_name] [--sync]"
    echo ""
    echo "Lists code created by agents. If agent_name is provided, only shows code for that agent."
    echo ""
    echo "Options:"
    echo "  --sync    Synchronize all agent code to the shared directory"
    echo "  --help    Display this help message"
    exit 0
fi

# Check if sync flag is provided
SYNC=false
if [[ "$1" == "--sync" || "$2" == "--sync" ]]; then
    SYNC=true
    # If first arg is --sync, clear AGENT_NAME
    if [[ "$1" == "--sync" ]]; then
        AGENT_NAME=""
    fi
fi

# Sync code if requested
if $SYNC; then
    echo "Syncing agent code to shared directory..."
    bash "$REPO_ROOT/scripts/sync-code.sh"
    echo ""
fi

# Header
echo "=============================================="
echo "            AGENT CODE INVENTORY              "
echo "=============================================="
echo ""

# First list agent-specific code
echo "AGENT-SPECIFIC CODE:"
echo "--------------------------------------------"

# Process each agent directory
for agent_dir in $(find "$AGENTS_DIR" -maxdepth 1 -type d | grep -v "^$AGENTS_DIR\$"); do
    agent=$(basename "$agent_dir")
    
    # Skip if agent filter is provided and doesn't match
    if [[ -n "$AGENT_NAME" && "$agent" != "$AGENT_NAME" ]]; then
        continue
    fi
    
    # Find Python, JavaScript and other code files
    code_files=$(find "$agent_dir" -type f -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.html" -o -name "*.css" | sort)
    
    if [[ -n "$code_files" ]]; then
        echo "Agent: $agent"
        echo "$code_files" | sed 's|'"$REPO_ROOT"'|.|g' | sed 's|^|  |'
        echo ""
    fi
done

# Now list shared code
echo ""
echo "SHARED CODE REPOSITORY:"
echo "--------------------------------------------"

# Categories to check
categories=("tools" "modules" "integrations" "ui")

for category in "${categories[@]}"; do
    category_dir="$SHARED_CODE_DIR/$category"
    
    if [ -d "$category_dir" ]; then
        # Find code files in this category
        if [[ -n "$AGENT_NAME" ]]; then
            # Filter by agent name if provided
            code_files=$(find "$category_dir" -type f -name "*${AGENT_NAME}*" | sort)
        else
            # Otherwise show all
            code_files=$(find "$category_dir" -type f | grep -v "README" | sort)
        fi
        
        if [[ -n "$code_files" ]]; then
            echo "Category: $category"
            echo "$code_files" | sed 's|'"$REPO_ROOT"'|.|g' | sed 's|^|  |'
            echo ""
        fi
    fi
done

# Show totals
echo ""
echo "SUMMARY:"
echo "--------------------------------------------"

total_agent_files=$(find "$AGENTS_DIR" -type f -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.html" -o -name "*.css" | wc -l)
total_shared_files=$(find "$SHARED_CODE_DIR" -type f -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.html" -o -name "*.css" | wc -l)

echo "Agent-specific files: $total_agent_files"
echo "Shared code files: $total_shared_files"
echo "Total code files: $((total_agent_files + total_shared_files))"
echo ""