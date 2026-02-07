# The Lathe

## Overview

The Lathe is a local-first orchestrator designed for AI-driven software development. Its core purpose is to build software systems by executing constrained tasks through pluggable agents. It aims to provide a deterministic, inspectable, and replaceable system, orchestrating "what to build" and delegating "how to build" to specialized executor agents. The project functions as a Python CLI application with an HTTP backend for integration with tools like OpenWebUI, focusing on robust backend operations without a web frontend. Its business vision centers on enabling reliable, AI-assisted software creation with clear architectural boundaries and strong safety guarantees.

## User Preferences

No specific user preferences were provided in the original `replit.md` file.

## System Architecture

The Lathe's architecture strictly separates reasoning (kernel) from stateful application logic.

**Core Principles:**
-   **Architectural Law:** "Lathe reasons. The app decides. Executors act. Nothing else is allowed."
-   **Separation of Concerns:** `lathe/` contains the stateless reasoning kernel, while `lathe_app/` manages all state, application logic, and external interactions.
-   **Workspace Isolation:** All agent actions are strictly scoped within isolated workspaces, preventing unauthorized access or modifications outside defined project boundaries.
-   **Deterministic Validation:** Agent responses are rigorously validated against contracts (e.g., Context Echo, Tool-Selection) to ensure compliance and predictable behavior.

**Key Components & Features:**
-   **Kernel (`lathe/`):** Handles core request processing, input normalization, output validation, and model tiering. It is stateless.
-   **Application Layer (`lathe_app/`):**
    -   **Orchestrator:** Drives the Lathe, manages speculative model selection, and produces run artifacts.
    -   **Artifacts:** Defines data structures for `RunRecord`, `ProposalArtifact`, `RefusalArtifact`.
    -   **Trust Policies:** Implements graduated trust levels for sensitive operations, particularly Git interactions.
    -   **Storage:** Pluggable persistence mechanisms (e.g., InMemoryStorage).
    -   **Executor:** Applies proposals, with optional auto-commit based on trust levels.
    -   **Contracts (`lathe_app/contracts/`):** Defines mandatory `Agent Contract` and `Tool-Selection Contract` that all agents must adhere to.
    -   **Validation (`lathe_app/validation/`):** Enforces structural rules like the `Context Echo Block` in agent responses.
    -   **Tools (`lathe_app/tools/`):** A registry for GET-based, read-only tools (e.g., `fs_tree`, `git_status`). Includes `requests.py` (tool_call v1 + tool_request legacy parsing), `execution.py` (tool execution + ToolCallTrace + TOOL_CONTEXT generation).
    -   **Knowledge (`lathe_app/knowledge/`):** Manages knowledge ingestion, chunking, and in-memory vector indexing for RAG.
    -   **Workspace (`lathe_app/workspace/`):** Provides workspace management, context scoping, snapshotting, memory tracking (`.lathe/context.md`), risk assessment, and Git integration.
-   **TUI (`lathe_tui/`):** A Text-User Interface console acting as a pure HTTP client for the `lathe_app.server`.
-   **HTTP API:** Exposes endpoints for managing runs, executing proposals, reviewing, filesystem inspection, knowledge ingestion, and workspace management.
-   **Git-backed Workspaces:** Supports cloning, pulling, committing, and pushing to Git repositories, gated by trust policies for write operations.
    -   **Safety Guarantees:** Git operations are whitelisted, executed without `shell=True`, locked to workspace directories, and credentials are redacted.
-   **Agent Contract Enforcement:** Mandates a `Context Echo Block` in every agent response, declaring accessed context (Workspace, Snapshot, Files) and validating against undeclared file references.
-   **Tool-Selection Contract:** Enforces a structured `tool_call` format with a mandatory `why` justification and rules for when agents *must* use tools.
-   **Workspace Memory:**
    -   **Workspace Snapshot:** Generates manifest and statistics for a given workspace.
    -   **File Read Artifacts + Staleness Detection:** Tracks file reads and identifies when content becomes stale.
    -   **Persistent Workspace Memory:** Supports loading `lathe.md` or `.lathe/context.md` for human-authored project context.

**Design Patterns:**
-   Command Query Responsibility Segregation (CQRS) principles are implicitly followed by separating intent (`propose`, `think`, `rag`, `plan`) from execution (`execute`).
-   Plugin architecture for executors and storage.
-   Strict contract enforcement for AI agent interactions.

## External Dependencies

-   **Python 3.11+**
-   **pytest:** For testing.
-   **pyyaml:** For YAML parsing (implied by Python ecosystem, though not explicitly tied to a core feature in the overview).
-   **OpenWebUI:** Integration is provided via an HTTP backend, exposing specific tools.
-   **Git:** Utilized for `git-backed workspaces`, performing operations like clone, pull, commit, and push.