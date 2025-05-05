"""User message widget for displaying user messages in the chat interface."""

from textual.app import ComposeResult
from textual.widgets import Static

from .reactive_markdown import ReactiveMarkdown


class UserMessageWidget(Static):
    """Widget that displays a user message."""
    
    def __init__(self, content: str, classes: str = "user-message"):
        super().__init__(classes=classes)
        self.markdown = ReactiveMarkdown(markdown=f"{content}", finished=True)
        self.border_title = "👤 You"

    def compose(self) -> ComposeResult:
        yield self.markdown