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

# App HTTP server (port 3000)
python -m lathe_app.server
```

## HTTP API (lathe_app.server)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/runs` | GET | List all run IDs |
| `/runs/<id>` | GET | Load a specific run |
| `/agent` | POST | Create a run (propose/think/rag/plan) |
| `/execute` | POST | Execute a proposal |

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
