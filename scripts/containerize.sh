#!/bin/bash
# Script to containerize agent execution for security and isolation

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

# Create Dockerfile for agent container
cat << 'EOF' > "$REPO_ROOT/Dockerfile.agent"
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tmux \
    bash \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create agent user with limited permissions
RUN useradd -m -s /bin/bash agent

# Set up environment
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set permissions
RUN chown -R agent:agent /app
USER agent

# Default environment variables
ENV CLAUDE_AGENT_NAME="containerized_agent"
ENV CLAUDE_AGENT_TYPE="general"
ENV CLAUDE_AGENT_CAPABILITIES="general"
ENV CHECK_INTERVAL=5

# Entry point
ENTRYPOINT ["bash", "scripts/container-entrypoint.sh"]
EOF

# Create entrypoint script
cat << 'EOF' > "$REPO_ROOT/scripts/container-entrypoint.sh"
#!/bin/bash
# Container entrypoint script

# Set up environment
export REPO_ROOT="/app"

# Validate agent name
if [ -z "$CLAUDE_AGENT_NAME" ]; then
  echo "ERROR: CLAUDE_AGENT_NAME environment variable must be set"
  exit 1
fi

echo "Starting agent: $CLAUDE_AGENT_NAME"

# Source appropriate agent script based on agent name
if [ "$CLAUDE_AGENT_NAME" = "team_lead" ]; then
  source "$REPO_ROOT/src/agents/team_lead.sh"
elif [ -f "$REPO_ROOT/agents/$CLAUDE_AGENT_NAME/claude_agent.sh" ]; then
  source "$REPO_ROOT/agents/$CLAUDE_AGENT_NAME/claude_agent.sh"
else
  echo "ERROR: Agent script not found for $CLAUDE_AGENT_NAME"
  exit 1
fi

# Keep container running (agent scripts run in background)
tail -f /dev/null
EOF

chmod +x "$REPO_ROOT/scripts/container-entrypoint.sh"

# Script to build agent containers
cat << 'EOF' > "$REPO_ROOT/scripts/build-containers.sh"
#!/bin/bash
# Build agent containers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

echo "Building base agent image..."
docker build -t claude-agent:latest -f "$REPO_ROOT/Dockerfile.agent" "$REPO_ROOT"

echo "Base agent image built successfully"
EOF

chmod +x "$REPO_ROOT/scripts/build-containers.sh"

# Script to run agent in container
cat << 'EOF' > "$REPO_ROOT/scripts/start-containerized.sh"
#!/bin/bash
# Start agents in containers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_DIR")" && pwd)"

# Create shared network if it doesn't exist
docker network inspect claude-agents >/dev/null 2>&1 || docker network create claude-agents

# Function to start an agent container
start_agent() {
  local agent_name="$1"
  
  echo "Starting containerized agent: $agent_name"
  
  # Check if container already exists and remove if it does
  if docker ps -a --format '{{.Names}}' | grep -q "claude-$agent_name"; then
    echo "Container for $agent_name already exists, removing..."
    docker rm -f "claude-$agent_name"
  fi
  
  # Load API key from .env file
  if [ -f "$REPO_ROOT/.env" ]; then
    api_key=$(grep "ANTHROPIC_API_KEY" "$REPO_ROOT/.env" | cut -d '=' -f2 | tr -d '"' | tr -d "'")
  else
    echo "ERROR: .env file not found"
    return 1
  fi
  
  # Start container
  docker run -d \
    --name "claude-$agent_name" \
    --network claude-agents \
    --restart unless-stopped \
    -e CLAUDE_AGENT_NAME="$agent_name" \
    -e ANTHROPIC_API_KEY="$api_key" \
    -v "$REPO_ROOT/shared_code:/app/shared_code:rw" \
    -v "$REPO_ROOT/data:/app/data:ro" \
    -v "$REPO_ROOT/logs:/app/logs:rw" \
    --memory=1g \
    --cpus=0.5 \
    claude-agent:latest
    
  echo "Agent $agent_name started in container"
}

# Start all agents or specified agent
if [ -z "$1" ]; then
  # Start all agents
  start_agent "team_lead"
  start_agent "agent1" 
  start_agent "agent2"
  start_agent "agent3"
else
  # Start specific agent
  start_agent "$1"
fi

# Show running containers
echo ""
echo "Running agent containers:"
docker ps --filter "name=claude-"
EOF

chmod +x "$REPO_ROOT/scripts/start-containerized.sh"

echo "Containerization scripts created:"
echo "1. build-containers.sh - Build the agent container image"
echo "2. start-containerized.sh - Start agents in containers"
echo ""
echo "To use containerized agents:"
echo "1. Run: ./scripts/build-containers.sh"
echo "2. Run: ./scripts/start-containerized.sh"
echo ""
echo "Docker must be installed on your system."