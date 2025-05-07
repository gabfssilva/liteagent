"""Tool use widget for displaying tool executions in the chat interface."""

import re

from textual.app import ComposeResult
from textual.widgets import TabbedContent
from textual.content import Content
from textual.reactive import var, reactive

from liteagent import Tool
from .base_widget import BaseMessageWidget
from .reactive_markdown import ReactiveMarkdown


class ToolUseWidget(BaseMessageWidget):
    """Widget that displays a tool use with arguments and results."""

    tool_name = var("")
    tool_emoji = var("")
    arguments = reactive("", init=False)
    result = reactive("", init=False)
    finished_arguments = reactive(False)
    finished_result = reactive(False)

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
            classes=classes,
            collapsed=True
        )
        self.tool_name = formatted_name
        self.tool_emoji = tool.emoji
        self.tooltip = Content.from_text(tool.description, markup=False)
        self.initial_args = initial_args

    @staticmethod
    def _camel_to_words(text: str) -> str:
        return re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)

    def message_children(self) -> ComposeResult:
        with TabbedContent("Arguments", "Result"):
            yield ReactiveMarkdown(
                markdown=self.arguments or "👻",
                id=f"{self.id}_args",
                refresh_rate=self.refresh_rate,
                follow=self.follow,
                finished=self.finished_arguments,
            )

            yield ReactiveMarkdown(
                markdown=self.result,
                id=f"{self.id}_result",
                refresh_rate=self.refresh_rate,
                finished=self.finished_result,
            )

    def watch_arguments(self, arguments: str):
        self.query_one(f"#{self.id}_args", ReactiveMarkdown).update(arguments)

    def watch_result(self, result: str):
        self.query_one(f"#{self.id}_result", ReactiveMarkdown).update(result)

    def watch_state(self, state: str) -> None:
        super().watch_state(state)
        if state in ["completed", "failed"]:
            self.finished_arguments = True
            self.finished_result = True

            self.query_one(f"#{self.id}_result", ReactiveMarkdown).finish()
            self.query_one(f"#{self.id}_args", ReactiveMarkdown).finish()

    def append_args(self, accumulated: str) -> None:
        self.arguments = '```json\n' + accumulated + '\n```'

    def append_result(self, json_result: str) -> None:
        self.result = '```json\n' + json_result + '\n```'
