# Swarm Node — Shared Knowledge Base

This is the shared filing system for all swarm agents.

## Directory Structure

```
swarm_node/
├── swarm_node.py          # Main node server
├── shared/
│   ├── knowledge/         # Long-term facts, references, learned info
│   ├── tasks/             # Active task definitions and status
│   ├── results/           # Completed task outputs
│   └── logs/              # Agent activity logs
└── agents/                # Agent-specific working directories
```

## Conventions

- All agents read from `shared/knowledge/` before starting work
- Task definitions go in `shared/tasks/` with status tracking
- Completed outputs go in `shared/results/`
- Each agent has its own folder in `agents/` for scratch work
- Files are named: `YYYY-MM-DD_agent_name_topic.ext`
