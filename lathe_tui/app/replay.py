"""
Pattern C — Run Replay / Debugger

Deterministic replay of historical RunRecords.
No re-execution, no mutation, no business logic.
"""
import json

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Static,
    Header,
    Footer,
    ListView,
    ListItem,
    Label,
    Button,
    LoadingIndicator,
    Rule,
)
from textual.binding import Binding

from .client import LatheClient
from .timeformat import format_timestamp


def _safe_get(d, *keys, default="—"):
    val = d
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, default)
        else:
            return default
    return val if val is not None else default


class RunListItem(ListItem):
    def __init__(self, run_data: dict) -> None:
        self.run_data = run_data
        run_id = run_data.get("id", run_data.get("run_id", "?"))
        intent = run_data.get("intent", "?")
        success = run_data.get("success", None)
        indicator = "[#879A39]OK[/]" if success else "[#D14D41]FAIL[/]" if success is False else "[#D0A215]?[/]"
        label = f"{indicator}  {intent:<10} {run_id}"
        super().__init__()
        self._label_text = label

    def compose(self) -> ComposeResult:
        yield Label(self._label_text, markup=True)


class RunDetailPanel(VerticalScroll):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_run_id: str | None = None

    def clear_detail(self) -> None:
        self._current_run_id = None
        self.remove_children()
        self.mount(Static("[#878580]Select a run to inspect[/]", markup=True))

    def show_loading(self) -> None:
        self.remove_children()
        self.mount(LoadingIndicator())

    def show_error(self, message: str) -> None:
        self.remove_children()
        self.mount(Static(f"[#D14D41]{message}[/]", markup=True))

    def show_run(self, run: dict, review: dict, staleness: dict, files: dict) -> None:
        run_id = run.get("id", run.get("run_id", "?"))
        self._current_run_id = run_id
        self.remove_children()

        self.mount(Static("[bold #3AA99F]━━━ IDENTITY ━━━[/]", markup=True))
        run_id = run.get("id", run.get("run_id", "?"))
        self.mount(Static(f"  Run ID:     {run_id}"))
        self.mount(Static(f"  Intent:     {_safe_get(run, 'intent')}"))
        self.mount(Static(f"  Task:       {_safe_get(run, 'task')}"))
        self.mount(Static(f"  Workspace:  {_safe_get(run, 'workspace', default='(none)')}"))
        self.mount(Static(f"  Timestamp:  {format_timestamp(_safe_get(run, 'timestamp'))}"))
        self.mount(Static(f"  Success:    {_safe_get(run, 'success')}"))

        model = _safe_get(run, 'model_used', default=None) or _safe_get(run, 'model', default=None)
        tier = _safe_get(run, 'model_tier', default=None)
        if model or tier:
            self.mount(Rule())
            self.mount(Static("[bold #3AA99F]━━━ MODEL SELECTION ━━━[/]", markup=True))
            if model:
                self.mount(Static(f"  Model:      {model}"))
            if tier:
                self.mount(Static(f"  Tier:       {tier}"))
            speculative = run.get("speculative", None)
            if speculative is not None:
                self.mount(Static(f"  Speculative: {speculative}"))
            escalated = run.get("escalated_from", None)
            if escalated:
                self.mount(Static(f"  Escalated from: {escalated}"))

        output = run.get("output", {})
        if isinstance(output, dict):
            self.mount(Rule())
            self.mount(Static("[bold #3AA99F]━━━ VALIDATION & CLASSIFICATION ━━━[/]", markup=True))
            if "reason" in output:
                self.mount(Static(f"  Reason:     {output['reason']}"))
            if "details" in output:
                self.mount(Static(f"  Details:    {output['details']}"))
            classification = output.get("classification", None)
            if classification:
                self.mount(Static(f"  Classification: {classification}"))

            proposals = output.get("proposals", [])
            if proposals:
                self.mount(Static(f"  Proposals:  {len(proposals)}"))
                for i, p in enumerate(proposals[:10]):
                    action = p.get("action", "?")
                    target = p.get("target", "?")
                    self.mount(Static(f"    [{i+1}] {action} → {target}"))

            assumptions = output.get("assumptions", [])
            if assumptions:
                self.mount(Static(f"  Assumptions: {len(assumptions)}"))
                for a in assumptions[:5]:
                    self.mount(Static(f"    • {a}"))

            risks = output.get("risks", [])
            if risks:
                self.mount(Static(f"  Risks:      {len(risks)}"))
                for r in risks[:5]:
                    self.mount(Static(f"    • {r}"))

        context_echo = run.get("context_echo", None)
        if context_echo and isinstance(context_echo, dict):
            self.mount(Rule())
            self.mount(Static("[bold #3AA99F]━━━ CONTEXT ECHO ━━━[/]", markup=True))
            self.mount(Static(f"  Valid:      {context_echo.get('valid', '?')}"))
            self.mount(Static(f"  Workspace:  {context_echo.get('workspace', '?')}"))
            self.mount(Static(f"  Snapshot:   {context_echo.get('snapshot', '?')}"))
            echo_files = context_echo.get("files", [])
            if echo_files:
                self.mount(Static(f"  Files ({len(echo_files)}):"))
                for f in echo_files[:20]:
                    self.mount(Static(f"    • {f}"))
            violations = context_echo.get("violations", [])
            if violations:
                self.mount(Static(f"  [#D14D41]Violations ({len(violations)}):[/]", markup=True))
                for v in violations:
                    rule = v.get("rule", "?")
                    detail = v.get("detail", "?")
                    self.mount(Static(f"    [#D14D41]✗ {rule}: {detail}[/]", markup=True))

        why = run.get("why", {})
        if why and isinstance(why, dict):
            self.mount(Rule())
            self.mount(Static("[bold #3AA99F]━━━ WHY RECORD ━━━[/]", markup=True))
            for k, v in why.items():
                self.mount(Static(f"  {k}: {v}"))

        review_endpoint_exists = not review.get("missing_endpoint", False)

        if review and review_endpoint_exists and review.get("ok", True):
            self.mount(Rule())
            self.mount(Static("[bold #3AA99F]━━━ REVIEW GATE ━━━[/]", markup=True))
            state = review.get("state", review.get("action", "—"))
            self.mount(Static(f"  State:      {state}"))
            reviewer = review.get("reviewer", review.get("reviewed_by", None))
            if reviewer:
                self.mount(Static(f"  Reviewer:   {reviewer}"))
            comment = review.get("comment", None)
            if comment:
                self.mount(Static(f"  Comment:    {comment}"))
            reviewed_at = review.get("reviewed_at", None)
            if reviewed_at:
                self.mount(Static(f"  Reviewed:   {format_timestamp(reviewed_at)}"))

        if review_endpoint_exists:
            self.mount(Button("Approve", id="btn-approve", variant="success"))
            self.mount(Button("Reject", id="btn-reject", variant="error"))
            self.mount(Static("", id="review-result"))

        if staleness and not staleness.get("missing_endpoint") and staleness.get("ok", True):
            self.mount(Rule())
            self.mount(Static("[bold #3AA99F]━━━ STALENESS ━━━[/]", markup=True))
            stale = staleness.get("potentially_stale", False)
            color = "#D14D41" if stale else "#879A39"
            self.mount(Static(f"  Potentially stale: [{color}]{stale}[/]", markup=True))
            self.mount(Static(f"  Stale files:  {staleness.get('stale_count', 0)}"))
            self.mount(Static(f"  Fresh files:  {staleness.get('fresh_count', 0)}"))
            stale_files = staleness.get("stale_files", [])
            for sf in stale_files[:10]:
                self.mount(Static(f"    [#D14D41]• {sf}[/]", markup=True))

        if files and not files.get("missing_endpoint") and files.get("ok", True):
            touched = files.get("files", [])
            if touched:
                self.mount(Rule())
                self.mount(Static("[bold #3AA99F]━━━ FILES TOUCHED ━━━[/]", markup=True))
                for f in touched[:30]:
                    self.mount(Static(f"  • {f}"))

        file_reads = run.get("file_reads", [])
        if file_reads:
            self.mount(Rule())
            self.mount(Static("[bold #3AA99F]━━━ FILE READS ━━━[/]", markup=True))
            for fr in file_reads[:20]:
                path = fr.get("path", "?")
                ts = format_timestamp(fr.get("timestamp", ""))
                self.mount(Static(f"  • {path}  ({ts})"))


class ReplayScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh_runs", "Refresh"),
        Binding("q", "quit_app", "Quit"),
        Binding("tab", "switch_screen", "Console"),
    ]

    def __init__(self, client: LatheClient) -> None:
        super().__init__()
        self.client = client
        self._runs: list = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="replay-container"):
            yield ListView(id="runs-list")
            yield RunDetailPanel(id="run-detail")
        yield Footer()

    def on_mount(self) -> None:
        self.load_runs()
        detail = self.query_one("#run-detail", RunDetailPanel)
        detail.clear_detail()

    def load_runs(self) -> None:
        data = self.client.runs_list(params={"limit": 50})
        runs_list = self.query_one("#runs-list", ListView)
        runs_list.clear()

        if not data.get("ok", True) or data.get("error_type"):
            runs_list.append(ListItem(Label(f"[#D14D41]Error: {data.get('message', 'Connection failed')}[/]", markup=True)))
            return

        self._runs = data.get("runs", [])
        if not self._runs:
            runs_list.append(ListItem(Label("[#878580]No runs found[/]", markup=True)))
            return

        for run in self._runs:
            runs_list.append(RunListItem(run))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, RunListItem):
            return
        run_data = item.run_data
        run_id = run_data.get("id", run_data.get("run_id"))
        if not run_id:
            return
        self.load_run_detail(run_id)

    def load_run_detail(self, run_id: str) -> None:
        detail = self.query_one("#run-detail", RunDetailPanel)
        detail.show_loading()

        run = self.client.runs_get(run_id)
        if not run.get("ok", True) or run.get("error_type"):
            detail.show_error(run.get("message", f"Failed to load run {run_id}"))
            return

        review = self.client.run_review_get(run_id)
        staleness = self.client.run_staleness_get(run_id)
        files = self.client.fs_run_files(run_id)

        detail.show_run(run, review, staleness, files)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        detail = self.query_one("#run-detail", RunDetailPanel)
        run_id = detail._current_run_id
        if not run_id:
            return

        if event.button.id == "btn-approve":
            action = "approve"
        elif event.button.id == "btn-reject":
            action = "reject"
        else:
            return

        result = self.client.review_submit(run_id, action)

        try:
            result_widget = detail.query_one("#review-result", Static)
        except Exception:
            return

        display = json.dumps(result, indent=2, default=str)
        status = result.get("_status", 200)

        if result.get("error_type"):
            result_widget.update(f"[#D14D41]Error:[/]\n{display}")
        elif result.get("missing_endpoint"):
            result_widget.update("[#D0A215]Review endpoint not available[/]")
        elif status >= 400:
            result_widget.update(f"[#D14D41]Server returned {status}:[/]\n{display}")
        else:
            result_widget.update(f"[#879A39]Server response:[/]\n{display}")

    def action_refresh_runs(self) -> None:
        self.load_runs()
        detail = self.query_one("#run-detail", RunDetailPanel)
        detail.clear_detail()

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_switch_screen(self) -> None:
        self.app.switch_mode("console")
