"""Base widget for chat UI components with common functionality."""

import time
from abc import abstractmethod

from textual.app import ComposeResult
from textual.events import Click
from textual.widgets import Static
from textual.reactive import reactive


class BaseMessageWidget(Static):
    """Base widget for message components with common features like state indicators and timers."""

    state = reactive("waiting")
    frame = reactive(0)
    elapsed = reactive(0)
    start = reactive(0)
    collapsed = reactive(True, init=False, recompose=False)

    def __init__(
        self,
        id: str,
        name: str,
        emoji: str,
        subtitle: str = None,
        refresh_rate: float = 0.5,
        follow: bool = False,
        collapsed: bool = False,
        classes: str = "message"
    ):
        super().__init__(id=id, classes=classes)
        self.collapsed_symbol = '▶'
        self.expanded_symbol = '▼'
        self.widget_name = self._format_name(name)
        self.emoji = emoji
        self.subtitle = subtitle
        self.refresh_rate = refresh_rate
        self.follow = follow
        self.title_template = f"{{symbol}} {emoji} {self.widget_name} {{state_emoji}}"
        self.collapsed = collapsed
        self.border_subtitle = subtitle or ""

    def _on_click(self, event: Click) -> None:
        if self == event.widget:
            self.collapsed = not self.collapsed

            if not self.collapsed:
                self.styles.padding = (1, 1, 1, 1)
            else:
                self.styles.padding = (-1, -1, 1, -1)

            for child in self.children:
                child.display = not self.collapsed

            self.border_title = self.current_title
            self.border_subtitle = self.current_subtitle

        event.stop()

    @property
    def symbol(self):
        return self.expanded_symbol if not self.collapsed else self.collapsed_symbol

    @staticmethod
    def _format_name(name: str) -> str:
        return name.replace("_", " ").title()

    def on_mount(self) -> None:
        self.start = time.perf_counter()
        self._elapsed_timer = self.set_interval(0.1, self._elapsed)
        self._blink_timer = self.set_interval(0.5, self._blink)

        if not self.collapsed:
            self.styles.padding = (1, 1, 1, 1)
        else:
            self.styles.padding = (-1, -1, 1, -1)

        for child in self.children:
            child.display = not self.collapsed

    def _elapsed(self):
        self.elapsed = time.perf_counter() - self.start

    def _blink(self) -> None:
        if self.state == "waiting":
            self.frame = 1 if self.frame == 0 else 0

    def watch_frame(self, frame):
        self.border_title = self.current_title

    def watch_elapsed(self, elapsed):
        self.border_subtitle = self.current_subtitle
        self.border_title = self.current_title

    @abstractmethod
    def message_children(self):
        pass

    def compose(self) -> ComposeResult:
        self.border_title = self.current_title
        self.border_subtitle = self.current_subtitle

        yield from self.message_children()

    @property
    def state_emoji(self):
        if self.state == 'waiting' and self.frame == 0:
            return "⚪"
        elif self.state == 'waiting':
            return "  "
        elif self.state == "completed":
            return "🟢"
        else:
            return "🔴"

    @property
    def current_title(self):
        return self.title_template.format(
            state_emoji=self.state_emoji,
            symbol=self.symbol,
        )

    @property
    def current_subtitle(self):
        return f"{self.subtitle or ''} {self.elapsed:.1f}s"

    def watch_state(self, state: str) -> None:
        if state in ["completed", "failed"]:
            self._blink_timer.stop()
            self._elapsed_timer.stop()
            self.border_title = self.current_title

    def complete(self, failed: bool = False) -> None:
        self.state = "failed" if failed else "completed"

    def finish(self) -> None:
        self.complete(failed=False)
