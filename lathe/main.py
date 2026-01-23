"""
The Lathe - Main Entry Point

Bootstraps the application, loads configuration, and runs the CLI.
"""

import sys
from pathlib import Path

from lathe.config import ConfigLoader
from lathe.logging import setup_logging, get_logger
from lathe.core import TaskSpec, Orchestrator
from lathe.bootstrap import OpenHandsExecutor
from lathe.storage import LatheDB
from lathe.cli.commands import (
    list_tasks,
    show_task,
    show_run,
    replay_task,
)


def bootstrap() -> tuple[Orchestrator, LatheDB]:
    """
    Bootstrap The Lathe system.

    Loads configuration, sets up logging, and initializes core components.

    Returns:
        Tuple of (Orchestrator, LatheDB) ready for use
    """
    config = ConfigLoader.load()

    setup_logging(
        level=config.logging.level,
        format_str=config.logging.format,
        log_file=config.logging.file,
    )

    logger = get_logger(__name__)
    logger.info("Starting The Lathe")
    logger.debug(f"Database path: {config.database.path}")

    db = LatheDB(Path(config.database.path))
    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor, db)

    logger.info("Bootstrap complete")

    return orchestrator, db


def main() -> None:
    """Main entry point for The Lathe CLI."""
    orchestrator, db = bootstrap()
    logger = get_logger(__name__)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "list":
            list_tasks(db)
            return

        if cmd == "show" and len(sys.argv) == 3:
            show_task(db, sys.argv[2])
            return

        if cmd == "run" and len(sys.argv) == 3:
            show_run(db, int(sys.argv[2]))
            return

        if cmd == "replay" and len(sys.argv) == 3:
            replay_task(db, orchestrator, sys.argv[2])
            return

        if cmd == "init-config":
            path = Path("lathe.yml")
            ConfigLoader.save_example(path)
            print(f"Created example configuration at {path}")
            return

        print("Usage:")
        print("  python -m lathe.main              # Run default task")
        print("  python -m lathe.main init-config  # Create lathe.yml")
        print("  python -m lathe.main list         # List all tasks")
        print("  python -m lathe.main show <id>    # Show task details")
        print("  python -m lathe.main run <id>     # Show run details")
        print("  python -m lathe.main replay <id>  # Replay a task")
        return

    logger.info("Running default task")

    task = TaskSpec(
        id="lathe-smoke-005",
        goal="Verify multi-run history",
        scope="bootstrap",
        constraints={},
        inputs={},
    )

    result = orchestrator.run_task(task)
    print("Task executed, run recorded")
    print("Success:", result.success)