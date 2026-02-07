"""
Lathe TUI Application

Main Textual application binding Pattern A (Console) and Pattern C (Replay).
Pure HTTP client — no imports from lathe or lathe_app.
"""
import os
from textual.app import App

from .client import LatheClient
from .replay import ReplayScreen
from .console import ConsoleScreen
from .styles import APP_CSS


class LatheTUI(App):
    TITLE = "The Lathe"
    SUB_TITLE = "Operator Console"
    CSS = APP_CSS

    MODES = {
        "replay": ReplayScreen,
        "console": ConsoleScreen,
    }

    def __init__(self, base_url: str | None = None, poll_interval: float = 2.0):
        super().__init__()
        url = base_url or os.environ.get("LATHE_URL", "http://127.0.0.1:3001")
        self.client = LatheClient(base_url=url)
        self._poll_interval = poll_interval

    def on_mount(self) -> None:
        self.switch_mode("replay")

    def _get_mode_screen(self, mode_name: str):
        if mode_name == "replay":
            return ReplayScreen(self.client)
        elif mode_name == "console":
            return ConsoleScreen(self.client, poll_interval=self._poll_interval)
        raise ValueError(f"Unknown mode: {mode_name}")

    def switch_mode(self, mode: str) -> None:
        screen = self._get_mode_screen(mode)
        self.push_screen(screen)


def run_tui(base_url: str | None = None, poll_interval: float = 2.0) -> None:
    app = LatheTUI(base_url=base_url, poll_interval=poll_interval)
    app.run()
