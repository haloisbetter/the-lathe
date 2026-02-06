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
├── orchestrator.py # Drives Lathe, produces artifacts + speculative model selection
├── artifacts.py    # RunRecord, ProposalArtifact, RefusalArtifact
├── classification.py # Failure taxonomy (FailureType, ResultClassification)
├── trust.py        # Graduated trust policies (TrustPolicy, evaluate_trust)
├── stats.py        # Operational dashboard signals (run/workspace/health stats)
├── storage.py      # Pluggable persistence (InMemoryStorage, NullStorage)
├── executor.py     # PatchExecutor for applying proposals
├── http_serialization.py  # JSON serialization
├── server.py       # HTTP server for OpenWebUI
├── knowledge/      # Knowledge ingestion for RAG
│   ├── models.py   # Document, Chunk, KnowledgeIndexStatus
│   ├── ingest.py   # File ingestion with chunking
│   ├── index.py    # In-memory vector index
│   └── status.py   # Index status tracking
└── workspace/      # Workspace isolation + external repo ingestion
    ├── models.py   # Workspace dataclass
    ├── manager.py  # WorkspaceManager with path safety
    ├── context.py  # WorkspaceContext for scoping
    ├── registry.py # WorkspaceRegistry (by name, in-memory)
    ├── scanner.py  # Stateless filesystem scanner with glob filtering
    ├── indexer.py  # Per-workspace RAG index management
    ├── risk.py     # Workspace risk assessment (import graph, hotspots)
    ├── errors.py   # Workspace-specific error types
    └── status.py   # Index status tracking

tests/              # 440 tests
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
| `/knowledge/status` | GET | Knowledge index status |
| `/knowledge/ingest` | POST | Ingest documents for RAG |
| `/workspace/list` | GET | List all workspaces |
| `/workspace/create` | POST | Create a new workspace |
| `/runs/stats` | GET | Aggregated run statistics (by intent, model, rates) |
| `/workspace/stats` | GET | Workspace statistics (file counts, extensions) |
| `/health/summary` | GET | Health summary (recent errors, success rate) |

### OpenWebUI Tools

Eight tool schemas are defined in server.py:
- `lathe_agent`: Create a new run
- `lathe_execute`: Execute an approved proposal
- `lathe_runs`: Search run history
- `lathe_review`: Review/approve/reject proposals
- `lathe_fs`: Read-only filesystem inspection
- `lathe_knowledge_ingest`: Ingest documents into knowledge index for RAG
- `lathe_workspace_create`: Create a new workspace for project isolation
- `lathe_workspace_list`: List all registered workspaces

See `openwebui_tools.json` for complete tool schemas with parameter definitions.

### POST /agent
```json
{"intent": "propose", "task": "add auth", "why": {...}, "model": "optional"}
```

### POST /execute
```json
{"run_id": "run-123", "dry_run": true}
```

### POST /knowledge/ingest
```json
{"path": "docs/", "rebuild": false}
```

Response includes `ingested_documents`, `ingested_chunks`, `errors`, and `index_status`.

**Supported formats:** .md, .txt, .py, .json

**Path safety:** Rejects system directories (/etc, /var, etc.) and path traversals.

### POST /workspace/create
```json
{"path": "/home/user/my-project", "workspace_id": "optional-id"}
```

Creates a workspace scoped to the given path. Execution is refused outside workspace boundaries.

**Workspace Isolation:** "Lathe reasons globally. The app scopes locally. Executors act only inside workspaces."

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
