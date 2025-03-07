# Shared Modules

This directory contains core functionality modules created by agents in the multi-agent system.

## Purpose

Modules provide the core business logic and functionality of the system.
They are more fundamental than tools and typically represent the main components.

## Naming Convention

Modules should follow this naming convention:

`{agent_name}_{module_name}.{extension}`

For example:
- `agent2_data_processor.py`
- `team_lead_task_manager.py`

## Documentation

Each module file should include:

1. A clear file header docstring describing the module's purpose
2. Class and method-level documentation
3. Example usage in comments if applicable
4. A note about which agent created it

## Integration

Modules in this directory can be imported by other components using:

```python
from shared_code.modules.agent2_data_processor import DataProcessor
```