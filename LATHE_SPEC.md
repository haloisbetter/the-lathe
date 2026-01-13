# THE LATHE — SYSTEM SPEC (v0.1)

Purpose:
The Lathe is a local-first orchestrator that builds software systems
by executing constrained tasks through agents.

Bootstrap Phase:
- OpenHands is used as an external bootstrap agent
- This dependency is temporary and must be removable

Core Principles:
- Deterministic
- Inspectable
- Replaceable
- Agent-constrained

Rules:
- The Lathe decides WHAT to build
- Bootstrap agents decide HOW (temporarily)
- All actions must be loggable
- SQLite is the only persistent store
- JSON defines tasks and specs

Milestone 1 Goal:
- Establish structure
- Define bootstrap boundary
- Runnable CLI