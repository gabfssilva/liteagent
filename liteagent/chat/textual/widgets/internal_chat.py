"""Internal chat view widget for displaying team dispatches in the chat interface."""

from textual.app import ComposeResult
from textual.widgets import TabbedContent
from textual.reactive import reactive

from liteagent import Agent
from .base_widget import BaseMessageWidget
from .reactive_markdown import ReactiveMarkdown


class InternalChatWidget(BaseMessageWidget):
    """Widget that displays an internal chat view for team dispatches."""

    prompt = reactive("", init=False)

    finished_prompt = reactive(False, init=False)
    finished_result = reactive(False, init=False)

    def __init__(
        self,
        *,
        id: str,
        name: str,
        prompt: dict | list | str | None,
        agent: Agent,
        loop_id: str | None = None,
        refresh_rate: float = 0.5,
        classes: str = "tool-message"
    ):
        pretty_name = name.replace("redirection", "").replace("_", " ").title()

        super().__init__(
            id=id,
            name=pretty_name,
            emoji="🤖",
            subtitle=f'{agent.provider}',
            refresh_rate=refresh_rate,
            follow=False,
            classes=classes,
            collapsed=True
        )

        self.agent_name = name

        if prompt and isinstance(prompt, dict) and len(prompt) == 1 and "prompt" in prompt:
            prompt = prompt["prompt"]

        self.prompt = prompt or ""
        self.agent = agent
        self.loop_id = loop_id

        from .chat_view import ChatWidget

        self.chat_widget: ChatWidget = ChatWidget(
            agent=self.agent,
            parent_id=self.id,
            refresh_rate=1 / 3,
            follow=False,
            loop_id=self.loop_id,
            id=f"{self.id}_chat"
        )

    def message_children(self) -> ComposeResult:
        with TabbedContent("Prompt", "Result", classes="internal-chat-view"):
            yield ReactiveMarkdown(
                markdown=self.prompt,
                refresh_rate=self.refresh_rate,
                id=f"{self.id}_prompt",
                finished=self.finished_prompt,
                follow=self.follow,
            )

            yield self.chat_widget

    def watch_prompt(self, prompt: str):
        self.query_one(f"#{self.id}_prompt", ReactiveMarkdown).update(prompt)

    def update_prompt(self, prompt):
        self.prompt = prompt

    def watch_state(self, state: str) -> None:
        super().watch_state(state)
        
        if state == "completed" or state == "failed":
            self.finished_prompt = True
            self.finished_result = True

    def watch_finished_result(self, finished_result: bool):
        if finished_result:
            from .chat_view import ChatWidget
            self.query_one(f"#{self.id}_chat", ChatWidget).mark_completed()

    def watch_finished_prompt(self, finished_prompt: bool):
        if finished_prompt:
            self.query_one(f"#{self.id}_prompt", ReactiveMarkdown).finish()

    def args_completed(self):
        self.finished_prompt = True

    async def handle_error(self, error) -> None:
        self.state = "failed"
        error_message = f"error: {error}"
        from .chat_view import ChatWidget
        await self.query_one(f"#{self.id}_chat", ChatWidget).mount(ReactiveMarkdown(error_message))
