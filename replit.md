# The Lathe

A local-first orchestrator that builds software systems by executing constrained tasks through agents.

## Overview

The Lathe is a deterministic, inspectable, and replaceable system for AI-driven software development. It orchestrates what to build, while delegating how to build to pluggable executor agents.

**Architectural Law:** "Lathe reasons. The app decides. Executors act. Nothing else is allowed."

## Project Type

This is a **Python CLI application** with an HTTP backend for OpenWebUI integration. No web frontend.

## Project Structure

```
lathe/              # Pure reasoning kernel (NEVER stores state)
├── pipeline.py     # Main request processing
├── normalize.py    # Input normalization
├── output_validator.py  # Response validation
├── model_tiers.py  # Model capability tiers
├── observability.py # Passive instrumentation
└── server.py       # Legacy HTTP adapter

lathe_app/          # Application layer (all state lives here)
├── __init__.py     # Public API: run_request, execute_proposal, etc.
├── orchestrator.py # Drives Lathe, produces artifacts
├── artifacts.py    # RunRecord, ProposalArtifact, RefusalArtifact
├── storage.py      # Pluggable persistence (InMemoryStorage, NullStorage)
├── executor.py     # PatchExecutor for applying proposals
├── http_serialization.py  # JSON serialization
└── server.py       # HTTP server for OpenWebUI

tests/              # 167 tests
├── test_*.py       # Core Lathe tests
└── app/            # App layer tests
```

## Running the Application

```bash
# CLI interface
python -m lathe.main

# App HTTP server (port 3001, configurable)
python -m lathe_app.server

# App with custom port
python -m lathe_app.server --port 4000
LATHE_APP_PORT=4000 python -m lathe_app.server

# Kernel server (port 5000, direct access)
python -m lathe.server
```

## HTTP API (lathe_app.server)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/runs` | GET | Search runs (query params: intent, outcome, file, since, until, limit) |
| `/runs/<id>` | GET | Load a specific run |
| `/runs/<id>/review` | GET | Get review state for a run |
| `/agent` | POST | Create a run (propose/think/rag/plan) |
| `/execute` | POST | Execute an approved proposal |
| `/review` | POST | Review/approve/reject a proposal |
| `/fs/tree` | GET | Directory tree (query: path, max_depth) |
| `/fs/status` | GET | Git status |
| `/fs/diff` | GET | Git diff (query: staged) |
| `/fs/run/<id>/files` | GET | Files touched by a run |

### OpenWebUI Tools

Five tool schemas are defined in server.py:
- `lathe_agent`: Create a new run
- `lathe_execute`: Execute an approved proposal
- `lathe_runs`: Search run history
- `lathe_review`: Review/approve/reject proposals
- `lathe_fs`: Read-only filesystem inspection

See `openwebui_tools.json` for complete tool schemas with parameter definitions.

### POST /agent
```json
{"intent": "propose", "task": "add auth", "why": {...}, "model": "optional"}
```

### POST /execute
```json
{"run_id": "run-123", "dry_run": true}
```

## Python API (lathe_app)

```python
from lathe_app import run_request, execute_proposal

# 1. Create a run (proposals do NOT auto-apply)
run = run_request(intent="propose", task="add auth", why={...})

# 2. Execute explicitly (dry_run=True by default)
result = execute_proposal(run.id, dry_run=False)
```

## Development Commands

```bash
# Run tests
pytest -q

# or via Makefile
make check
```

## Requirements

- Python 3.11+
- pytest
- pyyaml
