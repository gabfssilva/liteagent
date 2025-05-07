"""User message widget for displaying user messages in the chat interface."""
from textual import events
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static

from .reactive_markdown import ReactiveMarkdown


class UserMessageWidget(Static):
    """Collapsible widget that displays a user message."""

    collapsed = reactive(False, init=False)

    def __init__(self, content: str, classes: str = "user-message"):
        super().__init__(classes=classes)
        self.collapsed_symbol = '▶'
        self.expanded_symbol = '▼'
        self.border_title = f"{self.collapsed_symbol} 👤 You"
        self.message_content = content
        self.border_subtitle = f"⌨️ Typed ≈ {len(content) / 4} tokens"

    def compose(self) -> ComposeResult:
        yield ReactiveMarkdown(markdown=self.message_content, finished=True)

    def on_mount(self) -> None:
        if not self.collapsed:
            self.border_title = f"{self.expanded_symbol} 👤 You"
            self.styles.padding = (1, 1, 1, 1)
            self.query_one(ReactiveMarkdown).display = True
        else:
            self.border_title = f"{self.collapsed_symbol} 👤 You"
            self.styles.padding = (-1, -1, 1, -1)
            self.query_one(ReactiveMarkdown).display = False

    def _on_click(self, event: events.Click) -> None:
        if self == event.widget:
            self.collapsed = not self.collapsed

            if not self.collapsed:
                self.border_title = f"{self.expanded_symbol} 👤 You"
                self.styles.padding = (1, 1, 1, 1)
                self.query_one(ReactiveMarkdown).display = True
            else:
                self.border_title = f"{self.collapsed_symbol} 👤 You"
                self.styles.padding = (-1, -1, 1, -1)
                self.query_one(ReactiveMarkdown).display = False
