# Multi-Agent Claude System

A production-ready collaborative AI system where multiple Claude agents work together on complex tasks, each with their own specialization.

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/yourusername/multi-agent-claude/security-scan.yml?label=security%20scan)
![License](https://img.shields.io/github/license/yourusername/multi-agent-claude)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)

## What is Multi-Agent Claude?

This system orchestrates multiple Claude AI agents to solve complex problems that would be challenging for a single agent. Like a well-coordinated team, each agent has specific roles and expertise:

- **Team Lead**: Analyzes, breaks down, and coordinates complex tasks
- **API Agent**: Handles backend APIs and data processing
- **Dashboard Agent**: Creates visualization interfaces and dashboards
- **Login Agent**: Manages authentication and security features
- **Dynamic Agents**: Created on-demand for specialized requirements

## Key Features

- 🧠 **Specialized Agents**: Each Claude agent has its own memory, context, and capabilities
- 🔄 **Intelligent Task Breakdown**: Complex tasks are automatically analyzed and divided into manageable subtasks
- 💬 **Agent Communication Protocol**: Structured message-passing system between agents
- 🛠️ **Self-Enhancement**: Agents can develop tools to improve team capabilities
- 🔒 **Production-Ready Security**: Robust error handling, sandboxed execution, and credential protection
- 📊 **Monitoring Dashboard**: Real-time metrics on system performance and agent activity

## Quick Start

1. **Setup and Installation**
   ```bash
   # Clone this repository
   git clone https://github.com/yourusername/multi-agent-claude.git
   cd multi-agent-claude
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create and configure your environment
   cp .env.example .env
   # Edit .env file to add your Anthropic API key
   
   # Start the system
   ./scripts/start.sh
   ```

2. **Create Tasks**
   ```bash
   # Create a full-stack task
   ./scripts/task.sh "Create a data visualization dashboard for sales data"
   
   # Create a backend-focused task
   ./scripts/task.sh "Implement a REST API for user authentication" --capabilities="api,backend"
   
   # Create a custom task with specific requirements
   ./scripts/task.sh "Design a responsive landing page" --priority=high --capabilities="frontend,design"
   ```

3. **Monitor and Manage**
   ```bash
   # Check system status
   ./scripts/status.sh
   
   # View all tasks
   ./scripts/list-tasks.sh
   
   # Check agent activity
   ./scripts/agent-status.sh
   
   # Launch the monitoring dashboard
   python scripts/dashboard.py
   ```

## Common Commands

| Command | Description |
|---------|-------------|
| `./scripts/start.sh` | Start the multi-agent system |
| `./scripts/stop.sh` | Stop all agents |
| `./scripts/task.sh "Task description"` | Create a new task |
| `./scripts/list-tasks.sh` | List all current tasks |
| `./scripts/delete-task.sh <task_id>` | Delete a specific task |
| `./scripts/delete-all-tasks.sh` | Delete all tasks in the system |
| `./scripts/agent-status.sh` | Check status of all agents |
| `./scripts/add-data-task.sh` | Add a sample data analysis task |
| `./scripts/create-self-enhancement-task.sh` | Create a task for agents to enhance their capabilities |
| `./scripts/fix-and-restart.sh` | Fix issues and restart the system |
| `./scripts/regenerate.sh` | Regenerate the agent system |
| `./scripts/attach.sh` | Attach to the agent TMUX session |
| `./scripts/status.sh` | Check detailed system status |
| `./scripts/sync-code.sh` | Sync all agent code to the shared directory |
| `./scripts/list-agent-code.sh [agent_name] [--sync]` | List and optionally sync agent code |

## System Architecture

The Multi-Agent Claude system uses a sophisticated architecture to enable collaborative AI work:

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   Team Lead     │◄────┤  State Manager   │────►│ Specialized Agents │
│   Coordinator   │     │  Central Store   │     │ API, Dashboard, etc│
└────────┬────────┘     └──────────────────┘     └───────────────────┘
         │                       ▲                         ▲
         ▼                       │                         │
┌─────────────────┐              │                         │
│ Task Analyzer   │              │                         │
│ Breaks down and │              │                         │
│ assigns tasks   │              │                         │
└────────┬────────┘     ┌───────┴─────────┐     ┌─────────┴─────────┐
         │              │                 │     │                   │
         ▼              ▼                 ▼     ▼                   ▼
┌─────────────────┐  ┌─────────┐  ┌────────────┐  ┌─────────┐  ┌────────┐
│Shared Code Repo │  │ Metrics │  │ Monitoring │  │Reasoning│  │Sandbox │
│Tools & Modules  │  │Collector│  │ Dashboard  │  │ Logger  │  │Executor│
└─────────────────┘  └─────────┘  └────────────┘  └─────────┘  └────────┘
```

### How It Works

1. **Task Submission**: The user submits a complex task to the system
2. **Task Analysis**: The Team Lead agent analyzes the task's requirements and complexity
3. **Task Breakdown**: Complex tasks are split into smaller, specialized subtasks
4. **Capability Matching**: Subtasks are matched with agents based on required capabilities
5. **Parallel Execution**: Specialized agents work on their assigned subtasks independently
6. **Coordination**: Agents communicate progress, questions, and integration points
7. **Code Synchronization**: All code is automatically synced to the shared code repository
8. **Result Integration**: When all subtasks are complete, results are integrated into a cohesive solution
9. **Continuous Monitoring**: The monitoring system tracks performance and health metrics

## Shared Code Repository

All agent code is automatically synchronized to a central shared directory structure:

```
shared_code/
├── tools/         # Shared tools and utilities
├── modules/       # Core functionality modules  
├── integrations/  # External service integrations
└── ui/            # User interface components
```

When agents create code, they should use the `create_shared_file` function:

```bash
# Create a new Python tool
create_shared_file "search_tool" "py" "tools" "task_12345"

# Create a new JavaScript UI component
create_shared_file "dashboard" "js" "ui" "task_12345"
```

## Testing the System

Try these tests to verify your setup:

```bash
# Test the task breakdown system
./scripts/test-task-breakdown.sh

# Test agent reasoning capabilities
./scripts/test-reasoning.sh
```

## Troubleshooting

- **Agents not responding**: Run `./scripts/fix-and-restart.sh`
- **Tasks not being processed**: Check `./scripts/status.sh` for errors
- **API issues**: Verify your API key in the `.env` file

## Debugging & Maintenance

| Command | Description |
|---------|-------------|
| `./scripts/debug-context.sh` | Show debug information about the current context |
| `./scripts/regenerate-with-thinking.sh` | Regenerate system with enhanced reasoning |
| `./scripts/manual-breakdown.sh` | Manually break down a complex task |
| `rm -rf ./cache/claude_responses/*.json` | Clear the Claude API response cache |

## License

MIT License

---

Made with ❤️ using [Claude](https://www.anthropic.com/claude) | [Report Issues](https://github.com/yourusername/multi-agent-claude/issues)
