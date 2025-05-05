"""User message widget for displaying user messages in the chat interface."""
from textual import events
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static

from .reactive_markdown import ReactiveMarkdown


class UserMessageWidget(Static):
    """Collapsible widget that displays a user message."""

    collapsed = reactive(False, init=False, recompose=True)

    def __init__(self, content: str, classes: str = "user-message"):
        super().__init__(classes=classes)
        self.collapsed_symbol = '▶'
        self.expanded_symbol = '▼'
        self.border_title = f"{self.collapsed_symbol} 👤 You"
        self.message_content = content

    def compose(self) -> ComposeResult:
        if not self.collapsed:
            self.border_title = f"{self.expanded_symbol} 👤 You"
            self.styles.padding = (1, 1, 0, 0)
            yield ReactiveMarkdown(markdown=self.message_content, finished=True)
        else:
            self.border_title = f"{self.collapsed_symbol} 👤 You"
            self.styles.padding = (-1, -1, 0, -1)
            self.remove_children()

    def _on_click(self, event: events.Click) -> None:
        self.collapsed = not self.collapsed
        event.stop()
