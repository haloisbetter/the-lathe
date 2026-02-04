# The Lathe

A local-first orchestrator that builds software systems by executing constrained tasks through agents.

## Overview

The Lathe is a deterministic, inspectable, and replaceable system for AI-driven software development. It orchestrates what to build, while delegating how to build to pluggable executor agents.

## Project Type

This is a **Python CLI application** (no web frontend).

## Running the Application

```bash
# Run default task
python -m lathe.main

# Initialize configuration
python -m lathe.main init-config

# List all tasks
python -m lathe.main list

# Show task details
python -m lathe.main show <task_id>

# Show run details
python -m lathe.main run <run_id>

# Replay a task
python -m lathe.main replay <task_id>
```

## Development Commands

```bash
# Run tests
pytest -q

# or via Makefile
make check
```

## Project Structure

```
lathe/
├── core/           # Task orchestration and execution pipeline
├── storage/        # SQLite-based persistence layer
├── bootstrap/      # Temporary external agent integrations
├── config/         # Configuration loading and validation
├── logging/        # Logging setup and utilities
└── cli/            # Command-line interface
```

## Configuration

Copy `lathe.example.yml` to `lathe.yml` and customize settings for database path, logging, and executor type.

## Requirements

- Python 3.11+
- pytest
- pyyaml
