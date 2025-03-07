#!/usr/bin/env python3
import os
import sys
import json
import time
import curses
import argparse
import logging
from datetime import datetime
from colorama import Fore, Style, init
import subprocess
import re

# Initialize colorama for terminal colors
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('agent_activity')

# Get the path to the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "claude_state.json")
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# ANSI colors for terminal output
COLORS = {
    'team_lead': Fore.CYAN,
    'agent1': Fore.GREEN,
    'agent2': Fore.YELLOW,
    'agent3': Fore.MAGENTA,
    'default': Fore.WHITE
}

# Terminal color mapping to curses colors
CURSES_COLORS = {
    'team_lead': curses.COLOR_CYAN,
    'agent1': curses.COLOR_GREEN,
    'agent2': curses.COLOR_YELLOW,
    'agent3': curses.COLOR_MAGENTA,
    'default': curses.COLOR_WHITE
}

def get_agent_color(agent_name):
    """Return ANSI color for agent name"""
    agent_name = agent_name.lower()
    if 'team' in agent_name or 'lead' in agent_name:
        return COLORS['team_lead']
    elif 'agent1' in agent_name or 'login' in agent_name:
        return COLORS['agent1']
    elif 'agent2' in agent_name or 'dashboard' in agent_name:
        return COLORS['agent2']
    elif 'agent3' in agent_name or 'api' in agent_name:
        return COLORS['agent3']
    return COLORS['default']

def format_timestamp(timestamp):
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError):
        return timestamp

def load_state():
    """Load state from file with error handling"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                logger.info(f"Using existing state file at {STATE_FILE}")
                return json.load(f)
        else:
            logger.error(f"State file not found: {STATE_FILE}")
            return {"reasoning_logs": [], "messages": [], "tasks": {}}
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from state file: {STATE_FILE}")
        return {"reasoning_logs": [], "messages": [], "tasks": {}}
    except Exception as e:
        logger.error(f"Error loading state file: {e}")
        return {"reasoning_logs": [], "messages": [], "tasks": {}}

def get_reasoning_logs(state, limit=10):
    """Get reasoning logs sorted by timestamp"""
    logs = state.get("reasoning_logs", [])
    
    # Handle different data formats
    valid_logs = []
    for log in logs:
        if isinstance(log, dict):
            valid_logs.append(log)
        elif isinstance(log, str):
            # Try to parse JSON string
            try:
                parsed = json.loads(log)
                if isinstance(parsed, dict):
                    valid_logs.append(parsed)
            except:
                # If we can't parse as JSON, create a simple log entry
                valid_logs.append({
                    "agent": "unknown",
                    "timestamp": datetime.now().isoformat(),
                    "task_id": "unknown",
                    "reasoning": log
                })
    
    # Sort logs by timestamp, with error handling
    try:
        sorted_logs = sorted(valid_logs, 
                             key=lambda x: x.get("timestamp", datetime.now().isoformat()), 
                             reverse=True)
    except Exception as e:
        logger.error(f"Error sorting logs: {e}")
        sorted_logs = valid_logs
    
    return sorted_logs[:limit]

def get_messages(state, limit=20):
    """Get messages sorted by timestamp"""
    messages = state.get("messages", [])
    
    # Filter out any malformed messages and handle different formats
    valid_messages = []
    for msg in messages:
        if isinstance(msg, dict) and "timestamp" in msg:
            valid_messages.append(msg)
        elif isinstance(msg, dict):
            # Add a timestamp if missing
            msg["timestamp"] = datetime.now().isoformat()
            valid_messages.append(msg)
        elif isinstance(msg, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(msg)
                if isinstance(parsed, dict):
                    if "timestamp" not in parsed:
                        parsed["timestamp"] = datetime.now().isoformat()
                    valid_messages.append(parsed)
            except:
                # Create a simple message entry
                valid_messages.append({
                    "sender": "unknown",
                    "receiver": "unknown",
                    "timestamp": datetime.now().isoformat(),
                    "content": msg
                })
    
    # Sort messages by timestamp with error handling
    try:
        sorted_messages = sorted(valid_messages, 
                                key=lambda x: x.get("timestamp", datetime.now().isoformat()), 
                                reverse=True)
    except Exception as e:
        logger.error(f"Error sorting messages: {e}")
        sorted_messages = valid_messages
    
    return sorted_messages[:limit]

def get_active_tasks(state):
    """Get active tasks for each agent"""
    tasks = state.get("tasks", {})
    active_tasks = {}
    
    for branch, branch_tasks in tasks.items():
        if not isinstance(branch_tasks, list):
            continue
            
        branch_name = branch
        if branch == "login":
            branch_name = "Agent1 (Login)"
        elif branch == "dashboard":
            branch_name = "Agent2 (Dashboard)"
        elif branch == "api":
            branch_name = "Agent3 (API)"
        elif branch == "main":
            branch_name = "Team Lead"
            
        active_tasks[branch_name] = []
        for task in branch_tasks:
            if not isinstance(task, dict):
                continue
                
            if task.get("status") != "completed":
                active_tasks[branch_name].append(task)
                
    return active_tasks

def display_reasoning_logs(logs):
    """Display reasoning logs to terminal"""
    if not logs:
        print(f"{Fore.YELLOW}No reasoning logs found.{Style.RESET_ALL}")
        return
        
    print(f"{Fore.BLUE}===== AGENT REASONING LOGS ====={Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'-' * 80}{Style.RESET_ALL}")
    
    for log in logs:
        try:
            agent = log.get("agent", "unknown")
            timestamp = format_timestamp(log.get("timestamp", ""))
            task_id = log.get("task_id", "unknown")
            reasoning = log.get("reasoning", "").strip()
            
            # Detect API errors and other issues
            has_error = False
            error_type = None
            
            if "API Error" in reasoning:
                has_error = True
                error_type = "API Error"
            elif "error" in reasoning.lower() and "internal" in reasoning.lower():
                has_error = True
                error_type = "Internal Error"
            elif "exception" in reasoning.lower():
                has_error = True
                error_type = "Exception"
                
            agent_color = get_agent_color(agent)
            print(f"{agent_color}{agent}{Style.RESET_ALL} @ {timestamp}")
            print(f"Task: {task_id}")
            
            # Highlight if the agent is analyzing or planning something
            if "analyzing" in reasoning.lower() or "analyze" in reasoning.lower():
                print(f"  {Fore.CYAN}[ANALYZING]{Style.RESET_ALL}")
            elif "planning" in reasoning.lower() or "plan" in reasoning.lower():
                print(f"  {Fore.GREEN}[PLANNING]{Style.RESET_ALL}")
            elif "implementing" in reasoning.lower() or "implement" in reasoning.lower():
                print(f"  {Fore.MAGENTA}[IMPLEMENTING]{Style.RESET_ALL}")
            elif "testing" in reasoning.lower() or "test" in reasoning.lower():
                print(f"  {Fore.YELLOW}[TESTING]{Style.RESET_ALL}")
                
            # If we have an error, highlight it
            if has_error:
                print(f"  {Fore.RED}[{error_type} DETECTED]{Style.RESET_ALL}")
            
            # Print reasoning with proper indentation
            reasoning_lines = reasoning.strip().split('\n')
            for line in reasoning_lines:
                line = line.strip()
                if not line:
                    continue
                    
                if has_error and (error_type.lower() in line.lower() or "error" in line.lower()):
                    print(f"  ⎿  {Fore.RED}{line}{Style.RESET_ALL}")
                else:
                    print(f"  ⎿  {line}")
            
            print(f"{Fore.BLUE}{'-' * 30}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error displaying log: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'-' * 30}{Style.RESET_ALL}")

def display_messages(messages):
    """Display messages to terminal"""
    if not messages:
        print(f"{Fore.YELLOW}No messages found.{Style.RESET_ALL}")
        return
        
    print(f"{Fore.BLUE}===== AGENT COMMUNICATIONS ====={Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'-' * 80}{Style.RESET_ALL}")
    
    for msg in messages:
        try:
            sender = msg.get("sender", "unknown")
            receiver = msg.get("receiver", "unknown")
            timestamp = format_timestamp(msg.get("timestamp", ""))
            content = msg.get("content", "").strip()
            
            sender_color = get_agent_color(sender)
            receiver_color = get_agent_color(receiver)
            
            print(f"{sender_color}{sender}{Style.RESET_ALL} → {receiver_color}{receiver}{Style.RESET_ALL} @ {timestamp}")
            
            # Print message content with proper indentation
            for line in content.split('\n'):
                print(f"  {line}")
            
            print(f"{Fore.BLUE}{'-' * 30}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error displaying message: {e}{Style.RESET_ALL}")
    
def display_active_tasks(tasks):
    """Display active tasks to terminal"""
    if not tasks:
        print(f"{Fore.YELLOW}No active tasks found.{Style.RESET_ALL}")
        return
        
    print(f"{Fore.BLUE}===== ACTIVE TASKS ====={Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'-' * 80}{Style.RESET_ALL}")
    
    for agent, agent_tasks in tasks.items():
        agent_color = get_agent_color(agent)
        print(f"{agent_color}{agent}{Style.RESET_ALL}: {len(agent_tasks)} active tasks")
        
        if not agent_tasks:
            print(f"  No active tasks")
            continue
            
        for i, task in enumerate(agent_tasks, 1):
            task_id = task.get("id", "unknown")
            description = task.get("description", "No description")
            status = task.get("status", "unknown")
            
            print(f"  {i}. [{status}] {description} (ID: {task_id})")
        
        print(f"{Fore.BLUE}{'-' * 30}{Style.RESET_ALL}")

def safe_addstr(window, y, x, string, attr=curses.A_NORMAL):
    """Safely add a string to a curses window, handling overflow"""
    height, width = window.getmaxyx()
    
    # Skip if we're trying to write outside the window vertically
    if y >= height:
        return
    
    # If the string is too long, truncate it
    max_len = width - x - 1
    if len(string) > max_len:
        string = string[:max_len]
    
    try:
        window.addstr(y, x, string, attr)
    except curses.error:
        # Catch any curses errors and ignore them
        pass

def interactive_mode(stdscr, args):
    """Interactive mode using curses"""
    # Initialize curses
    curses.start_color()
    curses.use_default_colors()
    curses.curs_set(0)  # Hide cursor
    stdscr.timeout(1000)  # Set getch() timeout to 1 second
    
    # Initialize color pairs
    curses.init_pair(1, curses.COLOR_CYAN, -1)     # Team Lead
    curses.init_pair(2, curses.COLOR_GREEN, -1)    # Agent 1
    curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Agent 2
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)  # Agent 3
    curses.init_pair(5, curses.COLOR_RED, -1)      # Error
    curses.init_pair(6, curses.COLOR_BLUE, -1)     # Headers
    curses.init_pair(7, curses.COLOR_WHITE, -1)    # Regular text
    
    # Create color attribute mapping
    COLOR_ATTRS = {
        'team_lead': curses.color_pair(1),
        'agent1': curses.color_pair(2),
        'agent2': curses.color_pair(3),
        'agent3': curses.color_pair(4),
        'error': curses.color_pair(5),
        'header': curses.color_pair(6),
        'default': curses.color_pair(7)
    }
    
    # Window dimensions
    height, width = stdscr.getmaxyx()
    
    # Initial view mode
    view_mode = args.mode
    if view_mode == "all":
        show_tasks = True
        show_messages = True
        show_reasoning = True
    elif view_mode == "tasks":
        show_tasks = True
        show_messages = False
        show_reasoning = False
    elif view_mode == "messages":
        show_tasks = False
        show_messages = True
        show_reasoning = False
    elif view_mode == "reasoning":
        show_tasks = False
        show_messages = False
        show_reasoning = True
    
    # Main loop
    refresh_interval = args.interval
    last_refresh = 0
    running = True
    
    while running:
        # Get current time
        current_time = time.time()
        
        # Check if it's time to refresh
        if current_time - last_refresh >= refresh_interval:
            # Load updated state
            state = load_state()
            last_refresh = current_time
            
            # Clear screen
            stdscr.clear()
            
            # Calculate window dimensions
            if show_tasks and show_messages and show_reasoning:
                # All views mode
                task_height = height // 4
                msg_height = height // 4
                reason_height = height - task_height - msg_height - 1
            elif show_tasks and show_messages:
                # Tasks and messages mode
                task_height = height // 2
                msg_height = height - task_height - 1
                reason_height = 0
            elif show_tasks and show_reasoning:
                # Tasks and reasoning mode
                task_height = height // 3
                msg_height = 0
                reason_height = height - task_height - 1
            elif show_messages and show_reasoning:
                # Messages and reasoning mode
                task_height = 0
                msg_height = height // 2
                reason_height = height - msg_height - 1
            elif show_tasks:
                # Tasks only mode
                task_height = height - 1
                msg_height = 0
                reason_height = 0
            elif show_messages:
                # Messages only mode
                task_height = 0
                msg_height = height - 1
                reason_height = 0
            elif show_reasoning:
                # Reasoning only mode
                task_height = 0
                msg_height = 0
                reason_height = height - 1
            
            # Current y position for rendering
            current_y = 0
            
            # Display mode info
            mode_info = f"Mode: "
            if show_tasks and show_messages and show_reasoning:
                mode_info += "All"
            elif show_tasks:
                mode_info += "Tasks"
            elif show_messages:
                mode_info += "Messages"
            elif show_reasoning:
                mode_info += "Reasoning"
            
            mode_info += " | Press: t=Tasks, m=Messages, r=Reasoning, a=All, q=Quit"
            safe_addstr(stdscr, current_y, 0, mode_info, COLOR_ATTRS['header'])
            current_y += 1
            
            # Display tasks if enabled
            if show_tasks and task_height > 0:
                active_tasks = get_active_tasks(state)
                
                # Display header
                safe_addstr(stdscr, current_y, 0, "===== ACTIVE TASKS =====", COLOR_ATTRS['header'])
                current_y += 1
                safe_addstr(stdscr, current_y, 0, "-" * (width - 1), COLOR_ATTRS['header'])
                current_y += 1
                
                # Display tasks for each agent
                tasks_displayed = 0
                for agent, agent_tasks in active_tasks.items():
                    # Check if we have space to display this agent's tasks
                    if current_y >= task_height:
                        break
                        
                    # Display agent name and task count
                    agent_color = 'default'
                    if 'team' in agent.lower() or 'lead' in agent.lower():
                        agent_color = 'team_lead'
                    elif 'agent1' in agent.lower() or 'login' in agent.lower():
                        agent_color = 'agent1'
                    elif 'agent2' in agent.lower() or 'dashboard' in agent.lower():
                        agent_color = 'agent2'
                    elif 'agent3' in agent.lower() or 'api' in agent.lower():
                        agent_color = 'agent3'
                        
                    safe_addstr(stdscr, current_y, 0, f"{agent}: {len(agent_tasks)} active tasks", COLOR_ATTRS[agent_color])
                    current_y += 1
                    
                    # Display each task
                    for i, task in enumerate(agent_tasks, 1):
                        # Check if we have space to display this task
                        if current_y >= task_height:
                            break
                            
                        task_id = task.get("id", "unknown")
                        description = task.get("description", "No description")
                        status = task.get("status", "unknown")
                        
                        # Truncate description if too long
                        if len(description) > width - 20:
                            description = description[:width - 23] + "..."
                        
                        safe_addstr(stdscr, current_y, 2, f"{i}. [{status}] {description} (ID: {task_id})")
                        current_y += 1
                        tasks_displayed += 1
                    
                    # Add separator between agents
                    if current_y < task_height:
                        safe_addstr(stdscr, current_y, 0, "-" * 30, COLOR_ATTRS['header'])
                        current_y += 1
                
                # If no tasks found
                if tasks_displayed == 0:
                    safe_addstr(stdscr, current_y, 2, "No active tasks found.")
                    current_y += 1
                
                # Add separator
                if current_y < height:
                    safe_addstr(stdscr, current_y, 0, "=" * (width - 1), COLOR_ATTRS['header'])
                    current_y += 1
            
            # Reset current_y for messages section if needed
            if show_tasks and show_messages:
                current_y = task_height
            
            # Display messages if enabled
            if show_messages and msg_height > 0:
                messages = get_messages(state, limit=msg_height - 2)
                
                # Display header
                safe_addstr(stdscr, current_y, 0, "===== AGENT COMMUNICATIONS =====", COLOR_ATTRS['header'])
                current_y += 1
                safe_addstr(stdscr, current_y, 0, "-" * (width - 1), COLOR_ATTRS['header'])
                current_y += 1
                
                # Display each message
                if not messages:
                    safe_addstr(stdscr, current_y, 2, "No messages found.")
                    current_y += 1
                else:
                    for msg in messages:
                        # Check if we have space to display this message
                        if current_y >= current_y + msg_height - 2:
                            break
                            
                        try:
                            sender = msg.get("sender", "unknown")
                            receiver = msg.get("receiver", "unknown")
                            timestamp = format_timestamp(msg.get("timestamp", ""))
                            content = msg.get("content", "").strip()
                            
                            # Determine color for sender and receiver
                            sender_color = 'default'
                            if 'team' in sender.lower() or 'lead' in sender.lower():
                                sender_color = 'team_lead'
                            elif 'agent1' in sender.lower() or 'login' in sender.lower():
                                sender_color = 'agent1'
                            elif 'agent2' in sender.lower() or 'dashboard' in sender.lower():
                                sender_color = 'agent2'
                            elif 'agent3' in sender.lower() or 'api' in sender.lower():
                                sender_color = 'agent3'
                                
                            receiver_color = 'default'
                            if 'team' in receiver.lower() or 'lead' in receiver.lower():
                                receiver_color = 'team_lead'
                            elif 'agent1' in receiver.lower() or 'login' in receiver.lower():
                                receiver_color = 'agent1'
                            elif 'agent2' in receiver.lower() or 'dashboard' in receiver.lower():
                                receiver_color = 'agent2'
                            elif 'agent3' in receiver.lower() or 'api' in receiver.lower():
                                receiver_color = 'agent3'
                            
                            # Display sender, receiver, and timestamp
                            safe_addstr(stdscr, current_y, 0, f"{sender}", COLOR_ATTRS[sender_color])
                            safe_addstr(stdscr, current_y, len(sender) + 1, "→")
                            safe_addstr(stdscr, current_y, len(sender) + 3, f"{receiver}", COLOR_ATTRS[receiver_color])
                            safe_addstr(stdscr, current_y, len(sender) + len(receiver) + 5, f"@ {timestamp}")
                            current_y += 1
                            
                            # Display message content with proper indentation
                            for line in content.split('\n'):
                                if current_y >= current_y + msg_height - 2:
                                    break
                                    
                                if len(line) > width - 4:
                                    line = line[:width - 7] + "..."
                                    
                                safe_addstr(stdscr, current_y, 2, line)
                                current_y += 1
                            
                            # Add separator between messages
                            if current_y < current_y + msg_height - 2:
                                safe_addstr(stdscr, current_y, 0, "-" * 30, COLOR_ATTRS['header'])
                                current_y += 1
                        except Exception as e:
                            safe_addstr(stdscr, current_y, 0, f"Error displaying message: {e}", COLOR_ATTRS['error'])
                            current_y += 1
                
                # Add separator
                if current_y < height:
                    safe_addstr(stdscr, current_y, 0, "=" * (width - 1), COLOR_ATTRS['header'])
                    current_y += 1
            
            # Reset current_y for reasoning section if needed
            if (show_tasks or show_messages) and show_reasoning:
                if show_tasks and show_messages:
                    current_y = task_height + msg_height
                elif show_tasks:
                    current_y = task_height
                elif show_messages:
                    current_y = msg_height
            
            # Display reasoning logs if enabled
            if show_reasoning and reason_height > 0:
                logs = get_reasoning_logs(state, limit=reason_height - 2)
                
                # Display header
                safe_addstr(stdscr, current_y, 0, "===== AGENT REASONING LOGS =====", COLOR_ATTRS['header'])
                current_y += 1
                safe_addstr(stdscr, current_y, 0, "-" * (width - 1), COLOR_ATTRS['header'])
                current_y += 1
                
                # Display each log
                if not logs:
                    safe_addstr(stdscr, current_y, 2, "No reasoning logs found.")
                    current_y += 1
                else:
                    for log in logs:
                        # Check if we have space to display this log
                        if current_y >= height - 1:
                            break
                            
                        try:
                            agent = log.get("agent", "unknown")
                            timestamp = format_timestamp(log.get("timestamp", ""))
                            task_id = log.get("task_id", "unknown")
                            reasoning = log.get("reasoning", "").strip()
                            
                            # Determine color for agent
                            agent_color = 'default'
                            if 'team' in agent.lower() or 'lead' in agent.lower():
                                agent_color = 'team_lead'
                            elif 'agent1' in agent.lower() or 'login' in agent.lower():
                                agent_color = 'agent1'
                            elif 'agent2' in agent.lower() or 'dashboard' in agent.lower():
                                agent_color = 'agent2'
                            elif 'agent3' in agent.lower() or 'api' in agent.lower():
                                agent_color = 'agent3'
                            
                            # Display agent and timestamp
                            safe_addstr(stdscr, current_y, 0, f"{agent}", COLOR_ATTRS[agent_color])
                            safe_addstr(stdscr, current_y, len(agent) + 1, f"@ {timestamp}")
                            current_y += 1
                            
                            # Display task ID
                            safe_addstr(stdscr, current_y, 0, f"Task: {task_id}")
                            current_y += 1
                            
                            # Check for API errors
                            has_api_error = "API Error" in reasoning
                            
                            # Display reasoning with proper indentation
                            for line in reasoning.split('\n'):
                                if current_y >= height - 1:
                                    break
                                    
                                if len(line) > width - 6:
                                    line = line[:width - 9] + "..."
                                
                                # Highlight API errors
                                if has_api_error and "API Error" in line:
                                    safe_addstr(stdscr, current_y, 2, "⎿  ", COLOR_ATTRS['default'])
                                    safe_addstr(stdscr, current_y, 6, line, COLOR_ATTRS['error'])
                                else:
                                    safe_addstr(stdscr, current_y, 2, f"⎿  {line}")
                                
                                current_y += 1
                            
                            # Add separator between logs
                            if current_y < height - 1:
                                safe_addstr(stdscr, current_y, 0, "-" * 30, COLOR_ATTRS['header'])
                                current_y += 1
                        except Exception as e:
                            safe_addstr(stdscr, current_y, 0, f"Error displaying reasoning log: {e}", COLOR_ATTRS['error'])
                            current_y += 1
        
        # Refresh the screen
        stdscr.refresh()
        
        # Check for user input
        try:
            c = stdscr.getch()
            if c == ord('q'):
                running = False
            elif c == ord('t'):
                show_tasks = True
                show_messages = False
                show_reasoning = False
            elif c == ord('m'):
                show_tasks = False
                show_messages = True
                show_reasoning = False
            elif c == ord('r'):
                show_tasks = False
                show_messages = False
                show_reasoning = True
            elif c == ord('a'):
                show_tasks = True
                show_messages = True
                show_reasoning = True
        except:
            # Handle any errors with user input
            pass
            
        # Small delay to prevent high CPU usage
        time.sleep(0.1)

def get_claude_logs(agent_name=None, limit=5):
    """Get Claude's logs from log files"""
    logs = []
    log_dir = os.path.join(SCRIPT_DIR, "logs")
    
    if not os.path.exists(log_dir):
        logger.error(f"Log directory not found: {log_dir}")
        return logs
        
    log_files = []
    try:
        # Get all log files
        for root, dirs, files in os.walk(log_dir):
            for file in files:
                if file.endswith(".log") and "claude" in file.lower():
                    log_files.append(os.path.join(root, file))
                    
        # Sort by modification time (newest first)
        log_files.sort(key=os.path.getmtime, reverse=True)
    except Exception as e:
        logger.error(f"Error finding log files: {e}")
        return logs
        
    # Filter by agent if specified
    if agent_name:
        log_files = [f for f in log_files if agent_name.lower() in f.lower()]
        
    # Get the most recent logs
    for log_file in log_files[:5]:  # Look at 5 most recent log files
        try:
            agent = "unknown"
            if "team_lead" in log_file.lower() or "teamlead" in log_file.lower():
                agent = "team_lead"
            elif "agent1" in log_file.lower() or "login" in log_file.lower():
                agent = "agent1"
            elif "agent2" in log_file.lower() or "dashboard" in log_file.lower():
                agent = "agent2"
            elif "agent3" in log_file.lower() or "api" in log_file.lower():
                agent = "agent3"
                
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Check for claude prompts and responses
                claude_sections = []
                current_section = None
                for line in content.split("\n"):
                    if "SENDING TO CLAUDE:" in line:
                        if current_section:
                            claude_sections.append(current_section)
                        current_section = {"type": "prompt", "content": [], "agent": agent}
                    elif "CLAUDE RESPONSE:" in line:
                        if current_section:
                            claude_sections.append(current_section)
                        current_section = {"type": "response", "content": [], "agent": agent}
                    elif current_section:
                        current_section["content"].append(line)
                
                if current_section:
                    claude_sections.append(current_section)
                
                # Add to logs
                for section in claude_sections[-limit:]:  # Only take most recent sections
                    section_content = "\n".join(section["content"])
                    
                    # Extract task ID if present
                    task_id = "unknown"
                    for line in section["content"]:
                        if "task_id" in line.lower():
                            parts = line.split(":")
                            if len(parts) > 1:
                                task_id = parts[1].strip()
                                break
                    
                    logs.append({
                        "agent": section["agent"],
                        "timestamp": datetime.fromtimestamp(os.path.getmtime(log_file)).isoformat(),
                        "task_id": task_id,
                        "type": section["type"],
                        "reasoning": section_content
                    })
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
    
    # Sort by timestamp (newest first)
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]

def display_claude_logs(logs):
    """Display Claude logs"""
    if not logs:
        print(f"{Fore.YELLOW}No Claude logs found.{Style.RESET_ALL}")
        return
        
    print(f"{Fore.BLUE}===== CLAUDE LOGS ====={Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'-' * 80}{Style.RESET_ALL}")
    
    for log in logs:
        try:
            agent = log.get("agent", "unknown")
            timestamp = format_timestamp(log.get("timestamp", ""))
            task_id = log.get("task_id", "unknown")
            log_type = log.get("type", "unknown")
            content = log.get("reasoning", "").strip()
            
            agent_color = get_agent_color(agent)
            type_color = Fore.GREEN if log_type == "response" else Fore.YELLOW
            
            print(f"{agent_color}{agent}{Style.RESET_ALL} @ {timestamp}")
            print(f"Task: {task_id} | {type_color}{log_type.upper()}{Style.RESET_ALL}")
            
            # Print shortened version with key points
            shortened = content
            if len(content) > 500:
                shortened = content[:250] + "...[content truncated]..." + content[-250:]
                
            # Print with proper indentation
            for line in shortened.split('\n'):
                line = line.strip()
                if not line:
                    continue
                print(f"  {line}")
            
            print(f"{Fore.BLUE}{'-' * 30}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error displaying log: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.BLUE}{'-' * 30}{Style.RESET_ALL}")

def get_agent_status():
    """Check which agents are running and their status"""
    try:
        # Find claude processes
        result = subprocess.run(
            "ps aux | grep 'claude\|claude_agent' | grep -v grep", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        processes = result.stdout.strip().split('\n')
        agents = {
            "team_lead": {"active": False, "pid": None, "command": None},
            "agent1": {"active": False, "pid": None, "command": None},
            "agent2": {"active": False, "pid": None, "command": None},
            "agent3": {"active": False, "pid": None, "command": None}
        }
        
        for process in processes:
            if not process.strip():
                continue
                
            parts = process.split()
            if len(parts) < 11:
                continue
                
            pid = parts[1]
            cmd = ' '.join(parts[10:])
            
            if "team_lead" in cmd or "main-repo" in cmd:
                agents["team_lead"]["active"] = True
                agents["team_lead"]["pid"] = pid
                agents["team_lead"]["command"] = cmd
            elif "agent1" in cmd or "login" in cmd:
                agents["agent1"]["active"] = True
                agents["agent1"]["pid"] = pid
                agents["agent1"]["command"] = cmd
            elif "agent2" in cmd or "dashboard" in cmd:
                agents["agent2"]["active"] = True
                agents["agent2"]["pid"] = pid
                agents["agent2"]["command"] = cmd
            elif "agent3" in cmd or "api" in cmd:
                agents["agent3"]["active"] = True
                agents["agent3"]["pid"] = pid
                agents["agent3"]["command"] = cmd
        
        return agents
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {}

def get_tmux_output():
    """Get the output from the tmux panes for each agent"""
    try:
        # Check if tmux session exists
        result = subprocess.run(
            "tmux list-sessions | grep claude-team",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            logger.warning("No tmux session 'claude-team' found")
            return {}
            
        # Get output from each pane
        panes = [
            {"name": "team_lead", "window": 1}, 
            {"name": "agent1", "window": 2}, 
            {"name": "agent2", "window": 3}, 
            {"name": "agent3", "window": 4}
        ]
        
        outputs = {}
        for pane in panes:
            try:
                # Capture the last 15 lines from the tmux pane
                cmd = f"tmux capture-pane -p -t claude-team:{pane['window']} -S -15"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    outputs[pane["name"]] = output
            except Exception as e:
                logger.error(f"Error getting tmux output for {pane['name']}: {e}")
        
        return outputs
    except Exception as e:
        logger.error(f"Error getting tmux output: {e}")
        return {}

def parse_agent_output(output):
    """Parse the agent output to extract relevant information"""
    if not output:
        return {"status": "unknown", "task": None, "content": None}
        
    # Try to extract status
    status = "unknown"
    task = None
    content = None
    
    # Extract current task
    task_match = re.search(r"Working on task[:\s]+([^\n]+)", output)
    if task_match:
        task = task_match.group(1).strip()
    
    # Check status
    if "Sleeping" in output:
        status = "sleeping"
    elif "Working on task" in output:
        status = "working"
    elif "Waiting for tasks" in output:
        status = "waiting"
    elif "API Error" in output:
        status = "error"
    elif "Executing command" in output:
        status = "executing"
        
    # Try to extract reasoning
    reasoning_lines = []
    in_reasoning = False
    
    for line in output.split('\n'):
        if "THINKING:" in line or "REASONING:" in line:
            in_reasoning = True
            reasoning_lines = []
        elif in_reasoning and line.strip():
            reasoning_lines.append(line.strip())
        elif in_reasoning and not line.strip() and reasoning_lines:
            in_reasoning = False
    
    content = '\n'.join(reasoning_lines) if reasoning_lines else None
    
    return {"status": status, "task": task, "content": content}

def display_agent_activity(agent_outputs):
    """Display the agent activity from tmux outputs"""
    if not agent_outputs:
        print(f"{Fore.YELLOW}No agent activity found. Make sure the tmux session 'claude-team' is running.{Style.RESET_ALL}")
        return
        
    print(f"{Fore.BLUE}===== AGENT ACTIVITY ====={Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'-' * 80}{Style.RESET_ALL}")
    
    for agent_name, output in agent_outputs.items():
        try:
            agent_info = parse_agent_output(output)
            status = agent_info["status"]
            task = agent_info["task"]
            content = agent_info["content"]
            
            agent_color = get_agent_color(agent_name)
            
            # Format agent name
            if agent_name == "team_lead":
                display_name = "Team Lead"
            elif agent_name == "agent1":
                display_name = "Agent 1 (Login)"
            elif agent_name == "agent2":
                display_name = "Agent 2 (Dashboard)"
            elif agent_name == "agent3":
                display_name = "Agent 3 (API)"
            else:
                display_name = agent_name
                
            # Format status with color
            status_color = Fore.WHITE
            if status == "sleeping":
                status_color = Fore.YELLOW
            elif status == "working":
                status_color = Fore.GREEN
            elif status == "waiting":
                status_color = Fore.BLUE
            elif status == "error":
                status_color = Fore.RED
            elif status == "executing":
                status_color = Fore.MAGENTA
                
            print(f"{agent_color}{display_name}{Style.RESET_ALL}: {status_color}{status.upper()}{Style.RESET_ALL}")
            
            if task:
                print(f"  Task: {task}")
                
            if content:
                print(f"  {Fore.CYAN}REASONING:{Style.RESET_ALL}")
                
                # Limit content length
                if len(content) > 500:
                    content = content[:250] + f"\n  {Fore.YELLOW}... (content truncated) ...{Style.RESET_ALL}\n  " + content[-250:]
                
                for line in content.split('\n'):
                    print(f"    {line}")
            
            # Show a snippet of the raw output for debugging
            print(f"  {Fore.GRAY}Latest Activity:{Style.RESET_ALL}")
            last_lines = output.split('\n')[-5:]  # Last 5 lines
            for line in last_lines:
                if line.strip():
                    print(f"    {line}")
            
            print(f"{Fore.BLUE}{'-' * 30}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error displaying activity for {agent_name}: {str(e)}{Style.RESET_ALL}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Agent Activity Viewer for Multi-Agent Claude System")
    parser.add_argument("--mode", choices=["all", "tasks", "messages", "reasoning", "claude", "activity"], default="activity",
                        help="Display mode (default: activity)")
    parser.add_argument("--interval", type=int, default=5,
                        help="Refresh interval in seconds (default: 5)")
    parser.add_argument("--watch", action="store_true", default=True,
                        help="Watch mode - updates continuously (default: True)")
    parser.add_argument("--focus-agent", type=str, default=None,
                        help="Focus on a specific agent (options: team_lead, agent1, agent2, agent3)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Number of logs/messages to display (default: 10)")
    parser.add_argument("--no-simple", dest="simple", action="store_false", default=True,
                        help="Don't use simple mode (use curses instead)")
    
    args = parser.parse_args()
    
    # For backward compatibility
    if args.focus_agent and not args.agent:
        args.agent = args.focus_agent
    
    # If watch mode is enabled, use simple or curses mode
    if args.watch or args.simple:
        simple_watch_mode(args)
    else:
        try:
            # Use curses for interactive mode
            curses.wrapper(lambda stdscr: interactive_mode(stdscr, args))
        except curses.error as e:
            print(f"{Fore.RED}Curses error: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Falling back to simple mode.{Style.RESET_ALL}")
            simple_watch_mode(args)
        except Exception as e:
            print(f"{Fore.RED}Error in interactive mode: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Falling back to simple mode.{Style.RESET_ALL}")
            simple_watch_mode(args)

def simple_watch_mode(args):
    """Simple watch mode without curses"""
    try:
        while True:
            try:
                # Clear the screen
                os.system('clear' if os.name != 'nt' else 'cls')
                
                # Print timestamp
                print(f"{Fore.BLUE}===== AGENT ACTIVITY VIEWER ====={Style.RESET_ALL}")
                print(f"{Fore.BLUE}Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
                print(f"{Fore.BLUE}Mode: {args.mode}" + (f" | Focus: {args.focus_agent}" if args.focus_agent else "") + f"{Style.RESET_ALL}")
                print(f"{Fore.BLUE}{'-' * 80}{Style.RESET_ALL}")
                
                # Check agent status
                agent_status = get_agent_status()
                if agent_status:
                    print(f"{Fore.BLUE}===== AGENT STATUS ====={Style.RESET_ALL}")
                    for agent, info in agent_status.items():
                        agent_color = get_agent_color(agent)
                        status_text = f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}" if info["active"] else f"{Fore.RED}INACTIVE{Style.RESET_ALL}"
                        
                        # Skip if we're focusing on a specific agent and this isn't it
                        if args.focus_agent and args.focus_agent.lower() not in agent.lower():
                            continue
                            
                        if agent == "team_lead":
                            display_name = "Team Lead"
                        elif agent == "agent1":
                            display_name = "Agent 1 (Login)"
                        elif agent == "agent2":
                            display_name = "Agent 2 (Dashboard)"
                        elif agent == "agent3":
                            display_name = "Agent 3 (API)"
                        else:
                            display_name = agent
                            
                        print(f"  {agent_color}{display_name}{Style.RESET_ALL}: {status_text}")
                        if info["active"] and info["pid"]:
                            print(f"    PID: {info['pid']}")
                    print()
                
                # Display based on mode
                if args.mode == "activity":
                    try:
                        # Get agent outputs from tmux
                        agent_outputs = get_tmux_output()
                        
                        # Filter by agent if specified
                        if args.focus_agent:
                            filtered_outputs = {}
                            for agent, output in agent_outputs.items():
                                if args.focus_agent.lower() in agent.lower():
                                    filtered_outputs[agent] = output
                            agent_outputs = filtered_outputs
                            
                        display_agent_activity(agent_outputs)
                    except Exception as e:
                        print(f"{Fore.RED}Error displaying agent activity: {e}{Style.RESET_ALL}")
                
                if args.mode == "all" or args.mode == "tasks":
                    try:
                        state = load_state()
                        active_tasks = get_active_tasks(state)
                        # Filter by agent if specified
                        if args.focus_agent:
                            filtered_tasks = {}
                            for agent, tasks in active_tasks.items():
                                if args.focus_agent.lower() in agent.lower():
                                    filtered_tasks[agent] = tasks
                            active_tasks = filtered_tasks
                            
                        display_active_tasks(active_tasks)
                        print()
                    except Exception as e:
                        print(f"{Fore.RED}Error displaying tasks: {e}{Style.RESET_ALL}")
                        print()
                    
                if args.mode == "all" or args.mode == "messages":
                    try:
                        state = load_state()
                        messages = get_messages(state, limit=args.limit)
                        # Filter by agent if specified
                        if args.focus_agent:
                            messages = [m for m in messages if 
                                       args.focus_agent.lower() in m.get("sender", "").lower() or 
                                       args.focus_agent.lower() in m.get("receiver", "").lower()]
                        display_messages(messages)
                        print()
                    except Exception as e:
                        print(f"{Fore.RED}Error displaying messages: {e}{Style.RESET_ALL}")
                        print()
                    
                if args.mode == "all" or args.mode == "reasoning":
                    try:
                        state = load_state()
                        logs = get_reasoning_logs(state, limit=args.limit)
                        # Filter by agent if specified
                        if args.focus_agent:
                            logs = [l for l in logs if args.focus_agent.lower() in l.get("agent", "").lower()]
                        display_reasoning_logs(logs)
                        print()
                    except Exception as e:
                        print(f"{Fore.RED}Error displaying reasoning logs: {e}{Style.RESET_ALL}")
                        print()
                
                # Print instructions
                print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
                print(f"  ./view_agent_activity.py                               {Fore.GRAY}# View all agent activity (default){Style.RESET_ALL}")
                print(f"  ./view_agent_activity.py --focus-agent team_lead       {Fore.GRAY}# Focus on Team Lead agent{Style.RESET_ALL}")
                print(f"  ./view_agent_activity.py --mode tasks                  {Fore.GRAY}# View only task information{Style.RESET_ALL}")
                print(f"  ./view_agent_activity.py --interval 3                  {Fore.GRAY}# Set refresh interval to 3 seconds{Style.RESET_ALL}")
                print(f"\n{Fore.YELLOW}Press Ctrl+C to exit{Style.RESET_ALL}")
                
                # Wait before refreshing
                time.sleep(args.interval)
            except Exception as e:
                print(f"{Fore.RED}Error in watch mode: {e}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Retrying in {args.interval} seconds...{Style.RESET_ALL}")
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n{Fore.GREEN}Exiting agent activity viewer{Style.RESET_ALL}")
        return

if __name__ == "__main__":
    main() 