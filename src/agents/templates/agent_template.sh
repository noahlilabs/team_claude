#!/bin/bash
# =============================================================================
# Multi-Agent Claude System - Enhanced Agent Script
# =============================================================================

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")/../../.." && pwd)"  # Navigate to the repository root

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
export CLAUDE_AGENT_NAME="AGENT_NAME"
export CLAUDE_AGENT_TYPE="AGENT_TYPE"
export CLAUDE_AGENT_CAPABILITIES="AGENT_CAPABILITIES"
export CLAUDE_BRANCH_NAME="BRANCH_NAME"
export CLAUDE_STATE_FILE="$REPO_ROOT/claude_state.json"
export CLAUDE_WORKING_DIR="WORKING_DIR"
export CLAUDE_HEALTH_CHECK_INTERVAL=30  # seconds

# Agent-specific context storage - ensures each agent has its own context
export CLAUDE_CONTEXT_DIR="$CLAUDE_WORKING_DIR/context"
mkdir -p "$CLAUDE_CONTEXT_DIR"
export CLAUDE_CONTEXT_FILE="$CLAUDE_CONTEXT_DIR/agent_context.json"

# Initialize context file if it doesn't exist
if [ ! -f "$CLAUDE_CONTEXT_FILE" ]; then
    echo "{\"tasks\": {}, \"messages\": [], \"context\": {}, \"knowledge\": {}}" > "$CLAUDE_CONTEXT_FILE"
    echo "Initialized agent-specific context file at $CLAUDE_CONTEXT_FILE"
fi

# Import common agent functions
if [ -f "$REPO_ROOT/src/agents/templates/agent_common.sh" ]; then
    source "$REPO_ROOT/src/agents/templates/agent_common.sh"
else
    echo "Error: Could not find common agent functions at $REPO_ROOT/src/agents/templates/agent_common.sh"
    exit 1
fi

# Load API key from .env file
load_api_key

# Function to update agent's context with task information
update_agent_context() {
    local task_id="$1"
    local task_desc="$2"
    local status="$3"
    
    # Use jq to update the context file
    if command -v jq >/dev/null 2>&1; then
        # Create temporary file
        local temp_file=$(mktemp)
        
        # Add task to context
        jq --arg tid "$task_id" --arg desc "$task_desc" --arg status "$status" --arg time "$(date +"%Y-%m-%d %H:%M:%S")" \
           '.tasks[$tid] = {"description": $desc, "status": $status, "last_updated": $time}' \
           "$CLAUDE_CONTEXT_FILE" > "$temp_file"
        
        # Move temporary file to context file
        mv "$temp_file" "$CLAUDE_CONTEXT_FILE"
        
        echo "Updated agent context with task information"
    else
        echo "Warning: jq not installed, skipping context update"
    fi
}

# Function to process tagged messages
process_tagged_message() {
    local message="$1"
    
    # Extract tags from message
    local from_agent=$(echo "$message" | grep -o '\[@FROM:[^]]*\]' | sed 's/\[@FROM://;s/\]//')
    local broadcast=$(echo "$message" | grep -o '\[@BROADCAST\]' || echo "")
    local tag=$(echo "$message" | grep -o '\[@TAG:[^]]*\]' | sed 's/\[@TAG://;s/\]//' || echo "")
    local task_id=$(echo "$message" | grep -o '\[@TASK:[^]]*\]' | sed 's/\[@TASK://;s/\]//' || echo "")
    local code_change=$(echo "$message" | grep -o '\[@CODE_CHANGE\]' || echo "")
    local status_update=$(echo "$message" | grep -o '\[@STATUS_UPDATE\]' || echo "")
    local capability=$(echo "$message" | grep -o '\[@CAPABILITY:[^]]*\]' | sed 's/\[@CAPABILITY://;s/\]//' || echo "")
    
    # Clean message by removing tags
    local clean_message=$(echo "$message" | sed 's/\[@[^]]*\]//g' | xargs)
    
    echo "Processing message from $from_agent"
    
    # Handle different message types
    if [ -n "$broadcast" ]; then
        echo "Broadcast message received from $from_agent"
        
        if [ -n "$status_update" ] && [ -n "$task_id" ]; then
            echo "Status update for task $task_id: $clean_message"
            # Update our knowledge of what other agents are working on
            if command -v jq >/dev/null 2>&1; then
                local temp_file=$(mktemp)
                jq --arg agent "$from_agent" --arg task "$task_id" --arg status "$clean_message" --arg time "$(date +"%Y-%m-%d %H:%M:%S")" \
                  '.knowledge.agent_tasks[$agent][$task] = {"status": $status, "updated_at": $time}' \
                  "$CLAUDE_CONTEXT_FILE" > "$temp_file"
                mv "$temp_file" "$CLAUDE_CONTEXT_FILE"
            fi
        elif [ -n "$code_change" ] && [ -n "$task_id" ]; then
            echo "Code change for task $task_id: $clean_message"
            # Update our knowledge of code changes
            if command -v jq >/dev/null 2>&1; then
                local temp_file=$(mktemp)
                local file_path=$(echo "$message" | grep -o '\[@FILE:[^]]*\]' | sed 's/\[@FILE://;s/\]//')
                jq --arg task "$task_id" --arg file "$file_path" --arg desc "$clean_message" --arg agent "$from_agent" --arg time "$(date +"%Y-%m-%d %H:%M:%S")" \
                  '.knowledge.code_changes[$task][$file] = {"description": $desc, "agent": $agent, "updated_at": $time}' \
                  "$CLAUDE_CONTEXT_FILE" > "$temp_file"
                mv "$temp_file" "$CLAUDE_CONTEXT_FILE"
            fi
        fi
    # Handle collaboration requests or responses
    elif [[ "$clean_message" == *"[COLLABORATION_REQUEST]"* ]]; then
        echo "Collaboration request from $from_agent"
        local request=$(echo "$clean_message" | sed 's/\[COLLABORATION_REQUEST\] //')
        process_collaboration_request "$from_agent" "$request"
    elif [[ "$clean_message" == *"[COLLABORATION_RESPONSE]"* ]]; then
        echo "Collaboration response from $from_agent"
        # Update our knowledge with the collaboration response
        if command -v jq >/dev/null 2>&1; then
            local temp_file=$(mktemp)
            local response=$(echo "$clean_message" | sed 's/\[COLLABORATION_RESPONSE\] //')
            jq --arg agent "$from_agent" --arg response "$response" --arg time "$(date +"%Y-%m-%d %H:%M:%S")" \
              '.knowledge.collaboration_responses[$agent] = {"response": $response, "received_at": $time}' \
              "$CLAUDE_CONTEXT_FILE" > "$temp_file"
            mv "$temp_file" "$CLAUDE_CONTEXT_FILE"
        fi
    fi
}

# =============================================================================
# Main Agent Loop
# =============================================================================

echo "Starting Claude Agent: $CLAUDE_AGENT_NAME (Type: $CLAUDE_AGENT_TYPE)"
echo "Capabilities: $CLAUDE_AGENT_CAPABILITIES"
echo "Working directory: $CLAUDE_WORKING_DIR"
cd "$CLAUDE_WORKING_DIR" || exit 1

# Log that the agent is starting up
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
echo "[$TIMESTAMP] Agent $CLAUDE_AGENT_NAME starting up..."

# Register agent with the state manager
echo "[$TIMESTAMP] Registering agent $CLAUDE_AGENT_NAME with capabilities: $CLAUDE_AGENT_CAPABILITIES"
python3 "$REPO_ROOT/src/cli/state_cli.py" register_agent "$CLAUDE_AGENT_NAME" "$CLAUDE_AGENT_TYPE" "$CLAUDE_AGENT_CAPABILITIES"
if [ $? -ne 0 ]; then
    echo "[$TIMESTAMP] WARNING: Agent registration failed"
else
    echo "[$TIMESTAMP] Agent successfully registered"
fi

# Log startup event to shared state
python3 "$REPO_ROOT/src/cli/state_cli.py" log_reasoning "$CLAUDE_AGENT_NAME" "startup" "Agent started successfully with capabilities: $CLAUDE_AGENT_CAPABILITIES" --tags "startup"

# Announce agent startup to other agents
broadcast_message "Agent $CLAUDE_AGENT_NAME has started with capabilities: $CLAUDE_AGENT_CAPABILITIES" "normal" "agent_status"

echo "[$TIMESTAMP] Registered agent $CLAUDE_AGENT_NAME with the system"

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
    echo "[$TIMESTAMP] Looking for tasks for branch $CLAUDE_BRANCH_NAME:"
    BRANCH_TASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks "$CLAUDE_BRANCH_NAME")
    echo "$BRANCH_TASKS"
    
    # First, specifically look for breakdown tasks (high priority)
    echo "[$TIMESTAMP] Looking for breakdown tasks:"
    BREAKDOWN_TASKS=$(echo "$BRANCH_TASKS" | grep "\[BREAKDOWN_REQUIRED\]" || echo "")
    
    # Then look for any pending tasks assigned to this agent
    echo "[$TIMESTAMP] Looking for pending tasks assigned to $CLAUDE_AGENT_NAME:"
    PENDING_TASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --agent "$CLAUDE_AGENT_NAME" --status "pending")
    
    # Process tasks - prioritize breakdown tasks
    if [ -n "$BREAKDOWN_TASKS" ]; then
        echo "[$TIMESTAMP] Found tasks requiring breakdown:"
        for task_line in $BREAKDOWN_TASKS; do
            task_id=$(echo "$task_line" | awk '{print $1}' | tr -d ':')
            task_desc=$(echo "$task_line" | sed 's/^[^:]*: \[[^]]*\] //')
            echo "[$TIMESTAMP] Breaking down task: $task_desc"
            echo "[$TIMESTAMP] Task ID: $task_id"
            
            # Update agent's own context
            update_agent_context "$task_id" "$task_desc" "breaking_down"
            
            # Use the reasoning-based approach for breaking down tasks
            break_down_task "$task_id" "$task_desc"
            
            # Update context after breakdown
            update_agent_context "$task_id" "$task_desc" "broken_down"
            
            # Notify other agents about task breakdown
            share_work_status "$task_id" "Task broken down. Check if any subtasks are assigned to you."
            
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
            
            # Update agent's context before processing
            update_agent_context "$task_id" "$task_desc" "processing"
            
            # Notify other agents that we're working on this task
            share_work_status "$task_id" "Started working on task: $task_desc"
            
            # Use reasoning-based approach for regular tasks
            process_task_with_reasoning "$task_id" "$task_desc"
            
            # Update context after processing
            update_agent_context "$task_id" "$task_desc" "completed"
            
            # Notify other agents about task completion
            share_work_status "$task_id" "Completed task: $task_desc"
            
            # No need to process more than one task at a time
            break
        done
    else
        echo "[$TIMESTAMP] No pending tasks found for $CLAUDE_AGENT_NAME."
    fi
    
    # Check for messages
    echo "[$TIMESTAMP] Checking for messages..."
    MESSAGES=$(check_messages)
    
    if [ -n "$MESSAGES" ] && [ "$MESSAGES" != "No messages found" ]; then
        echo "[$TIMESTAMP] New messages:"
        echo "$MESSAGES"
        
        # Process each message line
        while IFS= read -r message_line; do
            if [[ "$message_line" =~ msg_[0-9_a-z]*:.* ]]; then
                # Extract message ID and content
                MSG_ID=$(echo "$message_line" | grep -o "msg_[0-9_a-z]*")
                MSG_CONTENT=$(echo "$message_line" | sed 's/^[^:]*: //')
                
                # Process tagged message
                process_tagged_message "$MSG_CONTENT"
                
                # Mark message as read
                python3 "$REPO_ROOT/src/cli/state_cli.py" mark_read "$MSG_ID"
            fi
        done <<< "$MESSAGES"
    fi
    
    # Sleep before next check
    echo "[$TIMESTAMP] Sleeping for ${CHECK_INTERVAL:-5} seconds..."
    sleep ${CHECK_INTERVAL:-5}
done