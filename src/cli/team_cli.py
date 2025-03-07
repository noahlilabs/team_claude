#!/usr/bin/env python3
"""
Multi-Agent Claude Team CLI

A simplified command line interface for users to interact with the multi-agent system.
"""

import os
import sys
import argparse
import subprocess
import time
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core import config
from src.core.state_manager import state_manager

def print_header(title):
    """Print a header with a border"""
    width = 60
    print("=" * width)
    print(title.center(width))
    print("=" * width)

def start_team(num_agents=4):
    """Start the multi-agent team with specified number of agents"""
    print_header("Starting Claude Agent Team")
    
    # Check if TMUX session exists
    result = subprocess.run(
        ["tmux", "has-session", "-t", config.TMUX_SESSION_NAME], 
        capture_output=True
    )
    
    if result.returncode == 0:
        print(f"TMUX session '{config.TMUX_SESSION_NAME}' already exists.")
        print("Please shut down existing team first.")
        return False
    
    # Create TMUX session
    subprocess.run(["tmux", "new-session", "-d", "-s", config.TMUX_SESSION_NAME])
    
    # Start the team lead first
    team_lead_dir = Path(config.AGENTS["team_lead"]["working_dir"])
    team_lead_script = team_lead_dir / "claude_agent.sh"
    
    if not team_lead_script.exists():
        # Create the agent structure from templates
        create_agent_from_template("team_lead", config.AGENTS["team_lead"])
    
    # Load the API key to pass to the tmux session
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    
    print("Starting Team Lead agent...")
    # Create a window for the team lead
    subprocess.run(["tmux", "new-window", "-d", "-t", config.TMUX_SESSION_NAME, "-n", "team_lead"])
    
    # Send the command to start the agent script in that window
    start_cmd = f"cd '{team_lead_dir}' && bash '{team_lead_script}'"
    subprocess.run(["tmux", "send-keys", "-t", f"{config.TMUX_SESSION_NAME}:team_lead", 
                   start_cmd, "C-m"])
    print(f"Team Lead agent started")
    
    # Start other agents
    agent_count = 0
    for agent_id, agent_config in config.AGENTS.items():
        if agent_id == "team_lead":
            continue
            
        if agent_count >= num_agents - 1:  # -1 because we already started team lead
            break
            
        agent_script = Path(agent_config["working_dir"]) / "claude_agent.sh"
        
        if not agent_script.exists():
            # Create the agent from template
            create_agent_from_template(agent_id, agent_config)
        
        print(f"Starting {agent_config['name']} agent...")
        
        # Create a window for the agent
        subprocess.run(["tmux", "new-window", "-d", "-t", config.TMUX_SESSION_NAME, "-n", agent_config['name']])
        
        # Send the command to start the agent script in that window
        agent_dir = Path(agent_config["working_dir"])
        start_cmd = f"cd '{agent_dir}' && bash '{agent_script}'"
        subprocess.run(["tmux", "send-keys", "-t", f"{config.TMUX_SESSION_NAME}:{agent_config['name']}", 
                      start_cmd, "C-m"])
        
        print(f"Agent {agent_config['name']} started")
        
        agent_count += 1
        time.sleep(1)  # Small delay to prevent race conditions
    
    print(f"Started {agent_count + 1} agents (including Team Lead)")
    print(f"To attach to the session: tmux attach-session -t {config.TMUX_SESSION_NAME}")
    return True

def create_agent_from_template(agent_id, agent_config):
    """Create an agent from the template files"""
    print(f"Creating agent {agent_id} from template...")
    
    # Create agent directory if it doesn't exist
    agent_dir = Path(agent_config["working_dir"])
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # Create context directory for this agent
    context_dir = agent_dir / "context"
    context_dir.mkdir(exist_ok=True)
    
    # Create agent script from template
    template_path = Path(config.AGENT_TEMPLATE_SCRIPT)
    agent_script_path = agent_dir / "claude_agent.sh"
    
    if not template_path.exists():
        print(f"Error: Template script not found at {template_path}")
        return False
    
    # Read template
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Replace placeholders
    agent_script = template_content.replace("AGENT_NAME", agent_config["name"])
    agent_script = agent_script.replace("AGENT_TYPE", agent_config["type"])
    agent_script = agent_script.replace("AGENT_CAPABILITIES", ",".join(agent_config["capabilities"]))
    agent_script = agent_script.replace("BRANCH_NAME", agent_config["branch"])
    agent_script = agent_script.replace("WORKING_DIR", str(agent_dir))
    
    # Write agent script
    with open(agent_script_path, 'w') as f:
        f.write(agent_script)
    
    # Make script executable
    os.chmod(agent_script_path, 0o755)
    
    # Create a simple README for the agent
    with open(agent_dir / "README.md", 'w') as f:
        f.write(f"# {agent_config['name']} Agent\n\n")
        f.write(f"Type: {agent_config['type']}\n")
        f.write(f"Capabilities: {', '.join(agent_config['capabilities'])}\n")
    
    # Create a simple app.py file for the agent
    with open(agent_dir / "app.py", 'w') as f:
        f.write('"""Sample app file for the agent"""\n\n')
        f.write('def main():\n')
        f.write('    print("Hello from the agent!")\n\n')
        f.write('if __name__ == "__main__":\n')
        f.write('    main()\n')
    
    print(f"Agent {agent_id} created successfully at {agent_dir}")
    return True

def shutdown_team():
    """Shut down the multi-agent team"""
    print_header("Shutting Down Claude Agent Team")
    
    # Check if TMUX session exists
    result = subprocess.run(
        ["tmux", "has-session", "-t", config.TMUX_SESSION_NAME], 
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f"TMUX session '{config.TMUX_SESSION_NAME}' not found.")
        return False
    
    # Kill the session
    subprocess.run(["tmux", "kill-session", "-t", config.TMUX_SESSION_NAME])
    print(f"Terminated TMUX session '{config.TMUX_SESSION_NAME}'")
    return True

def create_task(description, priority="medium", capabilities=None):
    """Create a new high-level task"""
    print_header("Creating New Task")
    
    # Parse capabilities if provided as string
    if capabilities and isinstance(capabilities, str):
        capabilities = [cap.strip() for cap in capabilities.split(',')]
    
    # Find a manager agent (team lead by default)
    manager_agent = "team_lead"
    agents = state_manager.get_agents(status="active", agent_type="manager")
    if agents:
        manager_agent = agents[0]["id"]
    
    # Find the branch for the manager agent
    manager_branch = "master"  # Default
    for agent_id, agent_config in config.AGENTS.items():
        if agent_config["name"] == manager_agent:
            manager_branch = agent_config["branch"]
            break
    
    # Add the task to the manager agent's branch
    task_id = state_manager.add_task(
        branch=manager_branch,
        task_description=f"[BREAKDOWN_REQUIRED] {description}",
        assigned_to=manager_agent,
        priority=priority,
        required_capabilities=capabilities
    )
    
    # Also create a message to the manager about this meta task
    state_manager.add_message(
        from_agent="system",
        to_agent=manager_agent,
        content=f"[BREAKDOWN_REQUIRED] New high-level task requires breakdown: '{description}'. Task ID: {task_id}",
        priority="high"
    )
    
    print(f"Task created: {description}")
    print(f"Task ID: {task_id}")
    print(f"Assigned to: {manager_agent}")
    print(f"The {manager_agent} agent will break this down into subtasks.")
    
    return task_id

def list_tasks():
    """List all current tasks"""
    print_header("Current Tasks")
    
    tasks = state_manager.get_tasks()
    
    if not tasks:
        print("No tasks found")
        return
    
    # Group tasks by branch and status
    by_branch = {}
    for task in tasks:
        branch = task.get("branch", "unknown")
        if branch not in by_branch:
            by_branch[branch] = []
        by_branch[branch].append(task)
    
    # Print tasks by branch
    for branch, branch_tasks in by_branch.items():
        print(f"\nBranch: {branch}")
        print("-" * len(f"Branch: {branch}"))
        
        # Group by status
        by_status = {}
        for task in branch_tasks:
            status = task.get("status", "pending")
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(task)
        
        # Print by status
        for status in config.TASK_STATUS_TYPES:
            if status in by_status and by_status[status]:
                print(f"\n  {status.upper()}:")
                for task in by_status[status]:
                    # Check if it's a subtask
                    prefix = "  └─ " if task.get("parent_id") else "  "
                    assigned = f" (Assigned to: {task.get('assigned_to', 'Unassigned')})"
                    print(f"{prefix}{task['id']}: {task['description']}{assigned}")
    
    return True

def task_summary():
    """Show a summary of tasks by status"""
    print_header("Task Summary")
    
    tasks = state_manager.get_tasks()
    
    if not tasks:
        print("No tasks found")
        return
    
    # Group by status
    by_status = {}
    for status in config.TASK_STATUS_TYPES:
        by_status[status] = 0
    
    for task in tasks:
        status = task.get("status", "pending")
        by_status[status] = by_status.get(status, 0) + 1
    
    # Calculate total and completion rate
    total = sum(by_status.values())
    completed = by_status.get("completed", 0)
    completion_rate = (completed / total) * 100 if total > 0 else 0
    
    # Print summary
    for status, count in by_status.items():
        if count > 0:
            print(f"{status.upper()}: {count}")
    
    print(f"\nTotal Tasks: {total}")
    print(f"Completion Rate: {completion_rate:.1f}%")
    
    return True

def list_agents():
    """List all agents and their status"""
    print_header("Agent Status")
    
    agents = state_manager.get_agents()
    
    if not agents:
        print("No agents found")
        return
    
    print(f"Found {len(agents)} agents:\n")
    
    # First list active agents
    active_agents = [a for a in agents if a.get("status") == "active"]
    if active_agents:
        print(f"ACTIVE ({len(active_agents)}):")
        for agent in active_agents:
            tasks_current = len(agent.get("tasks_current", []))
            tasks_completed = agent.get("tasks_completed", 0)
            print(f"  {agent['id']} ({agent.get('type', 'Unknown')})")
            print(f"    Capabilities: {', '.join(agent.get('capabilities', []))}")
            print(f"    Current Tasks: {tasks_current}, Completed: {tasks_completed}")
    
    # Then list inactive agents
    inactive_agents = [a for a in agents if a.get("status") != "active"]
    if inactive_agents:
        print(f"\nINACTIVE ({len(inactive_agents)}):")
        for agent in inactive_agents:
            print(f"  {agent['id']} ({agent.get('type', 'Unknown')})")
    
    return True

def create_agent(agent_type, capabilities=None, description=None, start=False):
    """Create a new dynamic agent"""
    print_header(f"Creating New {agent_type.capitalize()} Agent")
    
    # Parse capabilities if provided as string
    if capabilities and isinstance(capabilities, str):
        capabilities = [cap.strip() for cap in capabilities.split(',')]
    elif not capabilities:
        # Use default capabilities for this agent type
        capabilities = config.AGENT_TYPES[agent_type]["capabilities"]
    
    # Use default description if not provided
    if not description:
        description = config.AGENT_TYPES[agent_type]["description"]
    
    # Generate a unique agent ID
    timestamp = int(time.time())
    agent_id = f"{agent_type}_{timestamp}"
    
    # Create agent directory
    agent_dir = config.AGENTS_DIR / f"dynamic_{agent_id}"
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # Create agent configuration
    agent_config = {
        "name": agent_id,
        "type": agent_type,
        "branch": f"dynamic-{agent_id}",
        "description": description,
        "capabilities": capabilities,
        "working_dir": str(agent_dir)
    }
    
    # Create agent from template
    create_agent_from_template(agent_id, agent_config)
    
    # Register the agent in the shared state
    state_manager.register_agent(agent_id, agent_type, capabilities)
    
    # Register branch
    state_manager.register_branch(f"dynamic-{agent_id}", description, agent_id)
    
    print(f"Created dynamic agent {agent_id} of type {agent_type}")
    print(f"Working directory: {agent_dir}")
    
    # Start the agent if requested
    if start:
        start_agent(agent_id)
    
    return agent_id

def start_agent(agent_id):
    """Start a specific agent"""
    print_header(f"Starting Agent: {agent_id}")
    
    # Find the agent configuration
    agent_dir = None
    
    # Check if agent exists in state
    agents = state_manager.get_agents()
    for agent in agents:
        if agent.get("id") == agent_id:
            # Found the agent, now find its directory
            for a_id, a_config in config.AGENTS.items():
                if a_config["name"] == agent_id:
                    agent_dir = a_config["working_dir"]
                    break
            
            # If not found in config, try to construct it
            if not agent_dir:
                agent_dir = str(config.AGENTS_DIR / f"dynamic_{agent_id}")
            
            break
    
    if not agent_dir or not Path(agent_dir).exists():
        print(f"Error: Could not find directory for agent {agent_id}")
        return False
    
    # Check if agent script exists
    agent_script = Path(agent_dir) / "claude_agent.sh"
    if not agent_script.exists():
        print(f"Error: Agent script not found at {agent_script}")
        return False
    
    # Check if TMUX session exists, create it if not
    result = subprocess.run(
        ["tmux", "has-session", "-t", config.TMUX_SESSION_NAME], 
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f"Creating new TMUX session '{config.TMUX_SESSION_NAME}'")
        subprocess.run(["tmux", "new-session", "-d", "-s", config.TMUX_SESSION_NAME])
    
    # Start agent in a new window
    subprocess.run([
        "tmux", "new-window", "-t", config.TMUX_SESSION_NAME, 
        "-n", agent_id, 
        f"bash {str(agent_script)}"
    ])
    
    print(f"Started agent {agent_id}")
    print(f"To view agent: tmux select-window -t {config.TMUX_SESSION_NAME}:{agent_id}")
    return True

def attach_to_session():
    """Attach to the TMUX session"""
    result = subprocess.run(
        ["tmux", "has-session", "-t", config.TMUX_SESSION_NAME], 
        capture_output=True
    )
    
    if result.returncode != 0:
        print(f"TMUX session '{config.TMUX_SESSION_NAME}' not found.")
        return False
    
    # Attach to the session
    os.execvp("tmux", ["tmux", "attach-session", "-t", config.TMUX_SESSION_NAME])
    # The above call replaces the current process, so we won't return from here

def print_status():
    """Print the status of the entire system"""
    print_header("Claude Multi-Agent System Status")
    
    # Check if TMUX session exists
    tmux_result = subprocess.run(
        ["tmux", "has-session", "-t", config.TMUX_SESSION_NAME], 
        capture_output=True
    )
    
    if tmux_result.returncode == 0:
        print("System: RUNNING")
    else:
        print("System: STOPPED")
    
    # Get agent information
    agents = state_manager.get_agents()
    print(f"\nAgents: {len(agents)} registered")
    
    active = 0
    for agent in agents:
        if agent.get("status") == "active":
            active += 1
    
    print(f"  - {active} active")
    print(f"  - {len(agents) - active} inactive")
    
    # Get task summary
    tasks = state_manager.get_tasks()
    
    # Group by status
    by_status = {}
    for status in config.TASK_STATUS_TYPES:
        by_status[status] = 0
    
    for task in tasks:
        status = task.get("status", "pending")
        by_status[status] = by_status.get(status, 0) + 1
    
    print("\nTasks:")
    for status, count in by_status.items():
        if count > 0:
            print(f"  - {status}: {count}")
    
    # Calculate completion rate
    total = sum(by_status.values())
    completed = by_status.get("completed", 0)
    if total > 0:
        completion_rate = (completed / total) * 100
        print(f"\nCompletion rate: {completion_rate:.1f}%")
    
    return True

def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Claude Team Interface")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start team command
    start_parser = subparsers.add_parser("start", help="Start the agent team")
    start_parser.add_argument("--agents", type=int, default=4, 
                            help="Number of agents to start (including Team Lead)")
    
    # Shutdown team command
    shutdown_parser = subparsers.add_parser("stop", help="Stop the agent team")
    
    # Create task command
    task_parser = subparsers.add_parser("task", help="Create a new task")
    task_parser.add_argument("description", nargs="+", help="Task description")
    task_parser.add_argument("--priority", choices=config.TASK_PRIORITY_LEVELS, 
                           default="medium", help="Task priority")
    task_parser.add_argument("--capabilities", help="Required capabilities, comma-separated")
    
    # List tasks command
    list_tasks_parser = subparsers.add_parser("list-tasks", help="List all tasks")
    
    # Task summary command
    task_summary_parser = subparsers.add_parser("task-summary", help="Show summary of all tasks")
    
    # List agents command
    list_agents_parser = subparsers.add_parser("list-agents", help="List all agents")
    
    # Create agent command
    create_agent_parser = subparsers.add_parser("create-agent", help="Create a new dynamic agent")
    create_agent_parser.add_argument("agent_type", choices=list(config.AGENT_TYPES.keys()),
                                   help="Type of agent to create")
    create_agent_parser.add_argument("--capabilities", help="Comma-separated list of capabilities")
    create_agent_parser.add_argument("--description", help="Custom description for the agent")
    create_agent_parser.add_argument("--start", action="store_true", 
                                   help="Start the agent immediately after creation")
    
    # Start agent command
    start_agent_parser = subparsers.add_parser("start-agent", help="Start a specific agent")
    start_agent_parser.add_argument("agent_id", help="ID of the agent to start")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    
    # Attach command
    attach_parser = subparsers.add_parser("attach", help="Attach to the TMUX session")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.command == "start":
        start_team(args.agents)
    
    elif args.command == "stop":
        shutdown_team()
    
    elif args.command == "task":
        # Combine the description words into a single string
        description = " ".join(args.description)
        create_task(description, args.priority, args.capabilities)
    
    elif args.command == "list-tasks":
        list_tasks()
    
    elif args.command == "task-summary":
        task_summary()
    
    elif args.command == "list-agents":
        list_agents()
    
    elif args.command == "create-agent":
        create_agent(args.agent_type, args.capabilities, args.description, args.start)
    
    elif args.command == "start-agent":
        start_agent(args.agent_id)
    
    elif args.command == "status":
        print_status()
    
    elif args.command == "attach":
        attach_to_session()
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()