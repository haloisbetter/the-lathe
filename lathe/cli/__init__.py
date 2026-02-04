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

    # Ledger command
    ledger_parser = subparsers.add_parser("ledger", help="Folder context ledger system")
    ledger_subparsers = ledger_parser.add_subparsers(dest="ledger_command")
    ledger_show = ledger_subparsers.add_parser("show", help="Show the resolved ledger content")
    ledger_show.add_argument("path", nargs="?", default=".", help="Path to check for ledger")

    # Exec command
    exec_parser = subparsers.add_parser("exec", help="Safe command runner")
    exec_parser.add_argument("--cwd", default=".", help="Working directory")
    exec_parser.add_argument("--why", required=True, help="Path to WHY JSON file or inline JSON string")
    exec_parser.add_argument("--timeout", type=int, default=60, help="Execution timeout in seconds")
    exec_parser.add_argument("cmd_args", nargs=argparse.REMAINDER, help="Command and arguments")

    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Controlled patch application system")
    apply_parser.add_argument("--why", required=True, help="Path to WHY JSON file or inline JSON string")
    apply_parser.add_argument("--patch", required=True, help="Path to patch file")

    # Step 1: Repo search command
    repo_parser = subparsers.add_parser("repo", help="Repository awareness commands")
    repo_subparsers = repo_parser.add_subparsers(dest="repo_command")
    search_parser = repo_subparsers.add_parser("search", help="Search the repository")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--path", default=".", help="Root path to search")

    # Step 2: Context get command
    context_parser = subparsers.add_parser("context", help="Deterministic context retrieval")
    context_subparsers = context_parser.add_subparsers(dest="context_command")
    get_parser = context_subparsers.add_parser("get", help="Retrieve exact code context")
    get_parser.add_argument("path_spec", help="File path and line range (path:start-end)")

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
            ensure_ledger(args.path)
            print(read_ledger(args.path))
            return
        else:
            ledger_parser.print_help()
            return

    if args.command == "repo" and args.repo_command == "search":
        from lathe.repo import search_repo
        results = search_repo(args.query, args.path)
        if not results:
            print("No matches found.")
        else:
            for res in results:
                print(f"{res['path']}:{res['line']} | {res['snippet']}")
        return

    if args.command == "context" and args.context_command == "get":
        from lathe.context import get_file_context
        try:
            result = get_file_context(args.path_spec)
            print(f"--- File: {result['path']} ---")
            print(f"--- Hash: {result['hash']} ---")
            for line_num, content in result['lines']:
                print(f"{line_num:4} | {content}")
        except Exception as e:
            print(f"Error: {e}")
        return

    if args.command == "exec":
        from lathe.exec import run_safe_command, validate_why_input
        from lathe.ledger import append_recent_work, append_failed_attempt
        
        actual_cmd = args.cmd_args
        if actual_cmd and actual_cmd[0] == '--':
            actual_cmd = actual_cmd[1:]
        
        if not actual_cmd:
            print("Error: No command specified.")
            sys.exit(1)

        try:
            why_data = validate_why_input(args.why)
        except Exception as e:
            print(f"WHY Validation Failed: {e}")
            sys.exit(1)

        result = run_safe_command(args.cwd, actual_cmd, timeout=args.timeout)
        
        # Auto-update ledger
        cmd_str = " ".join(actual_cmd)
        summary = f"Executed command: {cmd_str}"
        res_str = f"Exit code {result.exit_code}"
        if result.timeout_flag:
            res_str += " (Timed out)"
            
        if result.exit_code == 0:
            append_recent_work(args.cwd, summary, why_data.get("goal", ""), cmd_str, res_str)
        else:
            append_failed_attempt(args.cwd, summary, why_data.get("goal", ""), cmd_str, res_str)

        print("--- Execution Report ---")
        print(f"Command: {cmd_str}")
        print(f"CWD: {Path(args.cwd).resolve()}")
        print(f"Exit Code: {result.exit_code}")
        print(f"Timeout: {result.timeout_flag}")
        print("\nSTDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        return

    if args.command == "apply":
        from lathe.exec import validate_why_input
        from lathe.patch import validate_patch, apply_patch
        
        try:
            why_data = validate_why_input(args.why)
        except Exception as e:
            print(f"WHY Validation Failed: {e}")
            sys.exit(1)
            
        patch_path = Path(args.patch)
        if not patch_path.exists():
            print(f"Error: Patch file not found: {args.patch}")
            sys.exit(1)
            
        patch_content = patch_path.read_text()
        try:
            target_files = validate_patch(patch_content)
        except Exception as e:
            print(f"Patch Validation Failed: {e}")
            sys.exit(1)
            
        print("--- Patch Preview ---")
        print(patch_content)
        print("\nTarget Files:")
        for f in target_files:
            print(f"  - {f}")
            
        confirm = input("\nApply this patch? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
            
        success, output = apply_patch(patch_path, why_data)
        print("\n--- Patch Result ---")
        print("Success:", success)
        print("Output:")
        print(output)
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
