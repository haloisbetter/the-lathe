CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    scope TEXT NOT NULL,
    constraints TEXT NOT NULL,
    inputs TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    task_id TEXT PRIMARY KEY,
    success INTEGER NOT NULL,
    summary TEXT NOT NULL,
    files_changed TEXT NOT NULL,
    commands_run TEXT NOT NULL,
    artifacts TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);