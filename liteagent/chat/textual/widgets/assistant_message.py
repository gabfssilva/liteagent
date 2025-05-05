"""Assistant message widget for displaying AI responses in the chat interface."""

from textual import events
from textual.app import ComposeResult
from textual.reactive import reactive

from liteagent import Agent
from .base_widget import BaseMessageWidget
from .reactive_markdown import ReactiveMarkdown


class AssistantMessageWidget(BaseMessageWidget):
    """Widget that displays an assistant message with real-time updates."""

    assistant_content = reactive("")
    finished = reactive(False)

    def __init__(
        self,
        id: str,
        agent: Agent,
        refresh_rate: float = 0.5,
        follow: bool = False,
        classes: str = "assistant-message",
    ):
        super().__init__(
            id=id,
            name=agent.name,
            emoji="🤖",
            subtitle=f'{agent.provider}',
            refresh_rate=refresh_rate,
            follow=follow,
            classes=classes
        )
        self.provider_name = agent.provider

    def message_children(self) -> ComposeResult:
        yield ReactiveMarkdown(
            refresh_rate=self.refresh_rate,
            follow=self.follow,
            markdown=self.assistant_content,
            finished=self.finished
        )

    def watch_assistant_content(self, assistant_content: str):
        if not self.collapsed:
            try:
                self.query_one(ReactiveMarkdown).update(assistant_content)
            except Exception as e:
                pass

    def watch_finished(self, finished: bool):
        if finished:
            self.complete()
            if not self.collapsed:
                self.query_one(ReactiveMarkdown).finish()

    def finish(self):
        self.finished = True

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button == 3:  # Right click
            self.app.copy_to_clipboard(self.assistant_content)
            self.notify("Copied to clipboard! ✅", severity="information")
