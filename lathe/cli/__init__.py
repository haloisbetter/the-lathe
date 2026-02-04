import argparse
import sys
from pathlib import Path

def bootstrap():
    from lathe.config import ConfigLoader
    from lathe.logging import setup_logging, get_logger
    from lathe.storage.db import LatheDB
    from lathe.bootstrap.openhands import OpenHandsExecutor
    from lathe.core.orchestrator import Orchestrator

    config = ConfigLoader.load()
    setup_logging(
        level=config.logging.level,
        format_str=config.logging.format,
        log_file=config.logging.file,
    )
    db = LatheDB(Path(config.database.path))
    executor = OpenHandsExecutor()
    orchestrator = Orchestrator(executor, db)
    return orchestrator, db, get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="The Lathe CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    subparsers.add_parser("init-config", help="Create lathe.yml example")
    subparsers.add_parser("list", help="List all tasks")
    show_parser = subparsers.add_parser("show", help="Show task details")
    show_parser.add_argument("id", help="Task ID")
    run_parser = subparsers.add_parser("run", help="Show run details")
    run_parser.add_argument("id", type=int, help="Run ID")
    replay_parser = subparsers.add_parser("replay", help="Replay a task")
    replay_parser.add_argument("id", help="Task ID")
    why_parser = subparsers.add_parser("why", help="WHY engine commands")
    why_subparsers = why_parser.add_subparsers(dest="why_command")
    why_subparsers.add_parser("example", help="Print a sample WHY record")

    args = parser.parse_args()

    if args.command == "init-config":
        from lathe.config import ConfigLoader
        path = Path("lathe.yml")
        ConfigLoader.save_example(path)
        print(f"Created example configuration at {path}")
        return

    if args.command == "why" and args.why_command == "example":
        from lathe.why import get_why_example
        print(get_why_example())
        return

    orchestrator, db, logger = bootstrap()

    from lathe.cli.commands import list_tasks, show_task, show_run, replay_task

    if args.command == "list":
        list_tasks(db)
    elif args.command == "show":
        show_task(db, args.id)
    elif args.command == "run":
        show_run(db, args.id)
    elif args.command == "replay":
        replay_task(db, orchestrator, args.id)
    elif args.command == "why":
        why_parser.print_help()
    elif args.command is None:
        from lathe.core.task import TaskSpec
        logger.info("Running default task")
        task = TaskSpec(id="lathe-smoke-005", goal="Verify multi-run history", scope="bootstrap", constraints={}, inputs={})
        result = orchestrator.run_task(task)
        print(f"Task executed, run recorded. Success: {result.success}")
    else:
        parser.print_help()
