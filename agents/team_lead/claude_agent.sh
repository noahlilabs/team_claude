#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Enhanced Agent Script
# =============================================================================

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="/Users/noahlofquist/Desktop/multi-agent claude"  # Navigate to the repository root

# Verify REPO_ROOT exists
if [ ! -d "$REPO_ROOT" ]; then
    echo "Error: Repository root directory not found at $REPO_ROOT"
    # Fallback to a simpler approach
    REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")/../.." && pwd)"
    if [ ! -d "$REPO_ROOT" ]; then
        echo "Error: Could not determine repository root directory"
        exit 1
    fi
fi

# Agent configuration - these will be replaced for each agent
export CLAUDE_team_lead="team_lead"
export CLAUDE_manager="manager"
export CLAUDE_planning,task_assignment,integration,architecture="planning,task_assignment,integration,architecture"
export CLAUDE_master="master"
export CLAUDE_STATE_FILE="$REPO_ROOT/claude_state.json"
export CLAUDE_/Users/noahlofquist/Desktop/multi-agent claude/agents/team_lead="/Users/noahlofquist/Desktop/multi-agent claude/agents/team_lead"
export CLAUDE_HEALTH_CHECK_INTERVAL=30  # seconds

# Import common agent functions
if [ -f "$REPO_ROOT/src/agents/templates/agent_common.sh" ]; then
    source "$REPO_ROOT/src/agents/templates/agent_common.sh"
else
    echo "Error: Could not find common agent functions at $REPO_ROOT/src/agents/templates/agent_common.sh"
    exit 1
fi

# Load API key from .env file
load_api_key

# =============================================================================
# Main Agent Loop
# =============================================================================

echo "Starting Claude Agent: $CLAUDE_team_lead (Type: $CLAUDE_manager)"
echo "Capabilities: $CLAUDE_planning,task_assignment,integration,architecture"
echo "Working directory: $CLAUDE_/Users/noahlofquist/Desktop/multi-agent claude/agents/team_lead"
cd "$CLAUDE_/Users/noahlofquist/Desktop/multi-agent claude/agents/team_lead" || exit 1

# Log that the agent is starting up
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
echo "[$TIMESTAMP] Agent $CLAUDE_team_lead starting up..."

# Register agent with the state manager
echo "[$TIMESTAMP] Registering agent $CLAUDE_team_lead with capabilities: $CLAUDE_planning,task_assignment,integration,architecture"
python3 "$REPO_ROOT/src/cli/state_cli.py" register_agent "$CLAUDE_team_lead" "$CLAUDE_manager" "$CLAUDE_planning,task_assignment,integration,architecture"
if [ $? -ne 0 ]; then
    echo "[$TIMESTAMP] WARNING: Agent registration failed"
else
    echo "[$TIMESTAMP] Agent successfully registered"
fi

# Log startup event to shared state
python3 "$REPO_ROOT/src/cli/state_cli.py" log_reasoning "$CLAUDE_team_lead" "startup" "Agent started successfully with capabilities: $CLAUDE_planning,task_assignment,integration,architecture" --tags "startup"

echo "[$TIMESTAMP] Registered agent $CLAUDE_team_lead with the system"

# Track last health check
LAST_HEALTH_CHECK=$(date +%s)

# Main loop
while true; do
    # Update timestamp for logging
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    
    # Ping health status periodically
    CURRENT_TIME=$(date +%s)
    if (( CURRENT_TIME - LAST_HEALTH_CHECK >= CLAUDE_HEALTH_CHECK_INTERVAL )); then
        ping_health_status
        LAST_HEALTH_CHECK=$CURRENT_TIME
    fi

    echo "[$TIMESTAMP] Checking for tasks..."
    
    # Get tasks for this branch
    echo "[$TIMESTAMP] Looking for tasks for branch $CLAUDE_master:"
    BRANCH_TASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks "$CLAUDE_master")
    echo "$BRANCH_TASKS"
    
    # First, specifically look for breakdown tasks (high priority)
    echo "[$TIMESTAMP] Looking for breakdown tasks:"
    BREAKDOWN_TASKS=$(echo "$BRANCH_TASKS" | grep "\[BREAKDOWN_REQUIRED\]" || echo "")
    
    # Then look for any pending tasks assigned to this agent
    echo "[$TIMESTAMP] Looking for pending tasks assigned to $CLAUDE_team_lead:"
    PENDING_TASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --agent "$CLAUDE_team_lead" --status "pending")
    
    # Process tasks - prioritize breakdown tasks
    if [ -n "$BREAKDOWN_TASKS" ]; then
        echo "[$TIMESTAMP] Found tasks requiring breakdown:"
        for task_line in $BREAKDOWN_TASKS; do
            task_id=$(echo "$task_line" | awk '{print $1}' | tr -d ':')
            task_desc=$(echo "$task_line" | sed 's/^[^:]*: \[[^]]*\] //')
            echo "[$TIMESTAMP] Breaking down task: $task_desc"
            echo "[$TIMESTAMP] Task ID: $task_id"
            
            # Use the reasoning-based approach for breaking down tasks
            break_down_task "$task_id" "$task_desc"
            
            # Mark the task as in progress
            python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$task_id" "in-progress" --message "Task breakdown started"
            break
        done
    # Then look for pending tasks
    elif [ -n "$PENDING_TASKS" ]; then
        echo "[$TIMESTAMP] Found pending tasks:"
        
        # Extract the first pending task for this agent
        for task_line in $PENDING_TASKS; do
            task_id=$(echo "$task_line" | awk '{print $1}' | tr -d ':')
            task_desc=$(echo "$task_line" | sed 's/^[^:]*: \[[^]]*\] //')
            
            echo "[$TIMESTAMP] Processing task: $task_desc"
            echo "[$TIMESTAMP] Task ID: $task_id"
            
            # Use reasoning-based approach for regular tasks
            process_task_with_reasoning "$task_id" "$task_desc"
            
            # No need to process more than one task at a time
            break
        done
    else
        echo "[$TIMESTAMP] No pending tasks found for $CLAUDE_team_lead."
    fi
    
    # Check for messages
    echo "[$TIMESTAMP] Checking for messages..."
    MESSAGES=$(check_messages)
    
    if [ -n "$MESSAGES" ] && [ "$MESSAGES" != "No messages found" ]; then
        echo "[$TIMESTAMP] New messages:"
        echo "$MESSAGES"
        
        # Handle collaboration requests
        COLLAB_MSG=$(echo "$MESSAGES" | grep "\[COLLABORATION_REQUEST\]" || echo "")
        if [ -n "$COLLAB_MSG" ]; then
            echo "[$TIMESTAMP] Found collaboration request, processing..."
            # Extract sender and request details
            SENDER=$(echo "$COLLAB_MSG" | sed -n 's/.*From \([^:]*\):.*/\1/p')
            REQUEST=$(echo "$COLLAB_MSG" | sed 's/.*\[COLLABORATION_REQUEST\] //')
            
            # Process collaboration request
            process_collaboration_request "$SENDER" "$REQUEST"
        fi
        
        # Also handle breakdown task messages
        BREAKDOWN_MSG=$(echo "$MESSAGES" | grep "\[BREAKDOWN_REQUIRED\]" || echo "")
        if [ -n "$BREAKDOWN_MSG" ]; then
            echo "[$TIMESTAMP] Found breakdown task message, adding to our task list..."
            # The shared_state.py script will have already added the task, we'll pick it up on next iteration
        fi
        
        # Mark all messages as read
        for MSG_ID in $(echo "$MESSAGES" | grep -o "msg_[0-9_a-z]*"); do
            python3 "$REPO_ROOT/src/cli/state_cli.py" mark_read "$MSG_ID"
        done
    fi
    
    # Sleep before next check
    echo "[$TIMESTAMP] Sleeping for ${CHECK_INTERVAL:-5} seconds..."
    sleep ${CHECK_INTERVAL:-5}
done