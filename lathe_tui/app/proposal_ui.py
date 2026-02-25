"""
Proposal Review UI Components

Risk badge, diff preview panel, and change metrics.
"""
from typing import Any, Dict, List, Optional

from textual.widgets import Static, Rule, Label
from textual.containers import Container, Vertical
from textual.reactive import reactive


class RiskBadge(Static):
    """
    Risk level badge with color coding.

    LOW: green (#879A39)
    MEDIUM: yellow (#D0A215)
    HIGH: red (#D14D41)
    """

    risk_level = reactive("LOW")

    def __init__(self, risk_level: str = "LOW", run_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.risk_level = risk_level
        self.run_id = run_id
        self._render()

    def _render(self) -> None:
        color_map = {
            "LOW": "#879A39",
            "MEDIUM": "#D0A215",
            "HIGH": "#D14D41",
        }
        color = color_map.get(self.risk_level, "#878580")
        self.update(f"[{color}][{self.risk_level} RISK][/]", markup=True)

    def update_risk(self, level: str) -> None:
        self.risk_level = level
        self._render()


class ChangeMetrics(Static):
    """
    Summary metrics header for proposed changes.

    Shows: Files: X | +Y / -Z lines
    """

    def __init__(self, metrics: Dict[str, Any] = None, **kwargs):
        super().__init__(**kwargs)
        self._metrics = metrics or {}
        self._render()

    def _render(self) -> None:
        metrics = self._metrics
        files = metrics.get("files_changed", 0)
        lines_added = metrics.get("lines_added", 0)
        lines_removed = metrics.get("lines_removed", 0)
        write_ops = metrics.get("write_operations", False)

        if not write_ops:
            self.update("[#878580]No file modifications proposed[/]", markup=True)
            return

        summary = f"Files: [bold]{files}[/] | [#879A39]+{lines_added}[/] / [#D14D41]-{lines_removed}[/] lines"
        self.update(summary, markup=True)

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        self._metrics = metrics
        self._render()


class DiffPreviewPanel(Container):
    """
    Collapsible diff preview panel.

    Shows unified diff with truncation at 300 lines.
    Displays "Show more" toggle if large.
    """

    def __init__(self, run_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.run_id = run_id
        self._diff_content = ""
        self._is_expanded = True
        self._max_lines = 300
        self._full_diff = ""
        self._has_more = False
        self._mounted = False

    def set_diff(self, diff_content: str, full_diff: str = "") -> None:
        """
        Set diff content and optional full diff.

        If full_diff is longer, a "Show more" toggle is provided.
        """
        self._diff_content = diff_content
        self._full_diff = full_diff
        self._has_more = len(full_diff) > len(diff_content) if full_diff else False
        self._render()

    def _render(self) -> None:
        self.remove_children()
        self._mounted = False

        if not self._diff_content:
            self.mount(Static("[#878580](no changes to preview)[/]", markup=True))
            return

        self.mount(Static("[bold #3AA99F]━━━ PROPOSED CHANGES ━━━[/]", markup=True))

        from textual.widgets import ScrollableContainer

        scroll = ScrollableContainer(Static(self._diff_content, id=f"diff-scroll-{self.run_id}"))
        self.mount(scroll)

        if self._has_more:
            self.mount(Static(""))
            self.mount(Static(
                "[#D0A215]... diff truncated. Enable line wrapping for full view.[/]",
                markup=True,
                id=f"diff-more-{self.run_id}"
            ))

        self._mounted = True

    def clear(self) -> None:
        self.remove_children()
        self._diff_content = ""
        self._full_diff = ""
        self._mounted = False


class ProposalReviewPanel(Container):
    """
    Complete proposal review section.

    Includes:
    - Risk badge
    - Change metrics
    - Affected files list
    - Diff preview
    """

    def __init__(self, run_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.run_id = run_id
        self._risk_badge: Optional[RiskBadge] = None
        self._metrics: Optional[ChangeMetrics] = None
        self._diff_panel: Optional[DiffPreviewPanel] = None
        self._mounted = False

    def render_proposal(
        self,
        risk_data: Dict[str, Any],
        metrics_data: Dict[str, Any],
        diff_content: str = "",
    ) -> None:
        """
        Render complete proposal review panel.

        risk_data: {"level": "HIGH", "reasons": [...]}
        metrics_data: {"files_changed": 2, "lines_added": 50, ...}
        diff_content: unified diff string
        """
        self.remove_children()

        risk_level = risk_data.get("level", "LOW")
        self.mount(Static("[bold #3AA99F]━━━ PROPOSAL REVIEW ━━━[/]", markup=True))

        self._risk_badge = RiskBadge(risk_level=risk_level, run_id=self.run_id, id=f"risk-badge-{self.run_id}")
        self.mount(self._risk_badge)

        reasons = risk_data.get("reasons", [])
        if reasons:
            self.mount(Static("[bold]Risk Factors:[/]", markup=True))
            for reason in reasons[:5]:
                self.mount(Static(f"  • {reason}"))

        self.mount(Rule())

        self._metrics = ChangeMetrics(metrics=metrics_data, id=f"metrics-{self.run_id}")
        self.mount(self._metrics)

        affected = metrics_data.get("affected_files", [])
        if affected:
            self.mount(Static(""))
            self.mount(Static("[bold]Affected Files:[/]", markup=True))
            for f in affected[:10]:
                self.mount(Static(f"  • {f}"))
            if len(affected) > 10:
                self.mount(Static(f"  ... and {len(affected) - 10} more"))

        self.mount(Rule())

        self._diff_panel = DiffPreviewPanel(run_id=self.run_id, id=f"diff-panel-{self.run_id}")
        if diff_content:
            self._diff_panel.set_diff(diff_content)
        self.mount(self._diff_panel)

        self._mounted = True

    def update_risk_badge(self, risk_level: str) -> None:
        if self._risk_badge:
            self._risk_badge.update_risk(risk_level)

    def update_metrics(self, metrics_data: Dict[str, Any]) -> None:
        if self._metrics:
            self._metrics.update_metrics(metrics_data)

    def clear(self) -> None:
        self.remove_children()
        self._risk_badge = None
        self._metrics = None
        self._diff_panel = None
        self._mounted = False
