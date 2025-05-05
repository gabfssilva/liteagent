"""Base widget for chat UI components with common functionality."""

import time

from textual.widgets import Static
from textual.reactive import reactive


class BaseMessageWidget(Static):
    """Base widget for message components with common features like state indicators and timers."""

    state = reactive("waiting")
    frame = reactive(0)
    elapsed = reactive(0)
    start = reactive(0)

    def __init__(
        self,
        id: str,
        name: str,
        emoji: str,
        subtitle: str = None,
        refresh_rate: float = 0.5,
        follow: bool = False,
        classes: str = "message"
    ):
        super().__init__(id=id, classes=classes)
        self.widget_name = self._format_name(name)
        self.emoji = emoji
        self.subtitle = subtitle
        self.refresh_rate = refresh_rate
        self.follow = follow
        self.title_template = f"{emoji} {self.widget_name} {{emoji}}"
        self.border_title = self.title_template.format(emoji="⚪")
        self.border_subtitle = subtitle or ""

    @staticmethod
    def _format_name(name: str) -> str:
        """Format tool/agent names for display."""
        return name.replace("_", " ").title()

    def on_mount(self) -> None:
        """Setup timers for animations and elapsed time."""
        self.start = time.perf_counter()
        self._elapsed_timer = self.set_interval(0.1, self._elapsed)
        self._blink_timer = self.set_interval(0.5, self._blink)

    def _elapsed(self):
        """Update elapsed time."""
        self.elapsed = time.perf_counter() - self.start

    def _blink(self) -> None:
        """Toggle animation frame for waiting state."""
        if self.state == "waiting":
            self.frame = 1 if self.frame == 0 else 0

    def watch_frame(self, frame):
        """Update UI based on animation frame."""
        emoji = "⚪" if frame == 0 else "  "
        self.border_title = self.title_template.format(emoji=emoji)

    def watch_elapsed(self, elapsed):
        """Update elapsed time display."""
        self.border_subtitle = f"{self.subtitle or ''} {elapsed:.1f}s"

    def watch_state(self, state: str) -> None:
        """React to state changes."""
        if state in ["completed", "failed"]:
            self._blink_timer.stop()
            self._elapsed_timer.stop()
            emoji = "🟢" if state == "completed" else "🔴"
            self.border_title = self.title_template.format(emoji=emoji)

    def complete(self, failed: bool = False) -> None:
        """Mark widget as completed or failed."""
        self.state = "failed" if failed else "completed"

    def finish(self) -> None:
        """Alias for complete(failed=False)."""
        self.complete(failed=False)
