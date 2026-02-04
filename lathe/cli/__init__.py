import argparse
import sys
import json
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

    # Step 1: Ledger command
    ledger_parser = subparsers.add_parser("ledger", help="Folder context ledger system")
    ledger_subparsers = ledger_parser.add_subparsers(dest="ledger_command")
    ledger_show = ledger_subparsers.add_parser("show", help="Show the resolved ledger content")
    ledger_show.add_argument("path", nargs="?", default=".", help="Path to check for ledger")

    # Step 2: Exec command
    exec_parser = subparsers.add_parser("exec", help="Safe command runner")
    exec_parser.add_argument("--cwd", default=".", help="Working directory")
    exec_parser.add_argument("--why", required=True, help="Path to WHY JSON file or inline JSON string")
    exec_parser.add_argument("--timeout", type=int, default=60, help="Execution timeout in seconds")
    exec_parser.add_argument("cmd_args", nargs=argparse.REMAINDER, help="Command and arguments")

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

    if args.command == "ledger":
        from lathe.ledger import read_ledger, ensure_ledger
        if args.ledger_command == "show":
            # Ensure it exists or just read the nearest
            ensure_ledger(args.path)
            print(read_ledger(args.path))
            return
        else:
            ledger_parser.print_help()
            return

    if args.command == "exec":
        from lathe.exec import run_safe_command, validate_why_input
        # Remove '--' if present in cmd_args (argparse.REMAINDER might include it)
        actual_cmd = args.cmd_args
        if actual_cmd and actual_cmd[0] == '--':
            actual_cmd = actual_cmd[1:]
        
        if not actual_cmd:
            print("Error: No command specified.")
            sys.exit(1)

        try:
            validate_why_input(args.why)
        except Exception as e:
            print(f"WHY Validation Failed: {e}")
            sys.exit(1)

        result = run_safe_command(args.cwd, actual_cmd, timeout=args.timeout)
        print("--- Execution Report ---")
        print(f"Command: {' '.join(actual_cmd)}")
        print(f"CWD: {Path(args.cwd).resolve()}")
        print(f"Exit Code: {result.exit_code}")
        print(f"Timeout: {result.timeout_flag}")
        print("\nSTDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
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
