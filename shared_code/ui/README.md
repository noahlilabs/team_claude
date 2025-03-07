# Shared UI Components

This directory contains UI components created by agents in the multi-agent system.

## Purpose

UI components provide the visual interface elements of the system.
These include frontend elements, visualizations, dashboards, etc.

## Naming Convention

UI components should follow this naming convention:

`{agent_name}_{component_name}.{extension}`

For example:
- `agent1_dashboard.js`
- `agent2_visualization.js`
- `login_form.html`

## Documentation

Each UI component file should include:

1. A clear file header describing the component's purpose
2. Component properties and methods documentation
3. Example usage in comments if applicable
4. A note about which agent created it

## Integration

UI components in this directory can be imported in JavaScript using:

```javascript
import { Dashboard } from './shared_code/ui/agent1_dashboard.js';
```

Or referenced in HTML:

```html
<script src="./shared_code/ui/agent1_dashboard.js"></script>
```