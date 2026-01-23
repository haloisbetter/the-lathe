# The Lathe

> A local-first orchestrator that builds software systems by executing constrained tasks through agents.

## Overview

The Lathe is a deterministic, inspectable, and replaceable system for AI-driven software development. It orchestrates what to build, while delegating how to build to pluggable executor agents.

## Core Principles

- **Deterministic**: Every action is predictable and reproducible
- **Inspectable**: All operations are logged and queryable
- **Replaceable**: External dependencies can be swapped without core changes
- **Agent-Constrained**: Clear boundaries between orchestration and execution

## Architecture

```
lathe/
├── core/           # Task orchestration and execution pipeline
├── storage/        # SQLite-based persistence layer
├── bootstrap/      # Temporary external agent integrations
├── config/         # Configuration loading and validation
├── logging/        # Logging setup and utilities
└── cli/            # Command-line interface
```

## Responsibility Boundaries

### What The Lathe DOES
- Define task specifications
- Orchestrate task execution
- Persist task history
- Provide CLI interface
- Load configuration
- Setup logging infrastructure

### What The Lathe DOES NOT
- Decide HOW to implement tasks (delegated to executors)
- Contain AI reasoning logic
- Make direct network calls (abstracted through executors)
- Include SaaS dependencies in core

### Bootstrap Phase
Currently uses OpenHands as a bootstrap executor. This dependency is:
- Temporary
- Isolated to `lathe/bootstrap/`
- Designed to be replaceable

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize configuration
python -m lathe.main init-config

# Edit lathe.yml as needed
```

### Configuration

Copy `lathe.example.yml` to `lathe.yml` and customize:

```yaml
database:
  path: "data/lathe.db"

logging:
  level: "INFO"
  file: null

executor:
  type: "openhands"
  timeout: 300
```

Environment variable override: `LATHE_CONFIG=/path/to/config.yml`

### Usage

```bash
# Run default task
python -m lathe.main

# List all tasks
python -m lathe.main list

# Show task details
python -m lathe.main show <task_id>

# Show run details
python -m lathe.main run <run_id>

# Replay a task
python -m lathe.main replay <task_id>
```

## Development

```bash
# Run tests
make test

# Run smoke tests
make smoke

# Clean build artifacts
make clean
```

## Data Storage

All persistent data is stored in SQLite:
- Location: `data/lathe.db` (configurable)
- Schema: `lathe/storage/schema.sql`
- Tables: `tasks`, `runs`

## Logging

Logs are configured via `lathe.yml`:
- Console output (default)
- Optional file output
- Configurable levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Design Philosophy

1. **Configuration over code**: Behavior is controlled via YAML
2. **Explicit over implicit**: No magic, clear boundaries
3. **Simple over clever**: Boring, stable solutions
4. **Local-first**: No required external services
5. **Minimal dependencies**: Only what's necessary

## Extending The Lathe

### Adding a New Executor

1. Implement `BootstrapExecutor` interface
2. Add to `lathe/bootstrap/`
3. Register in configuration
4. Maintain isolation from core

### Adding a New CLI Command

1. Add function to `lathe/cli/commands.py`
2. Register in `lathe/main.py`
3. Follow existing patterns

## Status

**Current Phase**: Bootstrap (Milestone 1)

Goals:
- ✓ Establish structure
- ✓ Define bootstrap boundary
- ✓ Runnable CLI
- ✓ Configuration system
- ✓ Logging infrastructure

## License

See LICENSE file for details.