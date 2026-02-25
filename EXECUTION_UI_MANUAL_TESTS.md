# Execution UI Manual Test Instructions

## Overview

This document provides step-by-step instructions to test the enterprise-grade operator timeline, live execution streaming, and async execution service.

## Prerequisites

- Python 3.8+
- The Lathe repository cloned
- Virtual environment activated

## Setup

```bash
cd /mnt/c/Users/somet/projects/the-lathe
source .venv/bin/activate
```

## Test Steps

### Step 1: Start the Server

In Terminal 1:

```bash
cd /mnt/c/Users/somet/projects/the-lathe
source .venv/bin/activate
python -m lathe_app.server
```

You should see:
```
Lathe App Server listening on 0.0.0.0:3001
Execution worker started
```

### Step 2: Create a Workspace

In Terminal 2:

```bash
cd /mnt/c/Users/somet/projects/the-lathe
source .venv/bin/activate

# Create a test workspace
mkdir -p /tmp/test-lathe-ws
touch /tmp/test-lathe-ws/hello.py
echo "x = 1" > /tmp/test-lathe-ws/hello.py

# Register workspace with Lathe
curl -s -X POST http://localhost:3001/workspace/create \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test-lathe-ws"}' | jq .
```

Expected output:
```json
{
  "workspace": {
    "name": "test-lathe-ws",
    "root_path": "/tmp/test-lathe-ws",
    ...
  },
  "results": []
}
```

### Step 3: Create a Propose Run

```bash
RESPONSE=$(curl -s -X POST http://localhost:3001/agent \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "propose",
    "task": "List Python files in the workspace",
    "why": {
      "goal": "test execution service",
      "context": "manual test"
    }
  }')

RUN_ID=$(echo "$RESPONSE" | jq -r '.id')
echo "Run ID: $RUN_ID"
echo "$RESPONSE" | jq .
```

Expected output:
- `Run ID: run-<uuid>`
- Full run record with proposals

### Step 4: Approve the Run

```bash
curl -s -X POST http://localhost:3001/review \
  -H "Content-Type: application/json" \
  -d "{\"run_id\": \"$RUN_ID\", \"action\": \"approve\"}" | jq .
```

Expected output:
```json
{
  "success": true,
  "run_id": "run-...",
  "previous_state": "PROPOSED",
  "new_state": "APPROVED"
}
```

### Step 5: Check Review State (Before Executing)

```bash
curl -s http://localhost:3001/runs/$RUN_ID/review | jq .
```

Expected output:
```json
{
  "state": "APPROVED",
  "results": []
}
```

### Step 6: Check Execution Status (Before Executing)

```bash
curl -s http://localhost:3001/runs/$RUN_ID/execute | jq .
```

Expected output:
```json
{
  "error_type": "not_found",
  "message": "No execution jobs found for run ...",
  ...
}
```

### Step 7: Execute the Run (Async Queue)

```bash
EXECUTE_RESPONSE=$(curl -s -X POST http://localhost:3001/runs/$RUN_ID/execute)
JOB_ID=$(echo "$EXECUTE_RESPONSE" | jq -r '.job_id')
echo "Job ID: $JOB_ID"
echo "$EXECUTE_RESPONSE" | jq .
```

Expected output:
```json
{
  "ok": true,
  "run_id": "run-...",
  "job_id": "job-...",
  "status": "queued",
  "results": []
}
```

### Step 8: Poll Job Status (Live Execution)

In a new terminal:

```bash
cd /mnt/c/Users/somet/projects/the-lathe

# Monitor job status as it progresses
for i in {1..10}; do
  echo "=== Poll $i ==="
  curl -s http://localhost:3001/jobs/$JOB_ID | jq '.status, .trace_count'
  sleep 1
done
```

Expected progression:
1. `queued` → `trace_count: 0`
2. `running` → `trace_count: 0` or `trace_count: 1`
3. `succeeded` → `trace_count: 1+`

### Step 9: View Tool Traces (Execution History)

```bash
curl -s http://localhost:3001/runs/$RUN_ID/tool_traces | jq .
```

Expected output:
```json
{
  "run_id": "run-...",
  "count": 1,
  "traces": [
    {
      "tool_id": "fs_stats",
      "started_at": "2026-...",
      "finished_at": "2026-...",
      "ok": true,
      "inputs": {"workspace": "test-lathe-ws"},
      "output": {
        "total_files": 1,
        ...
      }
    }
  ],
  "results": []
}
```

### Step 10: Get Full Job Detail

```bash
curl -s http://localhost:3001/jobs/$JOB_ID | jq .
```

Expected output:
```json
{
  "id": "job-...",
  "run_id": "run-...",
  "status": "succeeded",
  "created_at": "2026-...",
  "started_at": "2026-...",
  "finished_at": "2026-...",
  "error": null,
  "tool_traces": [
    {
      "tool_id": "fs_stats",
      "started_at": "2026-...",
      ...
    }
  ]
}
```

### Step 11: Verify Idempotency (409 on Second Execute)

```bash
# Try to execute again
curl -s -X POST http://localhost:3001/runs/$RUN_ID/execute | jq '.error'
```

Expected output:
```json
"already_executing"
```

(With HTTP status 409 Conflict)

### Step 12: Test TUI Live Timeline (Optional)

In Terminal 3:

```bash
cd /mnt/c/Users/somet/projects/the-lathe
source .venv/bin/activate
python -m lathe_tui.app.tui
```

Then in the TUI:
1. Tab → Replay mode
2. Select the run from the left panel
3. Observe:
   - Timeline showing: `[Proposed] → [Approved] → [Queued] → [Succeeded]`
   - History strip with timestamps
   - Execution trace panel with tool calls

## Expected Behaviors

### Timeline States

The timeline should progress through these states (color-coded):

```
[Proposed] (dim)
    ↓
[APPROVED] (blue)
    ↓
[queued] (yellow)
    ↓
[running] (yellow)
    ↓
[succeeded] (green) OR [failed] (red)
```

### History Strip

Should display:
- Proposed timestamp
- Approved timestamp (once approved)
- Executed timestamp (once executed)
- Outcome (succeeded/failed)
- Model used

### Execution Trace Panel

Should show:
- Tool ID
- Status badge (✓ for success, ✗ for failure)
- Duration in milliseconds
- Inputs and outputs
- Error reason if failed
- Auto-scrolling as new traces arrive

### Polling Behavior

- Running: poll every 0.5 seconds
- Queued > 5s: poll every 1 second
- Queued > 15s: poll every 2 seconds
- Terminal state: stop polling

### Idempotency

- First execute: returns job_id and status=queued
- Second execute (same run, while queued/running): returns 409 error
- Execute on non-approved run: returns 409 error "run_not_approved"
- Execute on non-existent run: returns 404 error "run_not_found"

## Debugging

### Check Server Logs

Terminal 1 shows:
- Worker picking up jobs
- Tool execution
- Trace recording

Example:
```
Execution worker started
Worker picked up job job-abc for run run-xyz
Worker finished job job-abc status=succeeded
```

### Check Database

Jobs and traces are persisted in SQLite:

```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect(os.path.expanduser("~/.lathe/execution.db"))
cursor = conn.cursor()
cursor.execute("SELECT id, run_id, status FROM execution_jobs LIMIT 5")
for row in cursor.fetchall():
    print(row)
EOF
```

### Monitor Worker

In Terminal 2, watch worker logs:

```bash
tail -f /tmp/lathe_worker.log  # if logging is configured
```

## Test Summary Checklist

- [ ] Server starts without errors
- [ ] Workspace created successfully
- [ ] Propose run created
- [ ] Run approved
- [ ] Execute returns queued job
- [ ] Job progresses to succeeded
- [ ] Traces recorded with correct data
- [ ] Idempotency guard returns 409 on second execute
- [ ] Full job detail accessible
- [ ] Tool traces append-only (no duplicates)
- [ ] TUI timeline displays correct state progression
- [ ] TUI history strip shows timestamps
- [ ] TUI trace panel auto-scrolls
- [ ] Polling stops when job reaches terminal state

## Cleanup

```bash
rm -rf /tmp/test-lathe-ws
rm ~/.lathe/execution.db  # Optional: reset execution state
```

---

**Test Date:** _____________

**Tester:** _____________

**Notes:** _____________
