#!/usr/bin/env python3
"""
Configuration for Multi-Agent Claude System

This module provides centralized configuration for the multi-agent system,
including file paths, agent settings, and system parameters.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to allow importing from the project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables from .env file if it exists
try:
    from src.utils.env_loader import load_env
    load_env()
except (ImportError, Exception) as e:
    # If there's any issue with load_env, continue with environment as is
    print(f"Note: Could not load environment from .env file: {e}")
    print("Using existing environment variables...")

# Base directories
ROOT_DIR = Path(__file__).parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
AGENTS_DIR = ROOT_DIR / "agents"
LOGS_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"

# Create necessary directories
AGENTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# State file
STATE_FILE = os.environ.get("CLAUDE_STATE_FILE", str(ROOT_DIR / "claude_state.json"))

# Dynamic agent configuration
MAX_AGENTS = 10

# Agent types
AGENT_TYPES = {
    "manager": {
        "description": "Task breakdown and coordination",
        "capabilities": ["planning", "task_assignment", "integration"]
    },
    "frontend": {
        "description": "UI and frontend development",
        "capabilities": ["html", "css", "javascript", "react"]
    },
    "backend": {
        "description": "API and server development",
        "capabilities": ["python", "api", "database", "server"]
    },
    "data": {
        "description": "Data processing and analysis",
        "capabilities": ["data_processing", "analytics", "visualization"]
    },
    "testing": {
        "description": "Quality assurance and testing",
        "capabilities": ["testing", "debugging", "validation"]
    }
}

# Task system configuration
TASK_PRIORITY_LEVELS = ["low", "medium", "high", "critical"]
TASK_STATUS_TYPES = ["pending", "in-progress", "blocked", "completed", "failed"]

# Communication system
COMMUNICATION_CHANNELS = {
    "direct": "Agent-to-agent direct communication",
    "broadcast": "One-to-all communication",
    "group": "Communication to a subset of agents"
}

# Agent settings
AGENTS = {
    "team_lead": {
        "name": "team_lead",
        "type": "manager",
        "branch": "master",
        "description": "Team leader coordinating all agents",
        "capabilities": ["planning", "task_assignment", "integration", "architecture"],
        "working_dir": str(AGENTS_DIR / "team_lead")
    },
    "agent1": {
        "name": "agent1",
        "type": "frontend",
        "branch": "feature-login",
        "description": "Login and authentication features",
        "capabilities": ["html", "css", "javascript", "auth"],
        "working_dir": str(AGENTS_DIR / "login")
    },
    "agent2": {
        "name": "agent2",
        "type": "frontend",
        "branch": "feature-dashboard",
        "description": "Dashboard and UI features",
        "capabilities": ["html", "css", "javascript", "visualization"],
        "working_dir": str(AGENTS_DIR / "dashboard")
    },
    "agent3": {
        "name": "agent3",
        "type": "backend",
        "branch": "feature-api",
        "description": "API and backend features",
        "capabilities": ["python", "api", "database", "server"],
        "working_dir": str(AGENTS_DIR / "api")
    }
}

# Tmux configuration
TMUX_SESSION_NAME = "claude-team"

# Claude API settings
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
CLAUDE_MODEL = "claude-3-7-sonnet-20250219"

# Caching settings
ENABLE_CACHE = True
CACHE_DIR = os.path.join(ROOT_DIR, "cache")
CACHE_EXPIRY = 86400  # 24 hours in seconds

# System settings
CHECK_INTERVAL = 5  # Time between checking for new tasks (seconds)
CHECK_AGENT_HEALTH_INTERVAL = 30  # Time between checking agent health (seconds)
INACTIVE_AGENT_THRESHOLD = 300  # Time before an agent is considered inactive (seconds)
MAX_REASONING_LENGTH = 1000  # Max characters to store for reasoning logs
MAX_RESPONSE_LENGTH = 4000  # Max characters to display from Claude responses

# Templates and scripts
AGENT_TEMPLATE_SCRIPT = str(ROOT_DIR / "src" / "agents" / "templates" / "agent_template.sh")
SCRIPTS_DIR = ROOT_DIR / "scripts"
START_SCRIPT = str(SCRIPTS_DIR / "start.sh")
VIEW_ACTIVITY_SCRIPT = str(SCRIPTS_DIR / "view_agent_activity.py")

# Git settings
GIT_REPO_DIR = str(ROOT_DIR / "repository")