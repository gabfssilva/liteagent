"""Chat application using the Textual library."""
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Grid
from textual.widgets import Input, Button, Markdown, Static, Footer

from ..textual.styles import light_theme, CHAT_CSS
from ..textual.widgets import ToolCallWidget, PythonRunnerWidget
from ...agent import Agent
from ...message import AssistantMessage, ToolMessage, ToolRequest, BaseModel

class ChatApp(App):
    CSS = CHAT_CSS

    def __init__(
        self,
        agent: Agent,
        session_getter,
        *,
        theme: str = "nord",
        initial_message: str = None,
        exit_command: str = "exit",
    ):
        super().__init__()
        self.register_theme(light_theme)
        self.session = session_getter(agent)
        self.is_processing = False
        self.stream_widget: Optional[Markdown] = None
        self.theme = theme
        self.title = f'🤖 {agent.name}'
        self.pending_tools: list[tuple[str, ToolCallWidget]] = []
        self.exit_command = exit_command
        self.agent = agent

        self.initial_message = initial_message
        if not self.initial_message:
            self.initial_message = f"Chat with {agent.name}"

    def compose(self) -> ComposeResult:
        with Grid(id="app"):
            with VerticalScroll(id="chat-container"):
                from art import text2art
                yield Static(text2art(self.initial_message, font='tarty2'), id="chat-art")

            yield Input(placeholder="What's on your mind?", id="message-input")

        yield Footer()

    def on_mount(self) -> None:
        self.chat_container = self.query_one("#chat-container", VerticalScroll)
        self.query_one("#message-input").focus()

    def on_key(self, event) -> None:
        if event.key == "c" and event.ctrl:
            self.exit()

    def on_unmount(self) -> None:
        self.session.reset()

    def add_message(self, text: str) -> Static:
        widget = Markdown(text, classes="chat-box")
        self.chat_container.mount(widget)
        return widget

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not self.is_processing and event.value.strip():
            await self.process_message(event.value.strip())
            event.input.value = ""

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-button" and not self.is_processing:
            input_widget = self.query_one("#message-input")
            message = input_widget.value.strip()
            if message:
                input_widget.value = ""
                await self.process_message(message)

    async def process_message(self, message: str) -> None:
        if message.lower() == self.exit_command:
            self.exit()
            return

        self.add_message(f"👤 ▷ 🤖: {message}")
        self.is_processing = True
        self.run_worker(self._process_response(message), exclusive=True)
        self.query_one("#message-input").focus()

    async def _process_response(self, message: str) -> None:
        try:
            last = None
            current_assistant_message = None

            async for current in self.session(message):
                def is_assistant_speaking():
                    return (
                        last and last.role == "assistant"
                        and isinstance(last.content, str)
                        and (current.role == "assistant" or not isinstance(current.content, str))
                    )

                if last and last.role == "assistant" and isinstance(last.content, str):
                    if current.role != "assistant" or not isinstance(current.content, str):
                        self.stream_widget = None
                        last = None
                        continue

                match current:
                    case AssistantMessage(content=ToolRequest(name="python_runner") as tool_request):
                        widget = PythonRunnerWidget(
                            emoji='🐍',
                            name='Python Runner',
                            args=tool_request.arguments or {},
                            theme=self.theme,
                        )

                        await self.chat_container.mount(widget)
                        self.pending_tools.append(("python_runner", widget))

                    case AssistantMessage(content=ToolRequest(name=name) as tool_request):
                        tool = self.agent.tool_by_name(name)
                        emoji = tool.emoji if tool else "🔧"

                        widget = ToolCallWidget(
                            emoji=emoji,
                            name=name,
                            args=tool_request.arguments or {},
                            theme=self.theme,
                        )

                        await self.chat_container.mount(widget)
                        self.pending_tools.append((name, widget))

                    case AssistantMessage(content=BaseModel() as content):
                        self.add_message("🤖 ▷ 👤:\n")
                        self.add_message(f"```json\n{content.model_dump_json(indent=2)}\n```")

                    case AssistantMessage(content=str() as text):
                        if not is_assistant_speaking() or not self.stream_widget:
                            current_assistant_message = "🤖 ▷ 👤:\n"
                            self.stream_widget = self.add_message(current_assistant_message)

                        if self.stream_widget:
                            current_assistant_message = current_assistant_message + text
                            await self.stream_widget.update(current_assistant_message)

                    case ToolMessage(content=content, name=name):
                        for i, (pending_name, widget) in enumerate(self.pending_tools):
                            if pending_name == name:
                                await widget.set_response(content)
                                self.pending_tools.pop(i)
                                break

                last = current
                self.chat_container.scroll_end()

            if last and last.role == "assistant" and isinstance(last.content, str):
                self.stream_widget = None

        except Exception as e:
            self.add_message(f"⚠️ Got an error: {e}")
        finally:
            self.is_processing = False
