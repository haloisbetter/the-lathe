"""
Pattern A — Worker Console / Live View

Live dashboard showing system health, recent runs, and statistics.
Polling-based with exponential backoff on connection failure.
No business logic. Renders server responses verbatim.
"""
import time
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Static,
    Header,
    Footer,
    ListView,
    ListItem,
    Label,
    Rule,
)
from textual.binding import Binding
from textual.timer import Timer

from .client import LatheClient


class ConsoleScreen(Screen):
    BINDINGS = [
        Binding("r", "force_refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
        Binding("tab", "switch_screen", "Replay"),
    ]

    DEFAULT_POLL_INTERVAL = 2.0
    MAX_BACKOFF = 30.0

    def __init__(self, client: LatheClient, poll_interval: float = 2.0) -> None:
        super().__init__()
        self.client = client
        self.poll_interval = poll_interval
        self._backoff = poll_interval
        self._connected = False
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            yield Static("", id="console-health")
            yield Rule()
            yield Static("", id="console-runs")
            yield Rule()
            yield Static("", id="console-stats")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()
        self._timer = self.set_interval(self.poll_interval, self._poll)

    def _poll(self) -> None:
        self.refresh_all()

    def refresh_all(self) -> None:
        self._refresh_health()
        self._refresh_runs()
        self._refresh_stats()

    def _refresh_health(self) -> None:
        widget = self.query_one("#console-health", Static)
        health = self.client.health()
        summary = self.client.health_summary()

        if health.get("error_type") == "connection_refused":
            self._connected = False
            self._backoff = min(self._backoff * 2, self.MAX_BACKOFF)
            if self._timer:
                self._timer.stop()
                self._timer = self.set_interval(self._backoff, self._poll)
            widget.update(
                "[bold red]━━━ DISCONNECTED ━━━[/]\n"
                f"  Cannot reach {self.client.base_url}\n"
                f"  Retrying every {self._backoff:.0f}s"
            )
            return

        if not self._connected:
            self._connected = True
            self._backoff = self.poll_interval
            if self._timer:
                self._timer.stop()
                self._timer = self.set_interval(self.poll_interval, self._poll)

        lines = ["[bold cyan]━━━ SYSTEM HEALTH ━━━[/]"]
        lines.append(f"  Status: [green]Connected[/]")

        if summary and not summary.get("error_type"):
            rate = summary.get("success_rate", None)
            if rate is not None:
                color = "green" if rate >= 0.8 else "yellow" if rate >= 0.5 else "red"
                lines.append(f"  Success rate: [{color}]{rate:.0%}[/]")
            recent_errors = summary.get("recent_errors", [])
            if recent_errors:
                lines.append(f"  Recent errors: [red]{len(recent_errors)}[/]")
                for err in recent_errors[:3]:
                    lines.append(f"    • {err}")
            total = summary.get("total_runs", None)
            if total is not None:
                lines.append(f"  Total runs: {total}")

        widget.update("\n".join(lines))

    def _refresh_runs(self) -> None:
        widget = self.query_one("#console-runs", Static)
        if not self._connected:
            widget.update("[dim]  Waiting for connection...[/]")
            return

        data = self.client.runs_list(params={"limit": 15})
        if data.get("error_type"):
            widget.update(f"[red]  Error loading runs: {data.get('message', '?')}[/]")
            return

        runs = data.get("runs", [])
        lines = ["[bold cyan]━━━ RECENT RUNS ━━━[/]"]
        if not runs:
            lines.append("  [dim]No runs recorded[/]")
        else:
            lines.append(f"  {'STATUS':<8} {'INTENT':<12} {'WORKSPACE':<16} {'ID'}")
            lines.append(f"  {'─'*8} {'─'*12} {'─'*16} {'─'*24}")
            for r in runs:
                success = r.get("success")
                status = "[green]OK[/]    " if success else "[red]FAIL[/]  " if success is False else "[yellow]?[/]     "
                intent = r.get("intent", "?")[:12]
                ws = (r.get("workspace") or "—")[:16]
                rid = r.get("id", r.get("run_id", "?"))
                model = r.get("model_used", r.get("model", ""))
                line = f"  {status} {intent:<12} {ws:<16} {rid}"
                if model:
                    line += f"  ({model})"
                lines.append(line)

        widget.update("\n".join(lines))

    def _refresh_stats(self) -> None:
        widget = self.query_one("#console-stats", Static)
        if not self._connected:
            widget.update("")
            return

        run_stats = self.client.runs_stats()
        ws_stats = self.client.workspace_stats()

        lines = ["[bold cyan]━━━ STATISTICS ━━━[/]"]

        if run_stats and not run_stats.get("error_type"):
            by_intent = run_stats.get("by_intent", {})
            if by_intent:
                lines.append("  Runs by intent:")
                for intent, count in sorted(by_intent.items()):
                    lines.append(f"    {intent}: {count}")
            by_model = run_stats.get("by_model", {})
            if by_model:
                lines.append("  Runs by model:")
                for model, count in sorted(by_model.items()):
                    lines.append(f"    {model}: {count}")
            total = run_stats.get("total", None)
            if total is not None:
                lines.append(f"  Total runs: {total}")

        if ws_stats and not ws_stats.get("error_type"):
            ws_count = ws_stats.get("workspace_count", ws_stats.get("total_workspaces", None))
            if ws_count is not None:
                lines.append(f"  Workspaces: {ws_count}")
            total_files = ws_stats.get("total_files", None)
            if total_files is not None:
                lines.append(f"  Total files: {total_files}")
            extensions = ws_stats.get("extensions", {})
            if extensions:
                lines.append("  Extensions:")
                for ext, count in sorted(extensions.items(), key=lambda x: -x[1])[:8]:
                    lines.append(f"    {ext}: {count}")

        widget.update("\n".join(lines))

    def action_force_refresh(self) -> None:
        self.refresh_all()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_switch_screen(self) -> None:
        self.app.switch_mode("replay")
