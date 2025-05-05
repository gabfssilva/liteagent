"""Internal chat view widget for displaying team dispatches in the chat interface."""

import time
from textual.app import ComposeResult
from textual.widgets import Static, TabbedContent
from textual.reactive import reactive

from liteagent import Agent
from .reactive_markdown import ReactiveMarkdown


class InternalChatView(Static):
    """Widget that displays an internal chat view for team dispatches."""
    
    prompt = reactive("")
    state = reactive("waiting")
    frame = reactive(0)
    elapsed = reactive(0)
    start = reactive(0)

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
        super().__init__(
            id=id,
            classes=classes
        )

        self.agent_name = name
        self.pretty_name = name.replace("redirection", "").replace("_", " ").title()

        if prompt and isinstance(prompt, dict) and len(prompt) == 1 and "prompt" in prompt:
            prompt = prompt["prompt"]

        self._prompt = prompt or ""
        self.agent = agent
        self.border_title = f"🤖 {self.pretty_name} ⚪"
        self.border_subtitle = f"{agent.provider}"
        self.loop_id = loop_id
        self.refresh_rate = refresh_rate

    def compose(self) -> ComposeResult:
        with TabbedContent("Prompt", "Result", classes="internal-chat-view"):
            yield ReactiveMarkdown(self._prompt, refresh_rate=self.refresh_rate)
            
            # To avoid circular imports, import ChatView here
            from .chat_view import ChatView
            yield ChatView(
                agent=self.agent,
                parent_id=self.id,
                refresh_rate=1 / 3,
                follow=False,
                loop_id=self.loop_id,
            )

    def on_mount(self) -> None:
        self.state = "waiting"
        self.start = time.perf_counter()
        self._timer = self.set_interval(0.5, self._blink)
        self._elapsed_timer = self.set_interval(0.1, self._elapsed)

    def _elapsed(self):
        self.elapsed = time.perf_counter() - self.start

    def _blink(self) -> None:
        if self.state == "waiting":
            if self.frame == 0:
                self.frame = 1
            else:
                self.frame = 0

    def update_prompt(self, prompt):
        self.query_one(ReactiveMarkdown).update(prompt)

    def watch_frame(self, frame):
        emoji = "⚪" if frame == 0 else "  "
        self.border_title = f"🤖 {self.pretty_name} {emoji}"

    def watch_state(self, state: str) -> None:
        if state == "completed":
            self._timer.stop()
            self._elapsed_timer.stop()
            # We need to avoid circular imports
            from .chat_view import ChatView
            self.query_one(ChatView).mark_completed()
            self.border_title = f"🤖 {self.pretty_name} 🟢"
        elif state == "failed":
            self._timer.stop()
            self._elapsed_timer.stop()
            from .chat_view import ChatView
            self.query_one(ChatView).mark_completed()
            self.border_title = f"🤖 {self.pretty_name} 🔴"

    def watch_elapsed(self, elapsed):
        self.border_subtitle = f"{self.agent.provider} {elapsed:.1f}s"

    def complete(self, failed: bool) -> None:
        self.state = "failed" if failed else "completed"

    def args_completed(self):
        self.query_one(ReactiveMarkdown).finish()

    async def handle_error(self, error) -> None:
        self.state = "failed"
        error_message = f"error: {error}"
        
        # We need to avoid circular imports
        from .chat_view import ChatView
        await self.query_one(ChatView).mount(ReactiveMarkdown(error_message))