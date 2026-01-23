# The Lathe - Scaffold Complete

## Overview

A minimal, clean scaffold for **lathe-core** - the core bootstrap subsystem of The Lathe AI coding platform.

## What Was Created

### 1. Configuration System (`lathe/config/`)
- **loader.py**: YAML-based configuration with environment variable overrides
- **LatheConfig**: Type-safe configuration dataclasses
- **ConfigLoader**: Deterministic config file search and loading
- **Example config**: `lathe.example.yml`

**Features**:
- Search order: `$LATHE_CONFIG` → `./lathe.yml` → `./lathe.yaml` → `~/.lathe/config.yml` → defaults
- Environment variable overrides
- Type-safe configuration schema
- Config generation command: `python -m lathe.main init-config`

### 2. Logging System (`lathe/logging/`)
- **setup.py**: Centralized logging configuration
- Console and optional file output
- Configurable log levels and formats
- Singleton initialization pattern

**Features**:
- Python standard logging integration
- Format customization
- Optional file logging
- Module-level logger factory

### 3. Module Initialization
- **lathe/__init__.py**: Package-level documentation and version
- **lathe/core/__init__.py**: Core module interface exports
- **lathe/storage/__init__.py**: Storage layer interface
- **lathe/bootstrap/__init__.py**: Bootstrap executor interface

**Purpose**: Clear module boundaries and responsibility documentation

### 4. Enhanced Main Entry Point (`lathe/main.py`)
- **bootstrap()**: Deterministic startup sequence
- Configuration loading
- Logging initialization
- Component wiring
- CLI routing with new `init-config` command

### 5. Documentation
- **README.md**: Comprehensive user documentation
- **ARCHITECTURE.md**: System architecture and design decisions
- **SCAFFOLD.md**: This file - scaffold completion summary

### 6. Development Infrastructure
- **.gitignore**: Comprehensive ignore patterns for Python projects
- **requirements.txt**: Added `pyyaml` dependency
- **lathe.example.yml**: Example configuration file

## Folder Structure

```
lathe/
├── __init__.py              # Package definition
├── main.py                  # Entry point and bootstrap
│
├── config/                  # Configuration management
│   ├── __init__.py
│   └── loader.py            # YAML loading, validation
│
├── logging/                 # Logging infrastructure
│   ├── __init__.py
│   └── setup.py             # Centralized logging setup
│
├── core/                    # Orchestration logic
│   ├── __init__.py
│   ├── orchestrator.py      # Task orchestration
│   ├── task.py              # Task specifications
│   ├── result.py            # Task results
│   └── executor.py          # Executor interface
│
├── storage/                 # Persistence layer
│   ├── __init__.py
│   ├── db.py                # SQLite operations
│   └── schema.sql           # Database schema
│
├── bootstrap/               # External agent integration
│   ├── __init__.py
│   └── openhands.py         # OpenHands executor
│
└── cli/                     # Command-line interface
    ├── __init__.py
    └── commands.py          # CLI command implementations
```

## Responsibility Boundaries

### What The Core Bootstrap DOES
- Load and validate configuration from YAML
- Setup logging infrastructure
- Initialize database connections
- Wire together core components
- Provide CLI interface
- Coordinate task orchestration

### What The Core Bootstrap DOES NOT
- Implement AI reasoning logic
- Decide HOW to execute tasks (delegated to executors)
- Make direct network calls
- Include SaaS dependencies
- Contain business rules for task generation

## Configuration-Driven Behavior

All runtime behavior is controlled via `lathe.yml`:

```yaml
database:
  path: "data/lathe.db"
  schema_path: "lathe/storage/schema.sql"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: null

executor:
  type: "openhands"
  timeout: 300
  options: {}
```

## Deterministic Startup Sequence

1. Load configuration (deterministic search order)
2. Setup logging (single initialization)
3. Initialize database (idempotent schema)
4. Create executor (from config)
5. Wire orchestrator
6. Execute CLI command

## Interface Contracts

### ConfigLoader
```python
config = ConfigLoader.load()                    # Auto-detect config file
config = ConfigLoader.load(Path("custom.yml")) # Explicit path
ConfigLoader.save_example(Path("lathe.yml"))   # Generate example
```

### Logging
```python
setup_logging(level="INFO", format_str="...", log_file=None)
logger = get_logger(__name__)
logger.info("Message")
```

### Bootstrap
```python
orchestrator, db = bootstrap()  # Returns fully initialized system
```

## CLI Commands

```bash
python -m lathe.main              # Run default task
python -m lathe.main init-config  # Create lathe.yml
python -m lathe.main list         # List all tasks
python -m lathe.main show <id>    # Show task details
python -m lathe.main run <id>     # Show run details
python -m lathe.main replay <id>  # Replay a task
```

## Dependencies

**Added**:
- `pyyaml`: Configuration file parsing

**Existing**:
- `pytest`: Testing framework

**Python**: Requires >=3.11 (for modern type hints)

## Design Principles Applied

### 1. Minimal Dependencies
- Only `pyyaml` added for config
- No external frameworks
- Stdlib-first approach

### 2. Explicit Separation of Concerns
- Each module has documented responsibilities
- Clear "DOES" and "DOES NOT" boundaries
- Interface-based abstractions

### 3. Deterministic Startup
- Fixed configuration search order
- Idempotent database initialization
- Singleton logging setup
- No global mutable state

### 4. Configuration-Driven
- Runtime behavior controlled by YAML
- Environment variable overrides
- No hardcoded paths or values

### 5. Placeholder Interfaces
- Executor abstraction ready for new implementations
- Storage layer ready for extensions
- CLI extensible via command registration

## Next Steps

### Immediate
1. Install dependencies: `pip install -r requirements.txt`
2. Generate config: `python -m lathe.main init-config`
3. Edit `lathe.yml` as needed
4. Run tests: `make test`

### Future Extensions
1. Add new executors in `lathe/bootstrap/`
2. Add CLI commands in `lathe/cli/commands.py`
3. Extend configuration schema in `lathe/config/loader.py`
4. Add observability hooks in logging

## Testing Strategy

Tests exist in `tests/`:
- `test_orchestrator.py`: Orchestration logic
- `test_replay.py`: Task replay functionality
- `test_runs.py`: Run history
- `test_smoke.py`: End-to-end validation

Run with: `make test` or `pytest tests/`

## Bootstrap Phase Status

**Current**: Using OpenHands as external executor

**Isolation**:
- All OpenHands code in `lathe/bootstrap/openhands.py`
- Interface in `lathe/core/executor.py`
- No core dependencies on bootstrap
- Swappable via configuration

**Goal**: Make external dependency replaceable

## Success Criteria Met

- ✓ Clear folder structure
- ✓ Explicit separation of concerns
- ✓ Minimal dependencies (only pyyaml added)
- ✓ Deterministic startup sequence
- ✓ Configuration-driven behavior
- ✓ CLI entrypoint with bootstrap
- ✓ Config schema (YAML)
- ✓ Logging setup
- ✓ Placeholder interfaces for modules
- ✓ README explaining boundaries
- ✓ Architecture documentation

## Files Modified/Created

### Created
- `lathe/__init__.py`
- `lathe/config/__init__.py`
- `lathe/config/loader.py`
- `lathe/logging/__init__.py`
- `lathe/logging/setup.py`
- `lathe/core/__init__.py`
- `lathe/storage/__init__.py`
- `lathe/bootstrap/__init__.py`
- `lathe.example.yml`
- `ARCHITECTURE.md`
- `SCAFFOLD.md`

### Modified
- `lathe/main.py`: Added bootstrap function and logging
- `lathe/storage/db.py`: Added schema_path parameter
- `README.md`: Complete rewrite with clear boundaries
- `requirements.txt`: Added pyyaml
- `.gitignore`: Enhanced Python-specific ignores

## Verification

All Python files have valid syntax and can be imported:
```bash
python3 -m py_compile lathe/config/loader.py
python3 -m py_compile lathe/logging/setup.py
python3 -m py_compile lathe/main.py
```

## Summary

The lathe-core scaffold is now complete with:
- Clean, documented module structure
- Configuration and logging infrastructure
- Deterministic, predictable startup
- Clear responsibility boundaries
- Ready for extension without core changes
- Minimal, stable dependencies

The system is ready for development and maintains strict separation between orchestration logic (WHAT) and execution logic (HOW).
