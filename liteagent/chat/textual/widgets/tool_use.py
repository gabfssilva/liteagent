"""Tool use widget for displaying tool executions in the chat interface."""

import re

from textual.app import ComposeResult
from textual.widgets import TabbedContent
from textual.content import Content
from textual.reactive import var

from liteagent import Tool
from .base_widget import BaseMessageWidget
from .reactive_markdown import ReactiveMarkdown


class ToolUseWidget(BaseMessageWidget):
    """Widget that displays a tool use with arguments and results."""

    tool_name = var("")
    tool_emoji = var("")

    def __init__(
        self,
        id: str,
        tool: Tool,
        initial_args: str | None,
        refresh_rate: float = 1 / 3,
        follow: bool = False,
        classes: str = "tool-message"
    ):
        formatted_name = self._camel_to_words(tool.name.replace("__", ": ").replace("_", " "))
        super().__init__(
            id=id,
            name=formatted_name,
            emoji=tool.emoji,
            subtitle=None,
            refresh_rate=refresh_rate,
            follow=follow,
            classes=classes
        )
        self.tool_name = formatted_name
        self.tool_emoji = tool.emoji
        self.tooltip = Content.from_text(tool.description, markup=False)
        self.initial_args = initial_args

    @staticmethod
    def _camel_to_words(text: str) -> str:
        return re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)

    def compose(self) -> ComposeResult:
        with TabbedContent("Arguments", "Result"):
            yield ReactiveMarkdown(
                markdown=self.initial_args or "👻",
                id=f"{self.id}_args",
                refresh_rate=self.refresh_rate,
                follow=self.follow,
            )

            yield ReactiveMarkdown(
                markdown="",
                id=f"{self.id}_result",
                refresh_rate=self.refresh_rate,
                follow=self.follow,
            )

    def watch_state(self, state: str) -> None:
        """Override base method to also finish markdown widgets."""
        super().watch_state(state)
        if state in ["completed", "failed"]:
            self.query_one(f"#{self.id}_result", ReactiveMarkdown).finish()
            self.query_one(f"#{self.id}_args", ReactiveMarkdown).finish()

    def append_args(self, accumulated: str) -> None:
        try:
            args = self.query_one(f"#{self.id}_args", ReactiveMarkdown)
            args.update('```json\n' + accumulated + '\n```')
        except Exception as e:
            self.app.exit(message=str(e))

    def append_result(self, json_result: str) -> None:
        try:
            self.query_one(f"#{self.id}_result", ReactiveMarkdown).update('```json\n' + json_result + '\n```')
        except Exception as e:
            self.app.exit(message=str(e))
