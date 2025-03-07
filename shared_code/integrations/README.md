# Shared Integrations

This directory contains integration components created by agents in the multi-agent system.

## Purpose

Integration components connect the system with external services and APIs.
These include API clients, service adapters, etc.

## Naming Convention

Integration components should follow this naming convention:

`{agent_name}_{service_name}_integration.{extension}`

For example:
- `agent3_google_search_integration.py`
- `api_agent_weather_api_integration.py`

## Documentation

Each integration file should include:

1. A clear file header describing the integration's purpose
2. API endpoints and methods documentation
3. Authentication requirements
4. Example usage in comments
5. A note about which agent created it

## Integration

Integration components in this directory can be imported by other components using:

```python
from shared_code.integrations.agent3_google_search_integration import GoogleSearchClient
```