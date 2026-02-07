"""12-hour local time formatting for display."""
from datetime import datetime, timezone


def format_timestamp(raw: str | None) -> str:
    if not raw or raw == "—":
        return "—"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        local_dt = dt.astimezone()
        return local_dt.strftime("%-I:%M:%S %p")
    except (ValueError, TypeError):
        return str(raw)
