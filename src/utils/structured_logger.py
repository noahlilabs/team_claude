#!/usr/bin/env python3
"""
Structured Logging Framework for Multi-Agent Claude System

This module provides a unified logging interface with structured JSON logs,
log correlation, and centralized configuration.
"""

import os
import sys
import json
import logging
import time
import uuid
import socket
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core import config

# Constants
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(message)s"
HOSTNAME = socket.gethostname()


class StructuredLogger:
    """
    Enhanced logger that outputs structured JSON logs with consistent fields.
    """
    
    def __init__(
        self,
        name: str,
        agent_id: Optional[str] = None,
        log_dir: Optional[str] = None,
        log_level: str = DEFAULT_LOG_LEVEL,
        correlation_id: Optional[str] = None,
    ):
        """
        Initialize the structured logger.
        
        Args:
            name: Logger name
            agent_id: Optional agent identifier
            log_dir: Optional directory for log files
            log_level: Logging level (INFO, DEBUG, etc)
            correlation_id: Optional correlation ID for request tracing
        """
        self.name = name
        self.agent_id = agent_id or "system"
        self.correlation_id = correlation_id or str(uuid.uuid4())
        
        # Set up logging level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(numeric_level)
        self.logger.propagate = False
        
        # Clear existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Configure file handler if log_dir provided
        if log_dir:
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True, parents=True)
            
            file_handler = logging.FileHandler(
                log_path / f"{name.lower().replace(' ', '_')}.log"
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            self.logger.addHandler(file_handler)
        
        # Always add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        self.logger.addHandler(console_handler)
        
        self.debug("Structured logger initialized")
    
    def _format_log(
        self, 
        level: str, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Format log entry as JSON with consistent fields.
        
        Args:
            level: Log level
            message: Log message
            context: Optional contextual data
            error: Optional exception
            task_id: Optional task identifier
            
        Returns:
            Formatted JSON log string
        """
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
        
        log_data = {
            "timestamp": timestamp,
            "level": level,
            "logger": self.name,
            "agent_id": self.agent_id,
            "correlation_id": self.correlation_id,
            "message": message,
            "hostname": HOSTNAME,
        }
        
        # Add optional fields
        if task_id:
            log_data["task_id"] = task_id
            
        if context:
            log_data["context"] = context
            
        if error:
            log_data["error"] = {
                "type": error.__class__.__name__,
                "message": str(error),
                "traceback": traceback.format_exc(),
            }
        
        return json.dumps(log_data)
    
    def debug(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """Log at DEBUG level."""
        formatted = self._format_log("DEBUG", message, context, None, task_id)
        self.logger.debug(formatted)
        
    def info(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """Log at INFO level."""
        formatted = self._format_log("INFO", message, context, None, task_id)
        self.logger.info(formatted)
        
    def warning(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """Log at WARNING level."""
        formatted = self._format_log("WARNING", message, context, None, task_id)
        self.logger.warning(formatted)
        
    def error(
        self, 
        message: str, 
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """Log at ERROR level."""
        formatted = self._format_log("ERROR", message, context, error, task_id)
        self.logger.error(formatted)
        
    def critical(
        self, 
        message: str, 
        error: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """Log at CRITICAL level."""
        formatted = self._format_log("CRITICAL", message, context, error, task_id)
        self.logger.critical(formatted)
        
    def with_correlation(self, correlation_id: str) -> "StructuredLogger":
        """
        Create a new logger with the same config but a different correlation ID.
        
        Args:
            correlation_id: New correlation ID
            
        Returns:
            New logger instance with updated correlation ID
        """
        return StructuredLogger(
            name=self.name,
            agent_id=self.agent_id,
            log_level=self.logger.level,
            correlation_id=correlation_id,
        )
        
    def with_task(self, task_id: str) -> "TaskLogger":
        """
        Create a task-specific logger wrapper.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskLogger instance
        """
        return TaskLogger(self, task_id)


class TaskLogger:
    """Wrapper around StructuredLogger that automatically includes task_id."""
    
    def __init__(self, logger: StructuredLogger, task_id: str):
        self.logger = logger
        self.task_id = task_id
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self.logger.debug(message, context, self.task_id)
        
    def info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self.logger.info(message, context, self.task_id)
        
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        self.logger.warning(message, context, self.task_id)
        
    def error(
        self, 
        message: str, 
        error: Optional[Exception] = None, 
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        self.logger.error(message, error, context, self.task_id)
        
    def critical(
        self, 
        message: str, 
        error: Optional[Exception] = None, 
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        self.logger.critical(message, error, context, self.task_id)


# Get logger instance
def get_logger(
    name: str, 
    agent_id: Optional[str] = None,
    log_dir: Optional[str] = None,
    log_level: str = DEFAULT_LOG_LEVEL,
    correlation_id: Optional[str] = None,
) -> StructuredLogger:
    """
    Get a configured structured logger.
    
    Args:
        name: Logger name
        agent_id: Optional agent identifier
        log_dir: Optional directory for log files
        log_level: Logging level (INFO, DEBUG, etc)
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Configured structured logger
    """
    return StructuredLogger(name, agent_id, log_dir, log_level, correlation_id)


# Example usage
if __name__ == "__main__":
    # Example
    logger = get_logger("ExampleLogger", "test_agent", log_dir="logs")
    
    # Log at different levels
    logger.debug("Debug message")
    logger.info("Info message with context", {"user_id": 123, "action": "login"})
    
    # Log with task ID
    task_logger = logger.with_task("task_123")
    task_logger.info("Processing task")
    
    # Log errors
    try:
        x = 1 / 0
    except Exception as e:
        logger.error("An error occurred", e, {"operation": "division"})