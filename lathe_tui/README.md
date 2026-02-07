# Lathe TUI

Terminal operator console for The Lathe. Pure HTTP client — no kernel or app layer imports.

## Install

```bash
pip install textual requests
```

## Run

```bash
# Start the TUI (default: connects to http://127.0.0.1:3001)
python -m lathe_tui

# Custom server URL
python -m lathe_tui --url http://myhost:4000

# Or via environment variable
LATHE_URL=http://myhost:4000 python -m lathe_tui

# Custom polling interval (seconds)
python -m lathe_tui --poll 5
```

## Screens

- **Replay** (Pattern C): Browse and inspect historical runs. Select a run to see full deterministic replay — identity, model selection, validation, context echo, review gate, staleness, and files touched.
- **Console** (Pattern A): Live dashboard with health status, recent runs, and aggregate statistics. Polls the server at a configurable interval with exponential backoff on disconnect.

### Keybinds

| Key   | Action              |
|-------|---------------------|
| Tab   | Switch screen       |
| r     | Refresh             |
| j/k   | Scroll list         |
| Enter | Load selected run   |
| q     | Quit                |

## Smoke Test

```bash
# Headless connectivity test (no TUI)
python -m lathe_tui --smoke

# Against a custom URL
python -m lathe_tui --smoke --url http://myhost:4000
```

## Architecture

The TUI is a pure HTTP client. It:
- Talks only to `lathe_app.server` via HTTP
- Never imports `lathe` or `lathe_app`
- Never touches filesystem or git directly
- Contains zero business logic
- Renders server responses verbatim
