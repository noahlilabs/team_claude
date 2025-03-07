#!/usr/bin/env python3
"""
Shared State Manager for Multi-Agent Claude System

This module provides a centralized state management system for coordinating
multiple Claude AI agents. It handles tasks, messages, branches, pull requests,
and reasoning logs with file-based persistence and locking mechanisms to prevent
race conditions in a multi-agent environment.
"""

import json
import os
import fcntl
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, cast
import uuid
from datetime import datetime
import sys

# Add parent directory to path to make imports work in restructured layout
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("state_manager")

# Type definitions
T = TypeVar('T')
TaskID = str
MessageID = str
BranchName = str
PRID = str
LogID = str
AgentID = str
JsonData = Dict[str, Any]

class SharedState:
    """
    Manages the shared state for the multi-agent Claude system.
    
    This class provides methods for managing tasks, messages, branches,
    pull requests, and reasoning logs with file locking to prevent
    race conditions between multiple agents.
    """
    
    def __init__(self, state_file: Union[str, Path] = None):
        """
        Initialize the shared state manager.
        
        Args:
            state_file: Path to the JSON state file (uses config.STATE_FILE if None)
        """
        self.state_file = Path(state_file or config.STATE_FILE)
        self.state_file.parent.mkdir(exist_ok=True)
        
        # Initialize state file if it doesn't exist
        if not self.state_file.exists():
            self._initialize_state_file()
            logger.info(f"Created new state file at {self.state_file}")
        else:
            logger.info(f"Using existing state file at {self.state_file}")
    
    def _initialize_state_file(self) -> None:
        """Initialize a new state file with empty collections."""
        initial_state = {
            "tasks": {},
            "branches": {},
            "messages": [],
            "pull_requests": {},
            "reasoning_logs": {},
            "agents": {}
        }
        
        with open(self.state_file, 'w') as f:
            json.dump(initial_state, f, indent=2)
    
    def _with_file_lock(self, callback: Callable[[JsonData], T], max_retries: int = 3, retry_delay: float = 0.5) -> T:
        """
        Execute a callback function with file locking to prevent race conditions.
        
        Args:
            callback: Function that takes the state data and returns a result
            max_retries: Maximum number of retries if locking fails
            retry_delay: Delay in seconds between retries
            
        Returns:
            The return value of the callback function
        
        Raises:
            IOError: If file operations fail
            JSONDecodeError: If the state file contains invalid JSON
        """
        retry_count = 0
        
        # Implement exponential backoff for retries
        def get_retry_delay(attempt):
            return min(60, retry_delay * (2 ** attempt))  # Cap at 60 seconds
            
        # Create backup before modifications
        backup_file = f"{self.state_file}.bak"
        try:
            import shutil
            shutil.copy2(self.state_file, backup_file)
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
            
        while True:
            try:
                with open(self.state_file, 'r+') as f:
                    try:
                        # Add timeout to prevent indefinite blocking
                        start_time = time.time()
                        while True:
                            try:
                                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)  # Non-blocking lock
                                break
                            except BlockingIOError:
                                # Check if we've waited too long (30 seconds)
                                if time.time() - start_time > 30:
                                    logger.warning("Lock wait timeout, forcing lock release")
                                    # Force release by continuing (may lead to data inconsistency but prevents deadlock)
                                    break
                                time.sleep(0.5)
                                
                        try:
                            # Attempt to load data with corruption detection
                            try:
                                data = json.load(f)
                            except json.JSONDecodeError:
                                # Try to restore from backup if main file is corrupted
                                logger.error("State file corrupted, attempting recovery from backup")
                                with open(backup_file, 'r') as bf:
                                    data = json.load(bf)
                                    
                            # Create a copy of data for transaction rollback if needed
                            import copy
                            data_backup = copy.deepcopy(data)
                            
                            try:
                                # Execute callback within transaction
                                result = callback(data)
                                
                                # Write changes
                                f.seek(0)
                                f.truncate()
                                json.dump(data, f, indent=2)
                                f.flush()  # Ensure data is written to disk
                                
                                return result
                            except Exception as e:
                                # Rollback the transaction on error
                                logger.error(f"Error during transaction, rolling back: {e}")
                                f.seek(0)
                                f.truncate()
                                json.dump(data_backup, f, indent=2)
                                raise
                                
                        except Exception as e:
                            logger.error(f"Error in file operation: {e}")
                            raise
                            
                    except BlockingIOError:
                        # Failed to acquire lock with normal retry logic
                        retry_count += 1
                        if retry_count >= max_retries:
                            logger.error(f"Failed to acquire lock after {max_retries} attempts")
                            raise IOError("Could not acquire file lock")
                        current_delay = get_retry_delay(retry_count)
                        logger.warning(f"Lock acquisition failed, retrying ({retry_count}/{max_retries}) in {current_delay}s...")
                        time.sleep(current_delay)
                        
            except IOError as e:
                logger.error(f"IO Error accessing state file: {e}")
                # Try to use backup if main file can't be accessed
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, 'r') as bf:
                            # Just try to read from backup to see if it's valid
                            backup_data = json.load(bf)
                            logger.warning("Main state file inaccessible, trying to use backup")
                            # If backup seems valid, copy it to main file
                            shutil.copy2(backup_file, self.state_file)
                            # Try again with the restored file
                            continue
                    except Exception as backup_error:
                        logger.error(f"Backup file also corrupted: {backup_error}")
                        
                raise
    
    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------
    
    def register_agent(self, agent_id: AgentID, agent_type: str, capabilities: List[str]) -> bool:
        """
        Register a new agent in the system with its capabilities.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (manager, frontend, backend, etc.)
            capabilities: List of agent capabilities
            
        Returns:
            True if the agent was registered, False if max agents reached
        """
        logger.info(f"Registering agent {agent_id} of type {agent_type}")
        
        def update(data: JsonData) -> bool:
            if "agents" not in data:
                data["agents"] = {}
            
            if len(data["agents"]) >= config.MAX_AGENTS:
                logger.warning(f"Maximum number of agents ({config.MAX_AGENTS}) reached")
                return False
                
            data["agents"][agent_id] = {
                "type": agent_type,
                "capabilities": capabilities,
                "status": "active",
                "last_active": time.time(),
                "created_at": time.time(),
                "tasks_completed": 0,
                "tasks_current": []
            }
            return True
        
        return self._with_file_lock(update)
    
    def update_agent_status(self, agent_id: AgentID, status: str = "active") -> bool:
        """
        Update an agent's status and last active timestamp.
        
        Args:
            agent_id: The agent identifier
            status: New status ("active", "inactive", "error", etc.)
            
        Returns:
            True if the agent was found and updated, False otherwise
        """
        logger.info(f"Updating agent {agent_id} status to {status}")
        
        def update(data: JsonData) -> bool:
            if "agents" not in data or agent_id not in data["agents"]:
                return False
                
            data["agents"][agent_id]["status"] = status
            data["agents"][agent_id]["last_active"] = time.time()
            return True
        
        return self._with_file_lock(update)
    
    def get_agents(self, status: Optional[str] = None, agent_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all agents, optionally filtered by status and type.
        
        Args:
            status: Optional status to filter by
            agent_type: Optional agent type to filter by
            
        Returns:
            List of agent dictionaries
        """
        logger.info(f"Getting agents (status={status}, type={agent_type})")
        
        def query(data: JsonData) -> List[Dict[str, Any]]:
            if "agents" not in data:
                return []
                
            result = []
            for agent_id, agent_info in data["agents"].items():
                if (status is None or agent_info.get("status") == status) and \
                   (agent_type is None or agent_info.get("type") == agent_type):
                    agent_copy = agent_info.copy()
                    agent_copy["id"] = agent_id
                    result.append(agent_copy)
            
            return result
        
        return self._with_file_lock(query)
    
    def find_best_agent_for_task(self, required_capabilities: List[str]) -> Optional[str]:
        """
        Find the most suitable agent based on capabilities and current workload.
        
        Args:
            required_capabilities: List of capabilities needed for the task
            
        Returns:
            Agent ID of the best agent, or None if no suitable agent found
        """
        logger.info(f"Finding best agent for capabilities: {required_capabilities}")
        
        def query(data: JsonData) -> Optional[str]:
            if "agents" not in data:
                return None
                
            best_agent = None
            best_score = -1
            
            for agent_id, agent_info in data["agents"].items():
                if agent_info.get("status") != "active":
                    continue
                    
                # Calculate capability match score
                agent_capabilities = set(agent_info.get("capabilities", []))
                required_set = set(required_capabilities)
                
                if not required_set:  # If no specific requirements, any agent works
                    match_score = 1
                else:
                    # Calculate how many required capabilities the agent has
                    matches = len(agent_capabilities.intersection(required_set))
                    match_score = matches / len(required_set) if required_set else 0
                
                # Calculate workload score (inverse of current tasks)
                current_tasks = len(agent_info.get("tasks_current", []))
                workload_score = 1 / (current_tasks + 1)  # +1 to avoid division by zero
                
                # Combined score (70% capability match, 30% workload)
                total_score = (match_score * 0.7) + (workload_score * 0.3)
                
                if total_score > best_score:
                    best_score = total_score
                    best_agent = agent_id
                    
            return best_agent
        
        return self._with_file_lock(query)
    
    # -------------------------------------------------------------------------
    # Task Management
    # -------------------------------------------------------------------------
    
    def add_task(self, branch: BranchName, task_description: str, 
                assigned_to: Optional[str] = None, 
                priority: str = "medium",
                required_capabilities: Optional[List[str]] = None) -> TaskID:
        """
        Add a new task for a specific branch.
        
        Args:
            branch: The branch name the task is associated with
            task_description: Description of the task
            assigned_to: Name of the agent assigned to the task
            priority: Priority level ("low", "medium", "high", "critical")
            required_capabilities: Optional list of capabilities required for the task
            
        Returns:
            The ID of the newly created task
        """
        logger.info(f"Adding task to branch '{branch}': {task_description}")
        
        def update(data: JsonData) -> TaskID:
            if "tasks" not in data:
                data["tasks"] = {}
                
            if branch not in data["tasks"]:
                data["tasks"][branch] = []
            
            task_id = f"task_{int(time.time())}_{len(data['tasks'][branch])}"
            task = {
                "id": task_id,
                "description": task_description,
                "assigned_to": assigned_to,
                "status": "pending",
                "priority": priority,
                "created_at": time.time(),
                "updated_at": time.time(),
                "required_capabilities": required_capabilities or []
            }
            data["tasks"][branch].append(task)
            
            # If assigned to an agent, update the agent's current tasks
            if assigned_to and "agents" in data and assigned_to in data["agents"]:
                if "tasks_current" not in data["agents"][assigned_to]:
                    data["agents"][assigned_to]["tasks_current"] = []
                data["agents"][assigned_to]["tasks_current"].append(task_id)
            
            return task_id
        
        return self._with_file_lock(update)
    
    def create_subtask(self, parent_task_id: TaskID, description: str, 
                      assigned_to: Optional[str] = None,
                      required_capabilities: Optional[List[str]] = None) -> Optional[TaskID]:
        """
        Create a subtask linked to a parent task.
        
        Args:
            parent_task_id: ID of the parent task
            description: Description of the subtask
            assigned_to: Optional agent to assign the subtask to
            required_capabilities: Optional list of capabilities needed
            
        Returns:
            The ID of the created subtask, or None if parent not found
        """
        logger.info(f"Creating subtask for {parent_task_id}: {description}")
        
        def update(data: JsonData) -> Optional[TaskID]:
            # Find the parent task to get its branch
            parent_task = None
            parent_branch = None
            
            for branch, tasks in data["tasks"].items():
                for task in tasks:
                    if task["id"] == parent_task_id:
                        parent_task = task
                        parent_branch = branch
                        break
                if parent_task:
                    break
                    
            if not parent_task:
                logger.error(f"Parent task {parent_task_id} not found")
                return None
                
            # Create the subtask
            subtask_id = f"subtask_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            subtask = {
                "id": subtask_id,
                "parent_id": parent_task_id,
                "description": description,
                "assigned_to": assigned_to,
                "required_capabilities": required_capabilities or [],
                "status": "pending",
                "created_at": time.time(),
                "updated_at": time.time()
            }
            
            # Add to the same branch as parent
            data["tasks"][parent_branch].append(subtask)
            
            # Update parent task to track subtasks
            if "subtasks" not in parent_task:
                parent_task["subtasks"] = []
            parent_task["subtasks"].append(subtask_id)
            
            # If assigned to an agent, update the agent's current tasks
            if assigned_to and "agents" in data and assigned_to in data["agents"]:
                if "tasks_current" not in data["agents"][assigned_to]:
                    data["agents"][assigned_to]["tasks_current"] = []
                data["agents"][assigned_to]["tasks_current"].append(subtask_id)
            
            return subtask_id
        
        return self._with_file_lock(update)
    
    def delete_task(self, task_id: TaskID, branch: Optional[BranchName] = None) -> bool:
        """
        Delete a task from the system.
        
        Args:
            task_id: The ID of the task to delete
            branch: Optional branch name to limit the search. If None, will
                  search all branches.
            
        Returns:
            True if the task was deleted, False otherwise
        """
        logger.info(f"Deleting task {task_id}" + (f" from branch {branch}" if branch else " from all branches"))
        
        def delete_task_data(data):
            deleted = False
            
            # If branch is specified, only look in that branch
            if branch:
                if branch in data["tasks"]:
                    # Filter out the task with the matching ID
                    old_len = len(data["tasks"][branch])
                    data["tasks"][branch] = [
                        task for task in data["tasks"][branch] 
                        if task.get("id") != task_id
                    ]
                    deleted = len(data["tasks"][branch]) < old_len
            else:
                # Search all branches
                for br in data["tasks"]:
                    old_len = len(data["tasks"][br])
                    data["tasks"][br] = [
                        task for task in data["tasks"][br] 
                        if task.get("id") != task_id
                    ]
                    if len(data["tasks"][br]) < old_len:
                        deleted = True
                        
            # Also remove any subtasks that have this task as parent
            for br in data["tasks"]:
                data["tasks"][br] = [
                    task for task in data["tasks"][br] 
                    if task.get("parent_id") != task_id
                ]
            
            return deleted
        
        return self._with_file_lock(delete_task_data)

    def delete_all_tasks(self, branch: Optional[BranchName] = None) -> bool:
        """
        Delete all tasks from the system or from a specific branch.
        
        Args:
            branch: Optional branch name to limit deletion. If None, will
                  delete from all branches.
            
        Returns:
            True if any tasks were deleted, False otherwise
        """
        logger.info(f"Deleting all tasks" + (f" from branch {branch}" if branch else " from all branches"))
        
        def delete_all_task_data(data):
            deleted = False
            
            # If branch is specified, only clear that branch
            if branch:
                if branch in data["tasks"] and data["tasks"][branch]:
                    data["tasks"][branch] = []
                    deleted = True
            else:
                # Clear all branches
                for br in list(data["tasks"].keys()):
                    if data["tasks"][br]:
                        data["tasks"][br] = []
                        deleted = True
            
            return deleted
        
        return self._with_file_lock(delete_all_task_data)

    def update_task_status(self, task_id: TaskID, new_status: str, 
                         branch: Optional[BranchName] = None,
                         message: Optional[str] = None) -> bool:
        """
        Update the status of a task.
        
        Args:
            task_id: The ID of the task to update
            new_status: The new status to set
            branch: Optional branch name to limit the search
            message: Optional status update message
            
        Returns:
            True if the task was found and updated, False otherwise
        """
        logger.info(f"Updating task {task_id} to status '{new_status}'")
        
        def update(data: JsonData) -> bool:
            # If branch is provided, look only there
            if branch and branch in data["tasks"]:
                branches_to_check = [branch]
            else:
                branches_to_check = list(data["tasks"].keys())
            
            task_found = False
            for b in branches_to_check:
                for task in data["tasks"][b]:
                    if task["id"] == task_id:
                        task["status"] = new_status
                        task["updated_at"] = time.time()
                        
                        if message:
                            if "status_history" not in task:
                                task["status_history"] = []
                            task["status_history"].append({
                                "status": new_status,
                                "message": message,
                                "timestamp": time.time()
                            })
                        
                        # If task is completed and assigned to an agent, update agent stats
                        if new_status == "completed" and task.get("assigned_to"):
                            agent_id = task["assigned_to"]
                            if "agents" in data and agent_id in data["agents"]:
                                # Increment completed tasks counter
                                data["agents"][agent_id]["tasks_completed"] = \
                                    data["agents"][agent_id].get("tasks_completed", 0) + 1
                                
                                # Remove from current tasks
                                if "tasks_current" in data["agents"][agent_id]:
                                    if task_id in data["agents"][agent_id]["tasks_current"]:
                                        data["agents"][agent_id]["tasks_current"].remove(task_id)
                        
                        task_found = True
                        break
                if task_found:
                    break
            
            if not task_found:
                logger.warning(f"Task {task_id} not found")
                return False
            
            return True
        
        return self._with_file_lock(update)
    
    def get_tasks(self, agent: Optional[str] = None, 
                branch: Optional[BranchName] = None, 
                status: Optional[str] = None,
                parent_task_id: Optional[TaskID] = None) -> List[Dict[str, Any]]:
        """
        Get tasks, with flexible filtering options.
        
        Args:
            agent: Optional agent name to filter by assigned agent
            branch: Optional branch name to filter tasks
            status: Optional status to filter tasks
            parent_task_id: Optional parent task ID to filter subtasks
            
        Returns:
            List of task dictionaries
        """
        filter_desc = []
        if agent:
            filter_desc.append(f"agent='{agent}'")
        if branch:
            filter_desc.append(f"branch='{branch}'")
        if status:
            filter_desc.append(f"status='{status}'")
        if parent_task_id:
            filter_desc.append(f"parent_task_id='{parent_task_id}'")
        
        logger.info(f"Getting tasks" + 
                   (f" with filters: {', '.join(filter_desc)}" if filter_desc else ""))
        
        def query(data: JsonData) -> List[Dict[str, Any]]:
            result = []
            
            if "tasks" not in data:
                return []
                
            if branch:
                branches = [branch] if branch in data["tasks"] else []
            else:
                branches = list(data["tasks"].keys())
            
            for b in branches:
                for task in data["tasks"][b]:
                    # Apply filters
                    if (status is None or task["status"] == status) and \
                       (agent is None or task.get("assigned_to") == agent) and \
                       (parent_task_id is None or task.get("parent_id") == parent_task_id):
                        task_copy = task.copy()
                        task_copy["branch"] = b
                        result.append(task_copy)
            
            return result
        
        return self._with_file_lock(query)
    
    # -------------------------------------------------------------------------
    # Message Management
    # -------------------------------------------------------------------------
    
    def add_message(self, from_agent: str, to_agent: str, content: str, 
                  channel: str = "direct", priority: str = "normal") -> MessageID:
        """
        Add a message between agents with channel and priority support.
        
        Args:
            from_agent: Name of the sending agent
            to_agent: Name of the receiving agent
            content: Message content
            channel: Communication channel ("direct", "broadcast", "group")
            priority: Message priority ("low", "normal", "high")
            
        Returns:
            ID of the newly created message
        """
        logger.info(f"Adding message from {from_agent} to {to_agent} via {channel}")
        
        def update(data: JsonData) -> MessageID:
            # Create a unique message ID
            msg_id = f"msg_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            
            # Create the message
            message = {
                "id": msg_id,
                "sender": from_agent,
                "receiver": to_agent,
                "content": content,
                "channel": channel,
                "priority": priority,
                "timestamp": datetime.now().isoformat(),
                "read": False
            }
            
            # Initialize messages as a list if it doesn't exist or isn't a list
            if "messages" not in data or not isinstance(data["messages"], list):
                data["messages"] = []
                
            # Add the message to the list
            data["messages"].append(message)
            return msg_id
        
        return self._with_file_lock(update)
    
    def broadcast_message(self, from_agent: str, content: str, 
                        priority: str = "normal") -> List[MessageID]:
        """
        Broadcast a message to all active agents.
        
        Args:
            from_agent: Name of the sending agent
            content: Message content
            priority: Message priority ("low", "normal", "high")
            
        Returns:
            List of created message IDs
        """
        logger.info(f"Broadcasting message from {from_agent}")
        
        def update(data: JsonData) -> List[MessageID]:
            message_ids = []
            
            # Get all active agents except the sender
            agents = []
            if "agents" in data:
                for agent_id, agent_info in data["agents"].items():
                    if agent_id != from_agent and agent_info.get("status") == "active":
                        agents.append(agent_id)
            
            # If no agents in state yet, fall back to config
            if not agents:
                for agent_config in config.AGENTS.values():
                    if agent_config["name"] != from_agent:
                        agents.append(agent_config["name"])
            
            # Send a message to each agent
            timestamp = datetime.now().isoformat()
            if "messages" not in data or not isinstance(data["messages"], list):
                data["messages"] = []
                
            for agent in agents:
                msg_id = f"msg_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                
                message = {
                    "id": msg_id,
                    "sender": from_agent,
                    "receiver": agent,
                    "content": content,
                    "channel": "broadcast",
                    "priority": priority,
                    "timestamp": timestamp,
                    "read": False
                }
                
                data["messages"].append(message)
                message_ids.append(msg_id)
            
            return message_ids
        
        return self._with_file_lock(update)
    
    def get_messages(self, agent: Optional[str] = None, 
                   unread_only: bool = False, 
                   channel: Optional[str] = None,
                   priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get messages with enhanced filtering options.
        
        Args:
            agent: The agent to get messages for
            unread_only: Whether to only get unread messages
            channel: Optional channel to filter by
            priority: Optional priority to filter by
            
        Returns:
            List of messages
        """
        logger.info(f"Getting messages for agent: {agent}, unread_only: {unread_only}")
        
        def query(data: JsonData) -> List[Dict[str, Any]]:
            messages = []
            
            # Check if messages is stored as a list or a dictionary
            if "messages" not in data:
                return []
                
            if isinstance(data["messages"], list):
                # Handle list format
                for msg in data["messages"]:
                    if (agent is None or msg.get("receiver", msg.get("to", "")) == agent) and \
                       (not unread_only or not msg.get("read", False)) and \
                       (channel is None or msg.get("channel") == channel) and \
                       (priority is None or msg.get("priority") == priority):
                            messages.append(msg.copy())
            else:
                # Handle dictionary format (legacy)
                for msg_id, msg in data["messages"].items():
                    if (agent is None or msg.get("to", "") == agent) and \
                       (not unread_only or not msg.get("read", False)) and \
                       (channel is None or msg.get("channel") == channel) and \
                       (priority is None or msg.get("priority") == priority):
                        msg_copy = msg.copy()
                        msg_copy["id"] = msg_id  # Include the ID in the copy
                        messages.append(msg_copy)
                            
            return sorted(messages, key=lambda m: m.get("timestamp", 0), reverse=True)
        
        return self._with_file_lock(query)
    
    def mark_message_read(self, message_id: MessageID) -> bool:
        """
        Mark a message as read.
        
        Args:
            message_id: ID of the message to mark as read
            
        Returns:
            True if the message was found and marked as read, False otherwise
        """
        logger.info(f"Marking message {message_id} as read")
        
        def update(data: JsonData) -> bool:
            # Check if messages is stored as a list
            if isinstance(data["messages"], list):
                for msg in data["messages"]:
                    if msg.get("id") == message_id:
                            msg["read"] = True
                            return True
                return False
            
            # Legacy dictionary format
            if message_id in data["messages"]:
                data["messages"][message_id]["read"] = True
                return True
            return False
        
        return self._with_file_lock(update)
    
    # -------------------------------------------------------------------------
    # Branch Management
    # -------------------------------------------------------------------------
    
    def register_branch(self, branch_name: BranchName, description: str, owner: str) -> bool:
        """
        Register a new branch in the system.
        
        Args:
            branch_name: Name of the branch
            description: Description of the branch's purpose
            owner: Name of the agent owning the branch
            
        Returns:
            True if the branch was registered, False if it already exists
        """
        logger.info(f"Registering branch '{branch_name}' owned by {owner}")
        
        def update(data: JsonData) -> bool:
            if "branches" not in data:
                data["branches"] = {}
                
            if branch_name not in data["branches"]:
                data["branches"][branch_name] = {
                    "description": description,
                    "owner": owner,
                    "created_at": time.time(),
                    "status": "active"
                }
                return True
            return False
        
        return self._with_file_lock(update)
    
    # -------------------------------------------------------------------------
    # Pull Request Management
    # -------------------------------------------------------------------------
    
    def create_pull_request(self, pr_id: PRID, title: str, description: str, 
                          source_branch: BranchName, target_branch: BranchName, 
                          author: str) -> bool:
        """
        Create a new pull request.
        
        Args:
            pr_id: ID for the pull request
            title: Title of the pull request
            description: Description of the changes
            source_branch: Branch containing the changes
            target_branch: Branch to merge changes into
            author: Name of the agent creating the PR
            
        Returns:
            True if the PR was created, False if it already exists
        """
        logger.info(f"Creating PR '{title}' from {source_branch} to {target_branch}")
        
        def update(data: JsonData) -> bool:
            if "pull_requests" not in data:
                data["pull_requests"] = {}
                
            if pr_id in data["pull_requests"]:
                logger.warning(f"PR {pr_id} already exists")
                return False
            
            data["pull_requests"][pr_id] = {
                "title": title,
                "description": description,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "author": author,
                "status": "open",
                "created_at": time.time(),
                "updated_at": time.time(),
                "comments": [],
                "approvals": []
            }
            return True
        
        return self._with_file_lock(update)
    
    def update_pull_request(self, pr_id: PRID, status: Optional[str] = None, 
                          comment: Optional[Dict[str, str]] = None, 
                          approval: Optional[Dict[str, str]] = None) -> bool:
        """
        Update a pull request with status change, comment, or approval.
        
        Args:
            pr_id: ID of the pull request to update
            status: Optional new status
            comment: Optional comment dictionary with 'author' and 'content' keys
            approval: Optional approval dictionary with 'author' key
            
        Returns:
            True if the PR was found and updated, False otherwise
        """
        updates = []
        if status:
            updates.append(f"status='{status}'")
        if comment:
            updates.append(f"comment from {comment['author']}")
        if approval:
            updates.append(f"approval from {approval['author']}")
            
        logger.info(f"Updating PR {pr_id} with: {', '.join(updates)}")
        
        def update(data: JsonData) -> bool:
            if "pull_requests" not in data or pr_id not in data["pull_requests"]:
                logger.warning(f"PR {pr_id} not found")
                return False
            
            pr = data["pull_requests"][pr_id]
            pr["updated_at"] = time.time()
            
            if status:
                pr["status"] = status
            
            if comment:
                pr["comments"].append({
                    "author": comment["author"],
                    "content": comment["content"],
                    "timestamp": time.time()
                })
            
            if approval:
                if approval["author"] not in [a["author"] for a in pr["approvals"]]:
                    pr["approvals"].append({
                        "author": approval["author"],
                        "timestamp": time.time()
                    })
            
            return True
        
        return self._with_file_lock(update)
    
    def get_pull_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pull requests, optionally filtered by status.
        
        Args:
            status: Optional status to filter by
            
        Returns:
            List of pull request dictionaries
        """
        logger.info(f"Getting pull requests" + 
                   (f" with status '{status}'" if status else ""))
        
        def query(data: JsonData) -> List[Dict[str, Any]]:
            result = []
            
            if "pull_requests" not in data:
                return []
                
            for pr_id, pr in data["pull_requests"].items():
                if status is None or pr["status"] == status:
                    pr_copy = pr.copy()
                    pr_copy["id"] = pr_id
                    result.append(pr_copy)
            return result
        
        return self._with_file_lock(query)

    # -------------------------------------------------------------------------
    # Reasoning Log Management
    # -------------------------------------------------------------------------
    
    def log_reasoning(self, agent: str, task_id: TaskID, reasoning: str, 
                    tags: Optional[str] = None) -> LogID:
        """
        Log an agent's reasoning for a specific task with optional tags.
        
        Args:
            agent: Name of the agent
            task_id: ID of the task
            reasoning: The reasoning text
            tags: Optional comma-separated tags for categorization
            
        Returns:
            ID of the new log entry
        """
        logger.info(f"Logging reasoning from {agent} for task {task_id}")
        
        def update(data: JsonData) -> LogID:
            # Initialize reasoning_logs if it doesn't exist (for backward compatibility)
            if "reasoning_logs" not in data:
                data["reasoning_logs"] = {}
                
            log_id = f"log_{int(time.time())}_{agent}"
            log_entry = {
                "id": log_id,
                "agent": agent,
                "task_id": task_id,
                "reasoning": reasoning,
                "tags": tags.split(",") if tags else [],
                "timestamp": time.time()
            }
            
            data["reasoning_logs"][log_id] = log_entry
            return log_id
        
        return self._with_file_lock(update)
    
    def get_reasoning_logs(self, agent: Optional[str] = None, 
                         task_id: Optional[TaskID] = None,
                         tags: Optional[List[str]] = None, 
                         limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get reasoning logs with enhanced filtering.
        
        Args:
            agent: Optional agent name to filter by
            task_id: Optional task ID to filter by
            tags: Optional list of tags to filter by
            limit: Maximum number of logs to return
            
        Returns:
            List of reasoning log dictionaries
        """
        filter_desc = []
        if agent:
            filter_desc.append(f"agent='{agent}'")
        if task_id:
            filter_desc.append(f"task_id='{task_id}'")
        if tags:
            filter_desc.append(f"tags='{','.join(tags)}'")
            
        logger.info(f"Getting reasoning logs" + 
                   (f" with filters: {', '.join(filter_desc)}" if filter_desc else "") +
                   f" (limit={limit})")
        
        def query(data: JsonData) -> List[Dict[str, Any]]:
            # Handle if reasoning_logs doesn't exist yet (backward compatibility)
            if "reasoning_logs" not in data:
                return []
                
            logs = []
            for log in data["reasoning_logs"].values():
                # Check if the log matches all filters
                if (agent is None or log["agent"] == agent) and \
                   (task_id is None or log["task_id"] == task_id) and \
                   (tags is None or any(tag in log.get("tags", []) for tag in tags)):
                    logs.append(log.copy())
            
            # Sort by timestamp (newest first) and apply limit
            logs.sort(key=lambda x: x["timestamp"], reverse=True)
            return logs[:limit]
        
        return self._with_file_lock(query)


    # Add a method to get the raw state data (for debugging and direct access)
    def get_state_data(self) -> Dict[str, Any]:
        """
        Get a copy of the current state data.
        
        Returns:
            A copy of the current state data
        """
        def query(data: JsonData) -> Dict[str, Any]:
            return data.copy()
            
        return self._with_file_lock(query)

# Create a global instance
state_manager = SharedState()


# -------------------------------------------------------------------------
# CLI Interface
# -------------------------------------------------------------------------

def main():
    """Command-line interface for the shared state system."""
    parser = argparse.ArgumentParser(description="Manage shared state for multi-agent Claude system")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Get or set the state file path
    state_file = os.environ.get("CLAUDE_STATE_FILE", config.STATE_FILE)
    
    # Add Task
    add_task_parser = subparsers.add_parser("add_task", help="Add a task")
    add_task_parser.add_argument("branch", help="Branch name")
    add_task_parser.add_argument("description", help="Task description")
    add_task_parser.add_argument("assigned_to", nargs="?", help="Agent to assign")
    add_task_parser.add_argument("--priority", choices=config.TASK_PRIORITY_LEVELS, 
                                default="medium", help="Task priority")
    add_task_parser.add_argument("--capabilities", help="Required capabilities (comma-separated)")
    
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
    
    # Create PR
    create_pr_parser = subparsers.add_parser("create_pr", help="Create a pull request")
    create_pr_parser.add_argument("pr_id", help="Pull request ID")
    create_pr_parser.add_argument("title", help="PR title")
    create_pr_parser.add_argument("description", help="PR description")
    create_pr_parser.add_argument("source_branch", help="Source branch")
    create_pr_parser.add_argument("target_branch", help="Target branch")
    create_pr_parser.add_argument("author", help="PR author")
    
    # Update PR
    update_pr_parser = subparsers.add_parser("update_pr", help="Update a pull request")
    update_pr_parser.add_argument("pr_id", help="Pull request ID")
    update_pr_parser.add_argument("--status", choices=["open", "closed", "merged"], help="New status")
    update_pr_parser.add_argument("--comment-author", help="Comment author")
    update_pr_parser.add_argument("--comment-content", help="Comment content")
    update_pr_parser.add_argument("--approval-author", help="Approval author")
    
    # Get PRs
    get_prs_parser = subparsers.add_parser("get_prs", help="Get pull requests")
    get_prs_parser.add_argument("--status", choices=["open", "closed", "merged"], help="Status to filter by")
    
    # Log Reasoning
    log_reasoning_parser = subparsers.add_parser("log_reasoning", help="Log agent reasoning")
    log_reasoning_parser.add_argument("agent", help="Agent name")
    log_reasoning_parser.add_argument("task_id", help="Task ID")
    log_reasoning_parser.add_argument("reasoning", help="Reasoning text")
    log_reasoning_parser.add_argument("--tags", help="Comma-separated tags")
    
    # Get Reasoning Logs
    get_logs_parser = subparsers.add_parser("get_reasoning", help="Get reasoning logs")
    get_logs_parser.add_argument("--agent", help="Agent to filter by")
    get_logs_parser.add_argument("--task-id", help="Task ID to filter by")
    get_logs_parser.add_argument("--tags", help="Comma-separated tags to filter by")
    get_logs_parser.add_argument("--limit", type=int, default=10, help="Max logs to return")
    
    # Delete a specific task
    delete_task_parser = subparsers.add_parser("delete_task", help="Delete a specific task")
    delete_task_parser.add_argument("task_id", help="ID of the task to delete")
    delete_task_parser.add_argument("branch", nargs="?", help="Branch name (optional)")
    
    # Delete all tasks
    delete_all_parser = subparsers.add_parser("delete_all_tasks", help="Delete all tasks")
    delete_all_parser.add_argument("branch", nargs="?", help="Branch name (optional, if not provided all tasks in all branches will be deleted)")
    delete_all_parser.add_argument("--confirm", action="store_true", help="Confirmation flag (required for safety)")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Create the shared state manager
    state = SharedState(state_file)
    
    # Execute the requested command
    if args.command == "add_task":
        capabilities = None
        if hasattr(args, 'capabilities') and args.capabilities:
            capabilities = [cap.strip() for cap in args.capabilities.split(',')]
            
        task_id = state.add_task(
            args.branch, 
            args.description, 
            args.assigned_to, 
            args.priority,
            capabilities
        )
        print(f"Added task {task_id}")
    
    elif args.command == "update_task":
        success = state.update_task_status(
            args.task_id, 
            args.status, 
            args.branch,
            args.message if hasattr(args, 'message') else None
        )
        print(f"Task update {'successful' if success else 'failed'}")
    
    elif args.command == "get_tasks":
        tasks = state.get_tasks(
            agent=args.agent if hasattr(args, 'agent') else None,
            branch=args.branch,
            status=args.status,
            parent_task_id=args.parent if hasattr(args, 'parent') else None
        )
        if tasks:
            for task in tasks:
                status_str = f"[{task['status']}]".ljust(10)
                print(f"{task['id']}: {status_str} {task['description']}")
        else:
            print("No tasks found")
    
    elif args.command == "send_message":
        msg_id = state.add_message(
            args.from_agent, 
            args.to_agent, 
            args.content,
            args.channel,
            args.priority
        )
        print(f"Sent message {msg_id}")
    
    elif args.command == "get_messages":
        messages = state.get_messages(
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
        success = state.mark_message_read(args.message_id)
        print(f"Message mark read {'successful' if success else 'failed'}")
    
    elif args.command == "register_branch":
        success = state.register_branch(args.branch_name, args.description, args.owner)
        print(f"Branch registration {'successful' if success else 'failed'}")
    
    elif args.command == "create_pr":
        success = state.create_pull_request(
            args.pr_id, args.title, args.description,
            args.source_branch, args.target_branch, args.author
        )
        print(f"PR creation {'successful' if success else 'failed'}")
    
    elif args.command == "update_pr":
        comment = None
        if hasattr(args, 'comment_author') and hasattr(args, 'comment_content') and args.comment_author and args.comment_content:
            comment = {
                "author": args.comment_author,
                "content": args.comment_content
            }
        
        approval = None
        if hasattr(args, 'approval_author') and args.approval_author:
            approval = {"author": args.approval_author}
        
        success = state.update_pull_request(args.pr_id, args.status, comment, approval)
        print(f"PR update {'successful' if success else 'failed'}")
    
    elif args.command == "get_prs":
        prs = state.get_pull_requests(args.status)
        if prs:
            for pr in prs:
                status_str = f"[{pr['status']}]".ljust(10)
                print(f"{pr['id']}: {status_str} {pr['title']} ({pr['source_branch']} → {pr['target_branch']})")
        else:
            print("No pull requests found")
    
    elif args.command == "log_reasoning":
        log_id = state.log_reasoning(
            args.agent, 
            args.task_id, 
            args.reasoning,
            args.tags if hasattr(args, 'tags') else None
        )
        print(f"Logged reasoning {log_id}")
    
    elif args.command == "get_reasoning":
        tags = None
        if hasattr(args, 'tags') and args.tags:
            tags = [tag.strip() for tag in args.tags.split(',')]
            
        logs = state.get_reasoning_logs(
            args.agent, 
            args.task_id, 
            tags, 
            args.limit
        )
        if logs:
            for log in logs:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(log['timestamp']))
                print(f"\n--- {log['id']} | {log['agent']} | {timestamp} ---")
                print(f"Task: {log['task_id']}")
                print(f"Reasoning: {log['reasoning'][:100]}...")
        else:
            print("No reasoning logs found")
            
    elif args.command == "delete_task":
        success = state.delete_task(args.task_id, args.branch)
        print(f"Task deletion {'successful' if success else 'failed'}")
    
    elif args.command == "delete_all_tasks":
        if not args.confirm:
            print("Error: Please use --confirm flag to confirm this action")
            return
            
        success = state.delete_all_tasks(args.branch)
        print(f"Task deletion {'successful' if success else 'failed'}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()