# Shared Code Directory

This directory contains all code produced by the multi-agent system. Agents should save their work here for better integration and collaboration.

## Directory Structure

- `tools/`: Shared tools and utilities used across the system
- `modules/`: Core functionality modules
- `integrations/`: Integration code for external services
- `ui/`: User interface components

## Usage Guidelines

1. All agents should save their code in this directory rather than in agent-specific locations
2. Use clear file naming with descriptive prefixes
3. Include a comment header in each file indicating the agent that created it
4. Before integrating code, run tests when available

## Automatic Code Sync

The system automatically syncs code from individual agent workspaces to this directory.