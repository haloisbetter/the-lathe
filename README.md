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
├── cli/            # Command-line implementation
└── why.py          # WHY record engine
```

## Usage

The Lathe provides a CLI for orchestration.

```bash
# Run default task
python -m lathe

# Initialize configuration (creates lathe.yml)
python -m lathe init-config

# List all tasks
python -m lathe list

# Show task details
python -m lathe show <task_id>

# Show run details
python -m lathe run <run_id>

# Replay a task
python -m lathe replay <task_id>

# WHY Engine: Print a sample WHY record
python -m lathe why example

# Ledger: Show folder context memory
python -m lathe ledger show <path>

# Exec: Safe command execution (requires a WHY record)
# Automatically updates the folder ledger with the outcome.
python -m lathe exec --why why.json -- ls

# Apply: Controlled patch application (requires a WHY record)
# Automatically updates the folder ledger with the outcome.
python -m lathe apply --why why.json --patch fix.patch

# Repo: Search the repository for keywords or file names
python -m lathe repo search "bootstrap"

# Context: Retrieve exact code context with line numbers and hash
python -m lathe context get lathe/main.py:1-20

# RAG: Preview retrieved evidence for a task
python -m lathe rag preview "Implement database-free search"

# Think: Model reasoning layer (placeholder for model interaction)
python -m lathe think "Implement database-free search" --why why.json
```

## Folder Context Ledger

Lathe uses `.lathe.md` files for persistent folder-level memory. Use `lathe ledger show` to resolve and view the context for any path. Successful and failed `exec` and `apply` operations are automatically appended to the ledger.

## Safe Execution

The `exec` command provides controlled execution with an allowlist of tools and protection against destructive commands. Every execution requires a valid WHY record and is logged to the nearest folder ledger.

## Repo Awareness

The `repo search` command provides deterministic, database-free search across the repository, respecting `.gitignore` and skipping binary files.

## Deterministic Context

The `context get` command retrieves specific line ranges from files, providing line numbers and a SHA-256 hash for verification. This ensures evidence retrieval is reproducible and auditable.

## Patch System

The `apply` command allows applying unified diff patches to the codebase. It requires a WHY record, provides a preview, and asks for user confirmation before proceeding.

## WHY Engine

The WHY system is the foundational learning core of Lathe. Every major decision is backed by a WHY record containing:
- **goal**: What are we trying to achieve?
- **context**: The environment and constraints.
- **evidence**: Data supporting the decision.
- **options_considered**: Alternative paths.
- **decision**: The chosen path.
- **risk_level**: Potential impact.
- **guardrails**: Safety measures.
- **verification_steps**: How to prove it works.

## Development

Requires Python 3.11+.

```bash
# Run tests
pytest -q
```

## Configuration

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

## License

See LICENSE file for details.
