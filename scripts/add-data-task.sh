#!/bin/bash
# Add a data-focused task that uses reasoning capabilities

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

# First, delete all existing tasks
"$SCRIPT_DIR/delete-all-tasks.sh"

# Create the data analysis task with detailed context
echo "Creating data analysis task with reasoning capabilities and detailed context..."
"$SCRIPT_DIR/task.sh" "Analyze this dataset: You are given a dataset about user behavior on a website. The data includes user IDs, session times, pages visited, and conversion rates. Your task is to analyze this data to identify patterns in user behavior that lead to successful conversions. Break down this analysis task into steps: 1) Data cleaning and preparation, 2) Exploratory data analysis, 3) Pattern identification, 4) Insight generation, and 5) Recommendations for improving conversion rates. For each step, document your reasoning process in detail before proceeding to the next step." --capabilities "data_processing,analytics,visualization"

echo "Data task created successfully. Run './scripts/list-tasks.sh' to see it." 