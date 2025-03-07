# Shared Tools

This directory contains all shared tools created by agents in the multi-agent system.

## Purpose

Tools are standalone utilities that provide specific functionality to the system.
Examples include search tools, file manipulation tools, data processing tools, etc.

## Naming Convention

Tools should follow this naming convention:

`{agent_name}_{tool_name}.{extension}`

For example:
- `agent1_web_search.py`
- `team_lead_file_processor.py`

## Documentation

Each tool file should include:

1. A clear file header docstring describing the tool's purpose
2. Function/method-level documentation
3. Example usage if applicable
4. A note about which agent created it

## Integration

Tools in this directory can be imported by other components using:

```python
from shared_code.tools.agent1_web_search import WebSearch
```