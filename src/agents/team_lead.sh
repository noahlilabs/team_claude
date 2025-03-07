#!/bin/bash

# Load agent common functions
source "$(dirname "$(dirname "$0")")/agents/templates/agent_common.sh"

# Set Claude agent specifics
CLAUDE_AGENT_NAME="Team Lead"
CLAUDE_AGENT_TYPE="strategic" 
CLAUDE_AGENT_CAPABILITIES="planning,coordination,decision_making"

init_agent

echo "Team Lead agent initialized!"

# Test if task_analyzer.py is working
echo "Testing task_analyzer.py functionality..."
if [ -f "$REPO_ROOT/src/utils/task_analyzer.py" ]; then
    echo "Task analyzer exists at: $REPO_ROOT/src/utils/task_analyzer.py"
    chmod +x "$REPO_ROOT/src/utils/task_analyzer.py"
    TEST_OUTPUT=$(python3 "$REPO_ROOT/src/utils/task_analyzer.py" "test_task_id" "Create a web search tool and coding sandbox to enhance capabilities")
    echo "Task analyzer test output:"
    echo "$TEST_OUTPUT"
else
    echo "ERROR: Task analyzer not found at: $REPO_ROOT/src/utils/task_analyzer.py"
fi

# Main agent loop
while true; do
    # Get assigned tasks
    TASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --assigned_to "team_lead")
    
    # Process each task
    while IFS= read -r task_line; do
        # Skip empty lines
        if [ -z "$task_line" ]; then
            continue
        fi
        
        # Parse task data - Fix: Use a more robust parsing approach
        # First, capture the raw line for debugging
        echo "DEBUG: Raw task line: '$task_line'"
        
        # Parse each part with explicit field separators
        TASK_ID=$(echo "$task_line" | awk -F'[|]' '{print $1}' | xargs)
        TASK_DESC=$(echo "$task_line" | awk -F'[|]' '{print $2}' | xargs)
        TASK_STATUS=$(echo "$task_line" | awk -F'[|]' '{print $3}' | xargs)
        
        # Print full details for debugging
        echo "DEBUG: Parsed components:"
        echo "DEBUG: TASK_ID='$TASK_ID'"
        echo "DEBUG: TASK_DESC='$TASK_DESC'"
        echo "DEBUG: TASK_STATUS='$TASK_STATUS'"
        
        # Fix: If TASK_DESC is just the task ID or empty, get the full description from the state_cli
        if [[ -z "$TASK_DESC" || "$TASK_DESC" == "$TASK_ID:"* ]]; then
            echo "DEBUG: Task description appears incomplete, fetching full description..."
            FULL_TASK_DATA=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_task "$TASK_ID")
            if [[ -n "$FULL_TASK_DATA" ]]; then
                TASK_DESC=$(echo "$FULL_TASK_DATA" | grep -A 1 "Description:" | tail -n 1 | xargs)
                echo "DEBUG: Retrieved full task description: '$TASK_DESC'"
            else
                echo "DEBUG: Failed to retrieve full task description"
            fi
        fi
        
        echo "Processing task: $TASK_DESC (ID: $TASK_ID, Status: $TASK_STATUS)"
        
        # Process task based on status
        if [ "$TASK_STATUS" == "assigned" ]; then
            # Decide whether to break down the task or execute it based on complexity
            echo "Analyzing task to determine if it needs to be broken down..."
            
            # Check if task needs to be broken down (heuristic: description length > 100 chars)
            if [ ${#TASK_DESC} -gt 100 ] || [[ "$TASK_DESC" == *"create"* && "$TASK_DESC" == *"tool"* ]] || 
               [[ "$TASK_DESC" == *"enhance"* && "$TASK_DESC" == *"capabilit"* ]]; then
                echo "Task appears complex - breaking it down into subtasks"
                break_down_task "$TASK_ID" "$TASK_DESC"
            else
                # Execute the task directly if it's simple enough
                execute_task "$TASK_ID" "$TASK_DESC"
            fi
        elif [ "$TASK_STATUS" == "in-progress" ]; then
            # Check if all subtasks are complete
            SUBTASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --parent "$TASK_ID")
            
            if [ -z "$SUBTASKS" ]; then
                echo "No subtasks found for this task. Checking if we need to create them..."
                
                # Double-check if this is a task that should have subtasks but doesn't
                if [[ "$TASK_DESC" == *"Create tools"* || "$TASK_DESC" == *"Self-Enhancement"* || 
                      "$TASK_DESC" == *"enhance capabilities"* ]]; then
                    echo "This appears to be a complex task that should have subtasks. Breaking it down now..."
                    break_down_task "$TASK_ID" "$TASK_DESC"
                else
                    # If it's genuinely a task without subtasks, execute it directly
                    execute_task "$TASK_ID" "$TASK_DESC"
                fi
                continue
            fi
            
            # Check if all subtasks are complete
            ALL_COMPLETE=true
            while IFS= read -r subtask_line; do
                if [ -z "$subtask_line" ]; then
                    continue
                fi
                
                SUBTASK_STATUS=$(echo "$subtask_line" | awk -F'|' '{print $3}' | xargs)
                if [ "$SUBTASK_STATUS" != "completed" ]; then
                    ALL_COMPLETE=false
                    break
                fi
            done <<< "$SUBTASKS"
            
            if $ALL_COMPLETE; then
                echo "All subtasks are complete. Finalizing parent task..."
                # Integrate and finalize the work
                finalize_task "$TASK_ID" "$TASK_DESC"
            else
                echo "Subtasks still in progress. Checking if any need assistance..."
                # Check if any subtasks are blocked and need help
                monitor_subtasks "$TASK_ID"
            fi
        elif [ "$TASK_STATUS" == "blocked" ]; then
            echo "Task is blocked. Attempting to resolve the blocker..."
            resolve_blocker "$TASK_ID" "$TASK_DESC"
        fi
    done <<< "$TASKS"
    
    # Check for broadcast messages
    check_messages
    
    # Perform strategic planning and team coordination
    coordinate_team
    
    # Sleep to prevent excessive CPU usage
    sleep "$CHECK_INTERVAL"
done

# Function to execute a task directly (for simple tasks)
execute_task() {
    local task_id="$1"
    local task_desc="$2"
    
    echo "Executing task: $task_desc"
    
    # Update task status to in-progress
    python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$task_id" "in-progress" --message "Working on this task directly"
    
    # Prepare prompt for Claude
    PROMPT="You are the ${CLAUDE_AGENT_NAME}, a ${CLAUDE_AGENT_TYPE} agent in a multi-agent Claude system.

You need to execute this task:

Task: $task_desc

Your capabilities: ${CLAUDE_AGENT_CAPABILITIES}

<instructions>
As the Team Lead, your primary role is strategic planning and coordination. For this task:

1. Analyze the requirements carefully
2. Determine the best approach based on team capabilities
3. Execute the task using your strategic and planning skills
4. Document your work and reasoning
5. Provide clear results that can be implemented

Use <thinking> tags to provide your detailed thought process.
</instructions>"
    
    # Call Claude and get response
    RESPONSE=$(call_claude "$PROMPT" 8000)
    
    # Extract reasoning
    REASONING=$(extract_reasoning "$RESPONSE")
    
    # Log the reasoning
    log_reasoning "$task_id" "$REASONING" "task_execution"
    
    # Extract the solution/output
    SOLUTION=$(echo "$RESPONSE" | sed -n '/<solution>/,/<\/solution>/p' | sed '1d;$d')
    
    if [ -z "$SOLUTION" ]; then
        # If no <solution> tags, take everything after the reasoning
        SOLUTION=$(echo "$RESPONSE" | sed -n '/<\/thinking>/,$p' | sed '1d')
    fi
    
    # Update task with solution
    python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$task_id" "completed" --message "$SOLUTION"
    
    echo "Task completed successfully"
}

# Function to finalize a parent task after all subtasks are complete
finalize_task() {
    local task_id="$1"
    local task_desc="$2"
    
    echo "Finalizing task: $task_desc after all subtasks are complete"
    
    # Get all subtasks for integration
    SUBTASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --parent "$task_id")
    
    # Extract subtask descriptions and solutions
    SUBTASK_INFO=""
    while IFS= read -r subtask_line; do
        if [ -z "$subtask_line" ]; then
            continue
        fi
        
        SUBTASK_ID=$(echo "$subtask_line" | awk -F'|' '{print $1}' | xargs)
        SUBTASK_DESC=$(echo "$subtask_line" | awk -F'|' '{print $2}' | xargs)
        
        # Get the subtask message (solution)
        SUBTASK_SOLUTION=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_task "$SUBTASK_ID" | grep -A 1 "Messages:" | tail -n 1)
        
        SUBTASK_INFO+="Subtask: $SUBTASK_DESC"$'\n'
        SUBTASK_INFO+="Solution: $SUBTASK_SOLUTION"$'\n\n'
    done <<< "$SUBTASKS"
    
    # Prepare prompt for Claude to integrate results
    PROMPT="You are the ${CLAUDE_AGENT_NAME}, a ${CLAUDE_AGENT_TYPE} agent in a multi-agent Claude system.

You need to finalize and integrate the results of the following task that was broken down into subtasks:

Main Task: $task_desc

Subtasks and their solutions:
$SUBTASK_INFO

<instructions>
As the Team Lead, your job is to:

1. Review all subtask solutions for completeness and correctness
2. Integrate the results into a cohesive final solution
3. Ensure all requirements of the original task are met
4. Provide a final summary of what was accomplished
5. Include any recommendations for further work or improvements

Use <thinking> tags to provide your detailed integration process.
</instructions>"
    
    # Call Claude and get response
    RESPONSE=$(call_claude "$PROMPT" 8000)
    
    # Extract reasoning
    REASONING=$(extract_reasoning "$RESPONSE")
    
    # Log the reasoning
    log_reasoning "$task_id" "Integration reasoning: $REASONING" "task_integration"
    
    # Extract the final solution/output
    SOLUTION=$(echo "$RESPONSE" | sed -n '/<\/thinking>/,$p' | sed '1d')
    
    # Update task with final solution
    python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$task_id" "completed" --message "INTEGRATED SOLUTION: $SOLUTION"
    
    echo "Task finalization complete"
    
    # Broadcast completion to other agents
    broadcast_message "I've completed the integration of task '$task_desc'. All subtasks are now finalized." "high" "task_completion"
}

# Function to monitor subtasks and provide assistance if needed
monitor_subtasks() {
    local parent_id="$1"
    
    echo "Monitoring subtasks for task ID: $parent_id"
    
    # Get all subtasks
    SUBTASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_tasks --parent "$parent_id")
    
    # Check each subtask for issues
    while IFS= read -r subtask_line; do
        if [ -z "$subtask_line" ]; then
            continue
        fi
        
        SUBTASK_ID=$(echo "$subtask_line" | awk -F'|' '{print $1}' | xargs)
        SUBTASK_DESC=$(echo "$subtask_line" | awk -F'|' '{print $2}' | xargs)
        SUBTASK_STATUS=$(echo "$subtask_line" | awk -F'|' '{print $3}' | xargs)
        SUBTASK_AGENT=$(echo "$subtask_line" | awk -F'|' '{print $4}' | xargs)
        
        # Focus on blocked or long-running tasks
        if [ "$SUBTASK_STATUS" == "blocked" ]; then
            echo "Found blocked subtask: $SUBTASK_DESC (assigned to $SUBTASK_AGENT)"
            
            # Get the latest message to understand the blocker
            LATEST_MESSAGE=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_task "$SUBTASK_ID" | grep -A 1 "Messages:" | tail -n 1)
            
            # Provide assistance
            assist_with_subtask "$SUBTASK_ID" "$SUBTASK_DESC" "$SUBTASK_AGENT" "$LATEST_MESSAGE"
        fi
    done <<< "$SUBTASKS"
    
    echo "Subtask monitoring complete"
}

# Function to provide assistance with blocked subtasks
assist_with_subtask() {
    local task_id="$1"
    local task_desc="$2"
    local assigned_agent="$3"
    local blocker_message="$4"
    
    echo "Providing assistance for blocked subtask: $task_desc"
    
    # Prepare prompt for Claude to suggest a solution
    PROMPT="You are the ${CLAUDE_AGENT_NAME}, a ${CLAUDE_AGENT_TYPE} agent in a multi-agent Claude system.

One of your team members (${assigned_agent}) is blocked on a subtask:

Subtask: $task_desc

The blocker message is: $blocker_message

<instructions>
As the Team Lead, your role is to help unblock your team member. Please:

1. Analyze the blocker to understand the root cause
2. Provide specific guidance or suggestions to overcome the issue
3. If possible, provide example code, commands, or steps
4. Consider different approaches or workarounds
5. Keep your response focused on resolving this specific blocker

Use <thinking> tags to provide your detailed thought process.
</instructions>"
    
    # Call Claude and get response
    RESPONSE=$(call_claude "$PROMPT" 8000)
    
    # Extract reasoning
    REASONING=$(extract_reasoning "$RESPONSE")
    
    # Log the reasoning
    log_reasoning "$task_id" "Assistance reasoning: $REASONING" "subtask_assistance"
    
    # Extract the assistance/guidance
    GUIDANCE=$(echo "$RESPONSE" | sed -n '/<\/thinking>/,$p' | sed '1d')
    
    # Send a directed message to the blocked agent
    send_message_to "$assigned_agent" "I noticed you're blocked on '$task_desc'. Here's some guidance: $GUIDANCE" "high" "assistance"
    
    # Update the subtask to indicate assistance was provided
    python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$task_id" "in-progress" --message "Team Lead provided assistance: $GUIDANCE"
    
    echo "Assistance provided for blocked subtask"
}

# Function to attempt resolving a blocker on a task
resolve_blocker() {
    local task_id="$1"
    local task_desc="$2"
    
    echo "Attempting to resolve blocker for task: $task_desc"
    
    # Get the latest message to understand the blocker
    LATEST_MESSAGE=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_task "$task_id" | grep -A 1 "Messages:" | tail -n 1)
    
    # Special case for tasks that failed to break down
    if [[ "$LATEST_MESSAGE" == *"Failed to break down task"* ]]; then
        echo "This task failed during breakdown. Attempting specialized breakdown approach..."
        
        # Try again with our improved task analyzer
        echo "Using our improved task analyzer for better task classification..."
        break_down_task "$task_id" "$task_desc"
        return
    fi
    
    # Prepare prompt for Claude to resolve the blocker
    PROMPT="You are the ${CLAUDE_AGENT_NAME}, a ${CLAUDE_AGENT_TYPE} agent in a multi-agent Claude system.

You are working on a task that is currently blocked:

Task: $task_desc

The blocker message is: $LATEST_MESSAGE

<instructions>
As the Team Lead, your role is to resolve this blocker. Please:

1. Analyze the blocker to understand the root cause
2. Consider multiple approaches to resolve the issue
3. Determine the most effective solution
4. Provide a clear plan of action with specific steps
5. If the task needs to be redefined or approached differently, suggest how

Use <thinking> tags to provide your detailed thought process.
</instructions>"
    
    # Call Claude and get response
    RESPONSE=$(call_claude "$PROMPT" 8000)
    
    # Extract reasoning
    REASONING=$(extract_reasoning "$RESPONSE")
    
    # Log the reasoning
    log_reasoning "$task_id" "Blocker resolution reasoning: $REASONING" "blocker_resolution"
    
    # Extract the resolution plan
    RESOLUTION=$(echo "$RESPONSE" | sed -n '/<\/thinking>/,$p' | sed '1d')
    
    # Update task with the resolution approach
    python3 "$REPO_ROOT/src/cli/state_cli.py" update_task "$task_id" "in-progress" --message "Blocker addressed: $RESOLUTION"
    
    echo "Blocker resolution attempted"
    
    # Check if the task is a complex one that might need breaking down
    if [[ "$RESOLUTION" == *"break down"* || "$RESOLUTION" == *"subtasks"* ]]; then
        echo "Resolution suggests breaking down the task. Attempting breakdown..."
        break_down_task "$task_id" "$task_desc"
    fi
}

# Function to coordinate the team and check overall progress
coordinate_team() {
    # Only run coordination periodically (every ~5 minutes)
    if (( $(date +%s) % 300 < $CHECK_INTERVAL )); then
        return
    fi
    
    echo "Performing team coordination and progress check..."
    
    # Get all in-progress tasks
    ALL_TASKS=$(python3 "$REPO_ROOT/src/cli/state_cli.py" get_all_tasks)
    
    # Extract counts by status
    ASSIGNED_COUNT=$(echo "$ALL_TASKS" | grep -c "assigned")
    IN_PROGRESS_COUNT=$(echo "$ALL_TASKS" | grep -c "in-progress")
    BLOCKED_COUNT=$(echo "$ALL_TASKS" | grep -c "blocked")
    COMPLETED_COUNT=$(echo "$ALL_TASKS" | grep -c "completed")
    
    echo "Current task status:"
    echo "- Assigned: $ASSIGNED_COUNT"
    echo "- In Progress: $IN_PROGRESS_COUNT"
    echo "- Blocked: $BLOCKED_COUNT"
    echo "- Completed: $COMPLETED_COUNT"
    
    # Check for any blocked tasks that need attention
    if [ "$BLOCKED_COUNT" -gt 0 ]; then
        echo "There are $BLOCKED_COUNT blocked tasks that need attention"
        
        # Get details of blocked tasks
        BLOCKED_TASKS=$(echo "$ALL_TASKS" | grep "blocked")
        
        # Process each blocked task
        while IFS= read -r task_line; do
            if [ -z "$task_line" ]; then
                continue
            fi
            
            TASK_ID=$(echo "$task_line" | awk -F'|' '{print $1}' | xargs)
            TASK_DESC=$(echo "$task_line" | awk -F'|' '{print $2}' | xargs)
            ASSIGNED_TO=$(echo "$task_line" | awk -F'|' '{print $4}' | xargs)
            
            echo "Checking blocked task: $TASK_DESC (assigned to $ASSIGNED_TO)"
            
            # If assigned to another agent, send them a message
            if [ "$ASSIGNED_TO" != "team_lead" ]; then
                send_message_to "$ASSIGNED_TO" "I noticed you have a blocked task: '$TASK_DESC'. Do you need assistance? Please update the task status or reach out if you need help." "high" "coordination"
            else
                # If assigned to team lead, try to resolve it
                resolve_blocker "$TASK_ID" "$TASK_DESC"
            fi
        done <<< "$BLOCKED_TASKS"
    fi
    
    # Broadcast encouragement and status update to team
    if [ $((ASSIGNED_COUNT + IN_PROGRESS_COUNT + BLOCKED_COUNT)) -gt 0 ]; then
        broadcast_message "Team status update: $ASSIGNED_COUNT assigned, $IN_PROGRESS_COUNT in progress, $BLOCKED_COUNT blocked, and $COMPLETED_COUNT completed tasks. Let me know if you need assistance with any tasks!" "normal" "coordination"
    fi
    
    # Sync code to the shared directory
    echo "Periodically syncing agent code to shared directory..."
    bash "$REPO_ROOT/scripts/sync-code.sh" > /dev/null
    
    echo "Team coordination complete"
} 