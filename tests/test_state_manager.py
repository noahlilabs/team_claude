#!/usr/bin/env python3
"""
Unit tests for the state manager component.
"""

import os
import sys
import json
import time
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.core.state_manager import SharedState


class TestSharedState(unittest.TestCase):
    """Test suite for SharedState class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary file for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "test_state.json"
        
        # Create state manager with test file
        self.state_manager = SharedState(str(self.state_file))
    
    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test if state file is correctly initialized."""
        # Assert file was created
        self.assertTrue(self.state_file.exists())
        
        # Check if initial structure is correct
        with open(self.state_file, 'r') as f:
            data = json.load(f)
            self.assertIn("tasks", data)
            self.assertIn("branches", data)
            self.assertIn("messages", data)
            self.assertIn("pull_requests", data)
            self.assertIn("reasoning_logs", data)
            self.assertIn("agents", data)
    
    def test_add_task(self):
        """Test adding a task."""
        task_id = self.state_manager.add_task("test_branch", "Test task", "agent1", "high")
        
        # Verify task was added
        tasks = self.state_manager.get_tasks(branch="test_branch")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["description"], "Test task")
        self.assertEqual(tasks[0]["assigned_to"], "agent1")
        self.assertEqual(tasks[0]["priority"], "high")
    
    def test_create_subtask(self):
        """Test creating a subtask linked to a parent task."""
        # Create parent task
        parent_id = self.state_manager.add_task("test_branch", "Parent task")
        
        # Create subtask
        subtask_id = self.state_manager.create_subtask(parent_id, "Subtask description", "agent2")
        
        # Verify subtask was created
        tasks = self.state_manager.get_tasks(parent_task_id=parent_id)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["description"], "Subtask description")
        self.assertEqual(tasks[0]["parent_id"], parent_id)
    
    def test_update_task_status(self):
        """Test updating task status."""
        # Create a task
        task_id = self.state_manager.add_task("test_branch", "Status test task")
        
        # Update status
        success = self.state_manager.update_task_status(task_id, "in-progress", message="Working on it")
        
        # Verify status was updated
        self.assertTrue(success)
        tasks = self.state_manager.get_tasks(branch="test_branch")
        self.assertEqual(tasks[0]["status"], "in-progress")
        self.assertIn("status_history", tasks[0])
        self.assertEqual(tasks[0]["status_history"][0]["message"], "Working on it")
    
    def test_add_message(self):
        """Test adding a message."""
        msg_id = self.state_manager.add_message("agent1", "agent2", "Test message", "direct", "high")
        
        # Verify message was added
        messages = self.state_manager.get_messages("agent2")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["content"], "Test message")
        self.assertEqual(messages[0]["sender"], "agent1")
        self.assertEqual(messages[0]["priority"], "high")
    
    def test_mark_message_read(self):
        """Test marking a message as read."""
        # Add a message
        msg_id = self.state_manager.add_message("agent1", "agent2", "Read test message")
        
        # Mark as read
        success = self.state_manager.mark_message_read(msg_id)
        
        # Verify message was marked as read
        self.assertTrue(success)
        messages = self.state_manager.get_messages("agent2", unread_only=False)
        self.assertTrue(messages[0]["read"])
    
    def test_log_reasoning(self):
        """Test logging agent reasoning."""
        log_id = self.state_manager.log_reasoning("agent1", "task123", "Test reasoning", "testing,reasoning")
        
        # Verify reasoning was logged
        logs = self.state_manager.get_reasoning_logs("agent1", "task123")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["reasoning"], "Test reasoning")
        self.assertIn("testing", logs[0]["tags"])
    
    def test_register_agent(self):
        """Test registering an agent."""
        success = self.state_manager.register_agent("test_agent", "tester", ["testing", "verification"])
        
        # Verify agent was registered
        self.assertTrue(success)
        agents = self.state_manager.get_agents()
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["id"], "test_agent")
        self.assertEqual(agents[0]["type"], "tester")
        self.assertIn("testing", agents[0]["capabilities"])
    
    def test_delete_task(self):
        """Test deleting a task."""
        # Create a task
        task_id = self.state_manager.add_task("test_branch", "Delete test task")
        
        # Delete the task
        success = self.state_manager.delete_task(task_id)
        
        # Verify task was deleted
        self.assertTrue(success)
        tasks = self.state_manager.get_tasks(branch="test_branch")
        self.assertEqual(len(tasks), 0)
    
    @patch('fcntl.flock')
    def test_file_locking(self, mock_flock):
        """Test file locking mechanism."""
        # Mock a successful lock acquisition
        mock_flock.return_value = None
        
        # Perform an operation that requires locking
        self.state_manager.add_task("test_branch", "Lock test task")
        
        # Verify lock was acquired
        mock_flock.assert_called()
    
    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        # Create a task to populate the file
        task_id = self.state_manager.add_task("test_branch", "Transaction test task")
        
        # Create a copy of the state file before error
        with open(self.state_file, 'r') as f:
            initial_state = json.load(f)
        
        # Define a callback that will raise an exception
        def failing_callback(data):
            data["tasks"]["test_branch"][0]["description"] = "Modified description"
            raise ValueError("Test error")
        
        # Attempt an operation that will fail
        with self.assertRaises(ValueError):
            self.state_manager._with_file_lock(failing_callback)
        
        # Verify the state file was not changed
        with open(self.state_file, 'r') as f:
            final_state = json.load(f)
        
        self.assertEqual(initial_state, final_state)


if __name__ == "__main__":
    unittest.main()