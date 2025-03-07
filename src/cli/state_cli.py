#!/usr/bin/env python3
"""
State Management CLI for Multi-Agent Claude System

This module provides a CLI interface for interacting with the shared state system,
allowing agents to manage tasks, messages, branches, and reasoning logs.
"""

import sys
import os
import argparse
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core import config
from src.core.state_manager import state_manager

def main():
    """Command-line interface for the shared state system."""
    parser = argparse.ArgumentParser(description="Manage shared state for multi-agent Claude system")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add Task
    add_task_parser = subparsers.add_parser("add_task", help="Add a task")
    add_task_parser.add_argument("branch", help="Branch name")
    add_task_parser.add_argument("description", help="Task description")
    add_task_parser.add_argument("assigned_to", nargs="?", help="Agent to assign")
    add_task_parser.add_argument("--priority", choices=config.TASK_PRIORITY_LEVELS, 
                                default="medium", help="Task priority")
    add_task_parser.add_argument("--capabilities", help="Required capabilities (comma-separated)")
    
    # Create Subtask
    create_subtask_parser = subparsers.add_parser("create_subtask", help="Create a subtask")
    create_subtask_parser.add_argument("parent_id", help="Parent task ID")
    create_subtask_parser.add_argument("description", help="Subtask description")
    create_subtask_parser.add_argument("assigned_to", nargs="?", help="Agent to assign")
    create_subtask_parser.add_argument("--capabilities", help="Required capabilities (comma-separated)")
    
    # Update Task
    update_task_parser = subparsers.add_parser("update_task", help="Update task status")
    update_task_parser.add_argument("task_id", help="Task ID")
    update_task_parser.add_argument("status", choices=config.TASK_STATUS_TYPES, help="New status")
    update_task_parser.add_argument("branch", nargs="?", help="Branch name")
    update_task_parser.add_argument("--message", help="Status update message")
    
    # Get Tasks
    get_tasks_parser = subparsers.add_parser("get_tasks", help="Get tasks")
    get_tasks_parser.add_argument("branch", nargs="?", help="Branch to filter by")
    get_tasks_parser.add_argument("--status", choices=config.TASK_STATUS_TYPES, help="Status to filter by")
    get_tasks_parser.add_argument("--agent", help="Agent to filter by")
    get_tasks_parser.add_argument("--parent", help="Parent task ID to filter by")
    
    # Get a single task by ID
    get_task_parser = subparsers.add_parser("get_task", help="Get a single task by ID")
    get_task_parser.add_argument("task_id", help="Task ID to retrieve")
    
    # Register Agent
    register_agent_parser = subparsers.add_parser("register_agent", help="Register a new agent")
    register_agent_parser.add_argument("agent_id", help="Agent ID")
    register_agent_parser.add_argument("agent_type", help="Agent type (manager, frontend, backend, etc.)")
    register_agent_parser.add_argument("capabilities", help="Comma-separated list of capabilities")
    
    # Send Message
    send_message_parser = subparsers.add_parser("send_message", help="Send a message")
    send_message_parser.add_argument("from_agent", help="Sending agent")
    send_message_parser.add_argument("to_agent", help="Receiving agent")
    send_message_parser.add_argument("content", help="Message content")
    send_message_parser.add_argument("--channel", choices=list(config.COMMUNICATION_CHANNELS.keys()), 
                                   default="direct", help="Communication channel")
    send_message_parser.add_argument("--priority", choices=["low", "normal", "high"], 
                                   default="normal", help="Message priority")
    
    # Get Messages
    get_messages_parser = subparsers.add_parser("get_messages", help="Get messages")
    get_messages_parser.add_argument("agent", help="Agent name")
    get_messages_parser.add_argument("--unread", action="store_true", help="Only unread messages")
    get_messages_parser.add_argument("--channel", choices=list(config.COMMUNICATION_CHANNELS.keys()), 
                                   help="Filter by channel")
    get_messages_parser.add_argument("--priority", choices=["low", "normal", "high"], 
                                   help="Filter by priority")
    
    # Mark Message Read
    mark_read_parser = subparsers.add_parser("mark_read", help="Mark message as read")
    mark_read_parser.add_argument("message_id", help="Message ID")
    
    # Register Branch
    register_branch_parser = subparsers.add_parser("register_branch", help="Register a branch")
    register_branch_parser.add_argument("branch_name", help="Branch name")
    register_branch_parser.add_argument("description", help="Branch description")
    register_branch_parser.add_argument("owner", help="Branch owner")
    
    # Delete Task
    delete_task_parser = subparsers.add_parser("delete_task", help="Delete a specific task")
    delete_task_parser.add_argument("task_id", help="ID of the task to delete")
    delete_task_parser.add_argument("branch", nargs="?", help="Branch name (optional)")
    
    # Delete All Tasks
    delete_all_tasks_parser = subparsers.add_parser("delete_all_tasks", help="Delete all tasks")
    delete_all_tasks_parser.add_argument("branch", nargs="?", help="Branch to delete tasks from (optional)")
    
    # Create PR
    create_pr_parser = subparsers.add_parser("create_pr", help="Create a pull request")
    create_pr_parser.add_argument("pr_id", help="Pull request ID")
    create_pr_parser.add_argument("title", help="PR title")
    create_pr_parser.add_argument("description", help="PR description")
    create_pr_parser.add_argument("source_branch", help="Source branch")
    create_pr_parser.add_argument("target_branch", help="Target branch")
    create_pr_parser.add_argument("author", help="PR author")
    
    # Log Reasoning
    log_reasoning_parser = subparsers.add_parser("log_reasoning", help="Log agent reasoning")
    log_reasoning_parser.add_argument("agent", help="Agent name")
    log_reasoning_parser.add_argument("task_id", help="Task ID")
    log_reasoning_parser.add_argument("reasoning", help="Reasoning text")
    log_reasoning_parser.add_argument("--tags", help="Comma-separated tags")
    
    # List Agents
    list_agents_parser = subparsers.add_parser("list-agents", help="List registered agents")
    list_agents_parser.add_argument("--status", help="Filter by status (active, inactive, etc.)")
    list_agents_parser.add_argument("--type", help="Filter by agent type")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Execute the requested command
    if args.command == "add_task":
        capabilities = None
        if hasattr(args, 'capabilities') and args.capabilities:
            capabilities = [cap.strip() for cap in args.capabilities.split(',')]
            
        task_id = state_manager.add_task(
            args.branch, 
            args.description, 
            args.assigned_to, 
            args.priority,
            capabilities
        )
        print(f"Added task {task_id}")
    
    elif args.command == "create_subtask":
        capabilities = None
        if hasattr(args, 'capabilities') and args.capabilities:
            capabilities = [cap.strip() for cap in args.capabilities.split(',')]
            
        subtask_id = state_manager.create_subtask(
            args.parent_id,
            args.description,
            args.assigned_to,
            capabilities
        )
        
        if subtask_id:
            print(f"Created subtask {subtask_id}")
        else:
            print(f"Failed to create subtask - parent task {args.parent_id} not found")
            sys.exit(1)
    
    elif args.command == "update_task":
        success = state_manager.update_task_status(
            args.task_id, 
            args.status, 
            args.branch,
            args.message if hasattr(args, 'message') else None
        )
        if not success:
            print(f"Task update failed - task {args.task_id} not found")
            sys.exit(1)
    
    elif args.command == "get_tasks":
        tasks = state_manager.get_tasks(
            agent=args.agent if hasattr(args, 'agent') else None,
            branch=args.branch,
            status=args.status,
            parent_task_id=args.parent if hasattr(args, 'parent') else None
        )
        if tasks:
            for task in tasks:
                status_str = f"[{task['status']}]".ljust(10)
                print(f"{task['id']}|{task['description']}|{task['status']}|{task.get('assigned_to', '')}")
        else:
            print("No tasks found")
            
    elif args.command == "get_task":
        # Find a specific task by ID
        all_tasks = []
        for branch in state_manager.get_state_data().get("tasks", {}):
            branch_tasks = state_manager.get_tasks(branch=branch)
            all_tasks.extend(branch_tasks)
            
        for task in all_tasks:
            if task["id"] == args.task_id:
                # Print full task details in a structured format
                print(f"ID: {task['id']}")
                print(f"Description: {task.get('description', 'No description')}")
                print(f"Status: {task.get('status', 'unknown')}")
                print(f"Assigned To: {task.get('assigned_to', 'unassigned')}")
                print(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(task.get('created_at', 0)))}")
                
                # Include messages/history if available
                if "status_history" in task and task["status_history"]:
                    print("Messages:")
                    for msg in task["status_history"]:
                        print(f"  {msg.get('message', 'No message')}")
                
                # Include any subtasks
                if "subtasks" in task and task["subtasks"]:
                    print("Subtasks:")
                    for subtask_id in task["subtasks"]:
                        print(f"  {subtask_id}")
                
                break
        else:
            print(f"Task {args.task_id} not found")
    
    elif args.command == "register_agent":
        # Parse capabilities as a comma-separated list
        capabilities = [cap.strip() for cap in args.capabilities.split(",") if cap.strip()]
        success = state_manager.register_agent(args.agent_id, args.agent_type, capabilities)
        if not success:
            print(f"Agent registration failed - agent {args.agent_id} may already exist")
            sys.exit(1)
    
    elif args.command == "send_message":
        msg_id = state_manager.add_message(
            args.from_agent, 
            args.to_agent, 
            args.content,
            args.channel,
            args.priority
        )
        print(f"Sent message {msg_id}")
    
    elif args.command == "get_messages":
        messages = state_manager.get_messages(
            args.agent, 
            args.unread,
            args.channel if hasattr(args, 'channel') else None,
            args.priority if hasattr(args, 'priority') else None
        )
        if messages:
            for msg in messages:
                read_status = "UNREAD" if not msg.get("read") else "READ"
                # Check if we're using the old format or new format
                if 'from' in msg:
                    sender = msg['from']
                elif 'sender' in msg:
                    sender = msg['sender']
                else:
                    sender = "unknown"
                    
                print(f"{msg['id']} [{read_status}] From {sender}: {msg['content']}")
        else:
            print("No messages found")
    
    elif args.command == "mark_read":
        success = state_manager.mark_message_read(args.message_id)
        if not success:
            print(f"Message mark read failed - message {args.message_id} not found")
            sys.exit(1)
    
    elif args.command == "register_branch":
        success = state_manager.register_branch(args.branch_name, args.description, args.owner)
        if not success:
            print(f"Branch registration failed - branch {args.branch_name} may already exist")
            sys.exit(1)
    
    elif args.command == "delete_task":
        success = state_manager.delete_task(args.task_id, args.branch)
        if not success:
            print(f"Task deletion failed - task {args.task_id} not found in branch {args.branch}")
            sys.exit(1)
    
    elif args.command == "delete_all_tasks":
        success = state_manager.delete_all_tasks(args.branch)
        if not success:
            print(f"All tasks deletion failed - branch {args.branch} not found")
            sys.exit(1)
    
    elif args.command == "create_pr":
        success = state_manager.create_pull_request(
            args.pr_id, args.title, args.description,
            args.source_branch, args.target_branch, args.author
        )
        if not success:
            print(f"PR creation failed - PR {args.pr_id} may already exist")
            sys.exit(1)
    
    elif args.command == "log_reasoning":
        log_id = state_manager.log_reasoning(
            args.agent, 
            args.task_id, 
            args.reasoning,
            args.tags if hasattr(args, 'tags') else None
        )
        print(f"Logged reasoning {log_id}")
    
    elif args.command == "list-agents":
        agents = state_manager.get_agents(
            status=args.status if hasattr(args, 'status') else None,
            agent_type=args.type if hasattr(args, 'type') else None
        )
        
        if agents:
            print(f"Found {len(agents)} agents:")
            for agent in agents:
                print(f"Agent: {agent['id']}")
                print(f"  Type: {agent.get('type', 'Unknown')}")
                print(f"  Status: {agent.get('status', 'Unknown')}")
                print(f"  Capabilities: {', '.join(agent.get('capabilities', []))}")
                print()
        else:
            print("No agents found matching the criteria")
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()