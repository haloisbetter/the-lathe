# The Lathe - Architecture Documentation

## System Overview

The Lathe is a local-first orchestrator for AI-driven software development. It maintains clear separation between orchestration logic (WHAT to build) and execution logic (HOW to build).

## Module Structure

```
lathe/
├── __init__.py              # Package initialization and version
├── main.py                  # Entry point, bootstrap, and CLI routing
│
├── config/                  # Configuration management
│   ├── __init__.py
│   └── loader.py            # YAML config loading with env overrides
│
├── logging/                 # Logging infrastructure
│   ├── __init__.py
│   └── setup.py             # Centralized logging configuration
│
├── core/                    # Core orchestration logic
│   ├── __init__.py
│   ├── orchestrator.py      # Main orchestration loop
│   ├── task.py              # Task specification
│   ├── result.py            # Task result types
│   └── executor.py          # Executor interface
│
├── storage/                 # Persistence layer
│   ├── __init__.py
│   ├── db.py                # SQLite database operations
│   └── schema.sql           # Database schema
│
├── bootstrap/               # External agent integrations (temporary)
│   ├── __init__.py
│   └── openhands.py         # OpenHands executor implementation
│
└── cli/                     # Command-line interface
    ├── __init__.py
    └── commands.py          # CLI command implementations
```

## Responsibility Matrix

| Module | Responsibilities | Does NOT Handle |
|--------|-----------------|-----------------|
| **config** | Load YAML, validate config, env overrides | Business logic, execution |
| **logging** | Setup logging, format configuration | Storage, networking |
| **core** | Task orchestration, executor abstraction | How tasks are executed |
| **storage** | SQLite operations, schema management | Business rules, validation |
| **bootstrap** | External agent integration | Core orchestration |
| **cli** | User interface, command routing | Task execution logic |

## Data Flow

```
User → CLI → Bootstrap → Config/Logging → Orchestrator
                                            ↓
                                         Executor
                                            ↓
                                         Storage
```

1. **User** invokes CLI command
2. **Bootstrap** loads config and initializes logging
3. **Orchestrator** receives task specification
4. **Executor** implements the task (delegated to external agent)
5. **Storage** persists task and run history

## Configuration

### File Locations (Search Order)
1. `$LATHE_CONFIG` environment variable
2. `./lathe.yml`
3. `./lathe.yaml`
4. `~/.lathe/config.yml`
5. Default configuration

### Configuration Schema

```yaml
database:
  path: string           # SQLite database path
  schema_path: string    # Schema file path

logging:
  level: string          # DEBUG|INFO|WARNING|ERROR|CRITICAL
  format: string         # Python logging format string
  file: string?          # Optional log file path

executor:
  type: string           # Executor type (e.g., "openhands")
  timeout: int           # Maximum execution time (seconds)
  options: object        # Executor-specific options
```

## Storage Schema

### tasks table
- `id` (TEXT PRIMARY KEY): Unique task identifier
- `goal` (TEXT): Human-readable task description
- `scope` (TEXT): Task scope/category
- `constraints` (TEXT): JSON-encoded constraints
- `inputs` (TEXT): JSON-encoded inputs
- `created_at` (TEXT): ISO timestamp

### runs table
- `run_id` (INTEGER PRIMARY KEY): Auto-increment run ID
- `task_id` (TEXT): Foreign key to tasks
- `success` (INTEGER): Boolean success flag
- `summary` (TEXT): Execution summary
- `files_changed` (TEXT): JSON-encoded file list
- `commands_run` (TEXT): JSON-encoded command list
- `artifacts` (TEXT): JSON-encoded artifacts
- `completed_at` (TEXT): ISO timestamp

## Extension Points

### Adding a New Executor

1. Create new file in `lathe/bootstrap/`
2. Implement `BootstrapExecutor` interface:
   ```python
   class CustomExecutor(BootstrapExecutor):
       def execute(self, task: TaskSpec) -> TaskResult:
           # Implementation
   ```
3. Register in config and bootstrap function

### Adding a New CLI Command

1. Add function to `lathe/cli/commands.py`:
   ```python
   def my_command(db: LatheDB, arg: str) -> None:
       # Implementation
   ```
2. Register in `lathe/main.py`:
   ```python
   if cmd == "mycommand" and len(sys.argv) == 3:
       my_command(db, sys.argv[2])
       return
   ```

### Adding Configuration Options

1. Add field to appropriate `@dataclass` in `config/loader.py`
2. Update `LatheConfig.from_dict()` method
3. Update example config in `ConfigLoader.save_example()`
4. Update `lathe.example.yml`

## Design Constraints

### Must Have
- All operations must be loggable
- SQLite is the only persistent store
- Configuration-driven behavior
- Clear module boundaries

### Must NOT Have
- AI reasoning logic in core
- Direct network calls in core
- Hard-coded external dependencies
- Global mutable state

## Bootstrap Phase

**Current State**: Using OpenHands as external executor

**Goal**: Make external dependency replaceable

**Isolation Strategy**:
- All OpenHands code in `lathe/bootstrap/`
- Interface defined in `lathe/core/executor.py`
- No direct imports of bootstrap modules in core
- Configuration-controlled executor selection

## Testing Strategy

- **Unit tests**: Test individual modules in isolation
- **Integration tests**: Test orchestrator with mock executor
- **Smoke tests**: End-to-end validation with real executor
- **Replay tests**: Verify determinism by replaying tasks

## Future Considerations

### Phase 2: Self-Hosting
- Replace bootstrap executor with internal implementation
- Remove dependency on external agents
- Maintain same interface and behavior

### Phase 3: Advanced Features
- Parallel task execution
- Task dependencies and DAGs
- Incremental task updates
- Distributed execution

## Principles in Practice

1. **Deterministic**
   - Fixed configuration loading order
   - No random behavior
   - Reproducible task execution

2. **Inspectable**
   - All tasks logged to database
   - Comprehensive logging system
   - Queryable history

3. **Replaceable**
   - Interface-based executors
   - Configuration-driven selection
   - Isolated bootstrap dependencies

4. **Agent-Constrained**
   - Core decides WHAT
   - Executors decide HOW
   - Clear interface boundaries
