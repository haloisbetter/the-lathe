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
├── trust.py        # Graduated trust policies (TrustPolicy, evaluate_trust, evaluate_git_trust)
├── stats.py        # Operational dashboard signals (run/workspace/health stats)
├── storage.py      # Pluggable persistence (InMemoryStorage, NullStorage)
├── executor.py     # PatchExecutor for applying proposals + auto_commit_after_execution
├── http_serialization.py  # JSON serialization
├── server.py       # HTTP server for OpenWebUI
├── contracts/      # Canonical agent contracts (read-only)
│   └── agent_contract.md  # Mandatory behavioral contract for all agents
├── validation/     # Structural validators for agent responses
│   └── context_echo.py    # Context Echo Block validator (deterministic)
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
    ├── snapshot.py # Workspace snapshot (authoritative manifest + stats)
    ├── memory.py   # File read artifacts + staleness detection + context.md
    ├── risk.py     # Workspace risk assessment (import graph, hotspots)
    ├── git_workspace.py # Git-backed workspace operations (clone/pull/status/commit/push)
    ├── errors.py   # Workspace-specific error types
    └── status.py   # Index status tracking

tests/              # 591 tests
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
| `/runs/<id>/staleness` | GET | Check file read staleness for a run |
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

## Git-backed Workspaces

The Lathe supports first-class Git-backed workspaces, allowing repos to be imported, managed, and pushed with trust-based approval gates.

### Git Intent (workspace.git)

Git operations are handled via `POST /agent` with `intent: workspace.git`. This intent is NOT handled by the kernel and does NOT invoke a model.

```json
{
  "intent": "workspace.git",
  "action": "clone",
  "workspace": "my-project",
  "repo": "git@github.com:user/my-project.git",
  "branch": "main"
}
```

Supported actions: `clone`, `pull`, `status`, `commit`, `push`

### Trust Policy for Git Operations

Trust levels gate git write operations (declared in `.lathe/trust.json`):

| Trust Level | clone | pull | status | commit | push |
|-------------|-------|------|--------|--------|------|
| 0 (default) | Yes | Yes | Yes | No | No |
| 1 | Yes | Yes | Yes | No | No |
| 2 | Yes | Yes | Yes | Yes | No |
| 3 | Yes | Yes | Yes | Yes | Yes |
| 4 | Yes | Yes | Yes | Yes | Yes |

### Proposal → Commit Flow

After a proposal is executed (not dry_run), the system can auto-commit if trust allows:
1. Apply diffs (existing executor flow)
2. If trust >= 2: `git commit -m "Lathe: <summary>"`
3. If trust >= 3: auto-push after commit

Use `auto_commit_after_execution()` from `lathe_app.executor`.

### Safety Guarantees

- Whitelisted git commands only (clone, pull, status, commit, push, log, init, add, etc.)
- No `shell=True` in subprocess
- cwd locked to workspace directory
- Credentials redacted from all output
- Workspace boundary checks enforced at all trust levels

## Agent Contract & Context Echo Validation

The Lathe enforces a mandatory Agent Contract on all executor agents. The contract is stored canonically at `lathe_app/contracts/agent_contract.md` (read-only, never mutated at runtime).

### Context Echo Block

Every agent response MUST include a Context Echo Block declaring what context it has access to:

```
--- CONTEXT_ECHO_START ---
Workspace: <name or NONE>
Snapshot: <id or NONE>
Files:
- path/to/file.py
- path/to/file2.md
--- CONTEXT_ECHO_END ---
```

### Deterministic Validation

The validator (`lathe_app/validation/context_echo.py`) enforces three structural rules:

1. **Block must exist** — delimited by `CONTEXT_ECHO_START` / `CONTEXT_ECHO_END`
2. **Required fields** — Workspace, Snapshot, Files must all be present
3. **No undeclared file references** — any file path referenced in reasoning must appear in the Files list

On failure: structured refusal with WHY record. No retries, no reframing, no model escalation.

### Orchestrator Wiring

Enable via `Orchestrator(require_context_echo=True)`. The validator wraps the agent_fn to intercept raw model output before kernel processing:

```
model_output → context_echo_validator → kernel output_validator → classification → execution
```

If validation fails, a structured refusal flows through the normal pipeline. The kernel remains untouched.

## Workspace Memory Contract

The Lathe implements a first-class workspace memory system that explicitly tracks what the AI knows, how it knows it, and whether that knowledge is stale.

### A. Workspace Snapshot (Authoritative)

Triggered via `POST /agent` with `intent: context`, `task: ingest_workspace`:

```json
{
  "intent": "context",
  "task": "ingest_workspace",
  "workspace": {
    "name": "my-project",
    "root_path": "/path/to/repo"
  }
}
```

Produces two artifacts:
- **workspace_manifest**: Per-file metadata (relative path, size, line count, extension, sha256 content hash, timestamp)
- **workspace_stats**: Aggregate statistics (total/python/markdown file counts, extension distribution, directory depth histogram)

Safety: Rejects system paths, self-ingestion, non-existent paths.

### B. File Read Artifacts + Staleness Detection

Every file read during reasoning produces a `FileReadArtifact` (path, content_hash, line_range, timestamp) attached to the `RunRecord.file_reads` list.

Check staleness via `GET /runs/<id>/staleness` — compares stored hashes against current filesystem state. If a file changed after being read, the run is flagged as "potentially stale."

This is **observability, not enforcement** — the system detects drift but does not silently reuse outdated content.

### C. Persistent Workspace Memory (.lathe/context.md)

An optional, human-authored file loaded automatically at session start:
- `.lathe/context.md` (preferred) or `lathe.md` (fallback)
- Contains project structure, invariants, trust level, architectural boundaries
- Operator-controlled — never auto-generated or auto-summarized
- Loaded and attached to `RunRecord.workspace_context_loaded`

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
