# Multi-Agent Claude System

A collaborative AI system where multiple Claude agents work together on complex tasks, each specializing in different areas.

## Overview

This system orchestrates multiple Claude agents to solve complex problems:
- **Team Lead**: Analyzes tasks and coordinates work
- **Specialized Agents**: Handle specific components (API, Dashboard, Login, etc.)
- **Dynamic Agents**: Created on-demand for specialized requirements

## Key Features

- **Specialized Agents**: Each agent has dedicated capabilities
- **Task Breakdown**: Large tasks are divided into manageable subtasks
- **Agent Communication**: Structured message system between agents
- **Production-Ready**: Error handling, sandboxed execution, monitoring

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/multi-agent-claude.git
cd multi-agent-claude
pip install -r requirements.txt
cp .env.example .env # Add your API key

# Start system
./scripts/start.sh

# Create a task
./scripts/task.sh "Create a data visualization dashboard"

# Monitor progress
./scripts/status.sh
```

## Architecture

```
Team Lead -- State Manager -- Specialized Agents
      |           |              |
      |           |              |
      |           |              |
Task Analyzer     |              |
      |           |              |
      |           |              |
Shared Code   Metrics    Monitoring    Reasoning    Sandbox
```

## Common Commands

| Command | Description |
|---------|-------------|
| `./scripts/start.sh` | Start the system |
| `./scripts/stop.sh` | Stop all agents |
| `./scripts/task.sh "Description"` | Create a task |
| `./scripts/list-tasks.sh` | List all tasks |
| `./scripts/agent-status.sh` | Check agent status |
| `./scripts/status.sh` | View system status |
| `./scripts/dashboard.py` | Launch monitoring dashboard |

## Advanced Features

- **Error Recovery**: Automatic agent monitoring and restart
- **Code Validation**: Security checks before execution
- **Containerization**: Docker-based agent isolation
- **Shared Code Repo**: Central code synchronization
- **Metrics Collection**: Performance monitoring

## License

MIT License

---

Made with love using Claude
