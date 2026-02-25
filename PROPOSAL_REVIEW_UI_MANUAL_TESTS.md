# Proposal Review UI Manual Test Instructions

## Overview

This document provides step-by-step instructions to test the structured proposal review interface with risk badges, change metrics, and diff previews.

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

Expected output:
```
Lathe App Server listening on 0.0.0.0:3001
Execution worker started
```

### Step 2: Create a Test Workspace

In Terminal 2:

```bash
cd /mnt/c/Users/somet/projects/the-lathe

# Create test directory
mkdir -p /tmp/test-proposal-ws
cat > /tmp/test-proposal-ws/config.py << 'EOF'
# Configuration file
DEBUG = False
LOG_LEVEL = "INFO"
EOF

# Register with Lathe
curl -s -X POST http://localhost:3001/workspace/create \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test-proposal-ws"}' | jq .
```

Expected output:
```json
{
  "workspace": {
    "name": "test-proposal-ws",
    "root_path": "/tmp/test-proposal-ws",
    ...
  }
}
```

### Step 3: Generate Proposal with Write Operations

```bash
# Create proposal that will write to files
RESPONSE=$(curl -s -X POST http://localhost:3001/agent \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "propose",
    "task": "Update configuration and add logging",
    "why": {
      "goal": "test proposal review UI",
      "context": "manual testing"
    }
  }')

RUN_ID=$(echo "$RESPONSE" | jq -r '.id')
echo "Run ID: $RUN_ID"
echo "$RESPONSE" | jq '.output | {proposals, change_summary}' 2>/dev/null || echo "$RESPONSE" | jq '.'
```

Expected output:
- Run ID returned (e.g., "run-abc123...")
- Proposal artifact with write operations

### Step 4: Check Proposal Before TUI

```bash
# Get full run details
curl -s http://localhost:3001/runs/$RUN_ID | jq '.output | {proposals: (.proposals | length), risks, assumptions}' 2>/dev/null || true

# Get proposal output
curl -s http://localhost:3001/runs/$RUN_ID | jq '.output.proposals[0] | {action, target}' 2>/dev/null | head -10
```

Expected output:
- Proposals count
- Risk factors
- Assumptions
- First proposal action and target

### Step 5: Start TUI (Replay Mode)

In Terminal 3:

```bash
cd /mnt/c/Users/somet/projects/the-lathe
source .venv/bin/activate
python -m lathe_tui.app.tui
```

You should see the TUI startup with:
- Header showing "The Lathe"
- Replay screen with runs list on left

### Step 6: Navigate to Proposal Run

In the TUI:

1. Press `Tab` to switch to **Replay** mode (if not already there)
2. Look at the left panel (runs list)
3. Find your run (contains "Update configuration" or the intent you used)
4. Press `Enter` or `↓` to select it

Expected UI state:
- Left panel shows list of runs
- Your run highlighted
- Right panel begins loading run details

### Step 7: Verify Risk Badge Display

In the right panel, scroll down to find:

**PROPOSAL REVIEW section should show:**

```
RISK BADGE: [MEDIUM RISK] or [HIGH RISK] (color-coded)
- Marked with yellow or red depending on operations
- Text color matches risk level

Risk Factors:
  • Proposes write operation
  • (Other factors if applicable)

Affected Files:
  • config.py
  • (Other files if modified)

Files: X | +Y / -Z lines
- Shows change metrics
- Example: "Files: 1 | +5 / -2 lines"
```

### Step 8: Verify Change Metrics

In the same panel:

**CHANGE METRICS header shows:**

```
Files: 1 | +5 / -2 lines
```

Where:
- `1` = files changed
- `+5` = lines added
- `-2` = lines removed

Or if read-only:

```
No file modifications proposed
```

### Step 9: Verify Proposed Changes (Diff)

Continue scrolling in the right panel to see:

**PROPOSED CHANGES section:**

```
PROPOSED CHANGES
━━━━━━━━━━━━━━━━━
--- a/config.py
+++ b/config.py
- DEBUG = False
+ DEBUG = True
+ VERBOSE = True
... (additional diff lines)
```

Features to verify:
- Unified diff format (-, +, file names)
- Indentation preserved
- Multiple changes shown
- If large diff: truncation message shown

### Step 10: Test Idempotency (No Duplicate Mounts)

In the TUI:

1. Press `r` (refresh runs)
2. Select the same run again
3. Verify the proposal review section appears **without duplication**
4. Risk badge, metrics, and diff should render cleanly

Expected behavior:
- No error messages
- No doubled widgets
- Smooth refresh

### Step 11: Test Different Risk Levels

Create additional proposals to test different risk levels:

**For LOW RISK proposal (read-only):**

```bash
curl -s -X POST http://localhost:3001/agent \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "propose",
    "task": "Analyze workspace structure",
    "why": {"goal": "test low risk", "context": "readonly"}
  }' | jq -r '.id' > /tmp/low_risk_run.txt

RUN_ID=$(cat /tmp/low_risk_run.txt)
```

In TUI:
- Select this run
- Observe: `[LOW RISK]` badge in green (#879A39)
- Message: "No file modifications proposed"

**For HIGH RISK proposal (if system supports trust escalation):**

Check if your proposal includes trust_required flags:

In TUI:
- Select run with trust requirements
- Observe: `[HIGH RISK]` badge in red (#D14D41)
- Risk factors mention trust requirement

### Step 12: Test Diff Truncation

Create a proposal with many changes:

```bash
# Create large change proposal (if your system supports it)
# Or manually craft one via API with large content
```

In TUI:
- If diff > 300 lines, observe:
  ```
  [... diff truncated at 300 lines ...]
  ```
- Truncation message appears at bottom

### Step 13: Verify Color Coding

In the proposal review section, confirm colors:

| Risk Level | Color | Code |
|-----------|-------|------|
| LOW | Green | #879A39 |
| MEDIUM | Yellow | #D0A215 |
| HIGH | Red | #D14D41 |

Text should be visible and readable on the dark background.

### Step 14: Test With Multiple Files

If possible, create a proposal affecting multiple files:

Expected in UI:
```
Affected Files:
  • config.py
  • settings.json
  • utils.py
  ... and 2 more
```

Files list shows up to 10, then "... and X more" message.

### Step 15: Verify No Kernel Changes

Confirm that this feature:
- ✅ Does not modify `/tmp/cc-agent/62910883/project/lathe/` directory
- ✅ Only changes TUI and app layers
- ✅ All tests still pass

Run verification:

```bash
python3 -m pytest tests/ -q --ignore=tests/cli --ignore=tests/tui/test_client.py
# Should see: 755 passed
```

---

## Expected Behaviors Checklist

### Risk Badge
- [ ] Appears below proposal list
- [ ] Color matches risk level (green/yellow/red)
- [ ] Text readable
- [ ] Only one badge per run (no duplicates on refresh)

### Risk Factors
- [ ] "Proposes write operation" shown for writes
- [ ] "Trust required for this operation" shown if applicable
- [ ] "Trust requirement satisfied" shown if met
- [ ] Limited to first 5 reasons

### Change Metrics
- [ ] Shows "Files: X" count
- [ ] Shows "+Y" lines added (green)
- [ ] Shows "-Z" lines removed (red)
- [ ] Or shows "No file modifications" for read-only
- [ ] Format: "Files: 2 | +50 / -10 lines"

### Affected Files
- [ ] Lists unique files affected
- [ ] Shows up to 10 files
- [ ] Shows "... and X more" if more than 10
- [ ] Files are sorted

### Diff Preview
- [ ] Shows "PROPOSED CHANGES" header
- [ ] Displays unified diff format
- [ ] File names shown (--- a/, +++ b/)
- [ ] Changes shown (- old, + new)
- [ ] Scrollable if large
- [ ] Truncation message if > 300 lines
- [ ] No duplicates on refresh

### Idempotency
- [ ] Refresh (press 'r') does not duplicate widgets
- [ ] Re-selecting run renders cleanly
- [ ] No console errors
- [ ] Performance acceptable (< 1s render)

### Color Display
- [ ] All markup colors render correctly
- [ ] Text readable on background
- [ ] No color bleeding or visual artifacts

---

## Debugging

### If Badge Doesn't Appear

1. Check that proposals exist in run output:
   ```bash
   curl -s http://localhost:3001/runs/$RUN_ID | jq '.output.proposals' | head -5
   ```

2. Verify TUI is showing full details (scroll down)

3. Check for errors in Terminal 1 (server logs)

### If Metrics Show Wrong Numbers

1. Count actual lines in proposal:
   ```bash
   curl -s http://localhost:3001/runs/$RUN_ID | jq '.output.proposals[0].proposal' | jq '.'
   ```

2. Calculate manually:
   - old_content lines - empty lines = removed
   - new_content lines - empty lines = added

### If Diff Doesn't Render

1. Check proposal has "proposal" field:
   ```bash
   curl -s http://localhost:3001/runs/$RUN_ID | jq '.output.proposals[0] | keys' | grep proposal
   ```

2. Verify old_content and new_content exist:
   ```bash
   curl -s http://localhost:3001/runs/$RUN_ID | jq '.output.proposals[0].proposal | {old_content, new_content} | map(length)'
   ```

### If Widgets Duplicate on Refresh

1. Check unique widget IDs:
   ```bash
   # In TUI, press 'r' to refresh
   # If duplicates appear, note the widget IDs in error message
   ```

2. Verify implementation uses correct ID pattern:
   - Should be: `proposal-review-{run_id}`, etc.

---

## Cleanup

```bash
rm -rf /tmp/test-proposal-ws
rm /tmp/low_risk_run.txt  # if created
```

---

## Test Summary Checklist

- [ ] Risk badge displays with correct color
- [ ] Risk factors listed appropriately
- [ ] Affected files shown
- [ ] Change metrics correct (files, +lines, -lines)
- [ ] Diff preview renders with unified format
- [ ] Large diffs truncate at 300 lines
- [ ] No duplicate widgets on refresh
- [ ] All colors readable
- [ ] Multiple file proposals handled
- [ ] LOW risk shows "No file modifications"
- [ ] Widget IDs are unique per run
- [ ] Performance acceptable (< 1s)
- [ ] No kernel modifications made
- [ ] All tests pass (755 tests)

---

**Test Date:** _____________

**Tester:** _____________

**Notes:** _____________
