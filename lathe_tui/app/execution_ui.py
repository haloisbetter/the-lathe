"""
Execution UI Components

Timeline, history strip, and trace panel for live execution display.
"""
import json
import time
from typing import Any, Dict, List, Optional

from textual.widgets import Static, Rule, Button, Label
from textual.containers import Container, Vertical
from textual.timer import Timer

from .timeformat import format_timestamp


class OperatorTimeline(Container):
    """
    Visual state progression: [Proposed] → [Approved] → [Queued] → [Running] → [Succeeded/Failed]

    States are color-coded:
    - Proposed: dim
    - Approved: blue
    - Queued: yellow
    - Running: yellow
    - Succeeded: green
    - Failed: red
    """

    def __init__(self, run_data: dict, review_data: Optional[dict] = None, job_data: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self._run_data = run_data
        self._review_data = review_data or {}
        self._job_data = job_data or {}
        self._render()

    def _render(self) -> None:
        self.remove_children()
        states = []
        states.append(("Proposed", "#878580"))

        review_state = self._review_data.get("state", None)
        if review_state:
            color = "#3AA99F" if review_state == "APPROVED" else "#D0A215" if review_state == "REVIEWED" else "#D14D41" if review_state == "REJECTED" else "#878580"
            states.append((review_state, color))

        job_status = self._job_data.get("status", None)
        if job_status:
            color = "#D0A215" if job_status == "queued" else "#D0A215" if job_status == "running" else "#879A39" if job_status == "succeeded" else "#D14D41" if job_status == "failed" else "#878580"
            states.append((job_status.upper(), color))

        timeline = " → ".join([f"[{color}]{state}[/]" for state, color in states])

        self.mount(Static(f"[bold]EXECUTION STATE:[/] {timeline}", markup=True))

    def update_job(self, job_data: dict) -> None:
        self._job_data = job_data
        self._render()

    def update_review(self, review_data: dict) -> None:
        self._review_data = review_data
        self._render()


class HistoryStrip(Container):
    """
    Render static history metadata above the timeline.

    Proposed at, Approved at, Executed at (if exists), Outcome, Model used
    """

    def __init__(self, run_data: dict, review_data: Optional[dict] = None, job_data: Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        self._run_data = run_data
        self._review_data = review_data or {}
        self._job_data = job_data or {}
        self._render()

    def _render(self) -> None:
        self.remove_children()
        lines = []

        proposed_at = self._run_data.get("timestamp", "")
        if proposed_at:
            lines.append(f"  Proposed:  {format_timestamp(proposed_at)}")

        review_state = self._review_data.get("state")
        reviewed_at = self._review_data.get("reviewed_at")
        if reviewed_at and review_state == "APPROVED":
            lines.append(f"  Approved:  {format_timestamp(reviewed_at)}")

        job_data = self._job_data
        if job_data and job_data.get("finished_at"):
            lines.append(f"  Executed:  {format_timestamp(job_data.get('finished_at', ''))}")
            status = job_data.get("status", "?")
            color = "#879A39" if status == "succeeded" else "#D14D41" if status == "failed" else "#D0A215"
            lines.append(f"  Outcome:   [{color}]{status}[/]")

        model = self._run_data.get("model_used", "") or self._run_data.get("model", "")
        if model:
            lines.append(f"  Model:     {model}")

        if lines:
            self.mount(Static("[bold #3AA99F]━━━ EXECUTION HISTORY ━━━[/]", markup=True))
            for line in lines:
                self.mount(Static(line, markup=True))


class ExecutionTracePanel(Container):
    """
    Live-updating traces panel with job polling.

    Append-only rendering: new traces added without re-rendering entire panel.
    Auto-scroll.
    Each trace shows: tool_id, start_time, duration, status badge, collapsible output.
    """

    def __init__(self, client, run_id: str, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.run_id = run_id
        self._traces: List[Dict[str, Any]] = []
        self._header_mounted = False
        self._job_id: Optional[str] = None
        self._last_trace_count = 0
        self._timer: Optional[Timer] = None
        self._poll_interval = 0.5
        self._last_poll_time = 0
        self._backoff_level = 0

    def start_polling(self) -> None:
        if self._timer is None:
            self._timer = self.app.set_interval(0.1, self._poll_tick)

    def stop_polling(self) -> None:
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _poll_tick(self) -> None:
        now = time.time()
        if now - self._last_poll_time < self._poll_interval:
            return

        self._last_poll_time = now
        self._poll_job()

    def _poll_job(self) -> None:
        data = self.client.run_execute_status(self.run_id)
        if data.get("error_type") or not data.get("ok", True):
            return

        self._job_id = data.get("id")
        if not self._job_id:
            return

        traces_data = self.client.run_tool_traces(self.run_id)
        if not traces_data.get("ok", True) or traces_data.get("error_type"):
            return

        new_traces = traces_data.get("traces", [])
        if len(new_traces) > self._last_trace_count:
            for trace in new_traces[self._last_trace_count:]:
                self._append_trace(trace)
            self._last_trace_count = len(new_traces)

        job_status = data.get("status", "")
        if job_status in ("succeeded", "failed"):
            self.stop_polling()

        self._update_backoff(job_status)

    def _update_backoff(self, job_status: str) -> None:
        if job_status == "running":
            self._poll_interval = 0.5
        elif job_status == "queued":
            elapsed = time.time() - self._last_poll_time
            if elapsed > 5:
                self._backoff_level = 1
                self._poll_interval = 1.0
            if elapsed > 15:
                self._backoff_level = 2
                self._poll_interval = 2.0

    def _render_header(self) -> None:
        if not self._header_mounted:
            self.mount(Static("[bold #3AA99F]━━━ EXECUTION TRACE ━━━[/]", markup=True))
            self._header_mounted = True

    def _append_trace(self, trace: Dict[str, Any]) -> None:
        self._render_header()
        tool_id = trace.get("tool_id", "?")
        started_at = trace.get("started_at", "")
        finished_at = trace.get("finished_at", "")
        ok = trace.get("ok", False)
        status_badge = "[#879A39]✓[/]" if ok else "[#D14D41]✗[/]"

        duration = ""
        if started_at and finished_at:
            try:
                start_ts = time.fromisoformat(started_at.replace("Z", "+00:00"))
                finish_ts = time.fromisoformat(finished_at.replace("Z", "+00:00"))
                dur_ms = int((finish_ts - start_ts).total_seconds() * 1000)
                duration = f" ({dur_ms}ms)"
            except:
                pass

        trace_line = f"  {status_badge}  {tool_id}{duration}"
        self.mount(Static(trace_line, markup=True))

        inputs = trace.get("inputs", {})
        if inputs:
            for k, v in inputs.items():
                self.mount(Static(f"      input.{k}: {v}"))

        if ok:
            output = trace.get("output", {})
            if output and isinstance(output, dict):
                for k, v in list(output.items())[:5]:
                    self.mount(Static(f"      output.{k}: {v}"))
        else:
            error = trace.get("error", {})
            if error and isinstance(error, dict):
                reason = error.get("reason", "unknown")
                self.mount(Static(f"      [#D14D41]error: {reason}[/]", markup=True))

    def show_initial_traces(self) -> None:
        traces_data = self.client.run_tool_traces(self.run_id)
        if traces_data.get("ok", True) and not traces_data.get("error_type"):
            traces = traces_data.get("traces", [])
            self._traces = traces
            self._last_trace_count = len(traces)
            for trace in traces:
                self._append_trace(trace)

    def mount_placeholder(self) -> None:
        self._render_header()
        self.mount(Static("  (waiting for execution...)"))

    def clear(self) -> None:
        self.remove_children()
        self._header_mounted = False
        self._traces = []
        self._last_trace_count = 0
        self.stop_polling()
