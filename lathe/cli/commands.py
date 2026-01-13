from lathe.storage.db import LatheDB
from lathe.core.orchestrator import Orchestrator


def list_tasks(db: LatheDB) -> None:
    tasks = db.list_tasks()
    if not tasks:
        print("No tasks found.")
        return

    for task in tasks:
        print(f"- {task['id']} | {task['goal']} | {task['created_at']}")


def show_task(db: LatheDB, task_id: str) -> None:
    task = db.get_task(task_id)
    if not task:
        print(f"Task not found: {task_id}")
        return

    runs = db.list_runs(task_id)

    print("Task:")
    for k, v in task.items():
        print(f"  {k}: {v}")

    print("\nRuns:")
    if not runs:
        print("  (no runs yet)")
        return

    for r in runs:
        print(f"  Run {r['run_id']} | success={r['success']} | {r['completed_at']}")


def show_run(db: LatheDB, run_id: int) -> None:
    run = db.get_run(run_id)
    if not run:
        print(f"Run not found: {run_id}")
        return

    print("Run:")
    for k, v in run.items():
        print(f"  {k}: {v}")


def replay_task(db: LatheDB, orchestrator: Orchestrator, task_id: str) -> None:
    task = db.load_task_spec(task_id)
    if not task:
        print(f"Task not found: {task_id}")
        return

    print(f"Replaying task: {task_id}")
    result = orchestrator.run_task(task)

    print("Replay complete")
    print("Success:", result.success)
    print("Summary:", result.summary)