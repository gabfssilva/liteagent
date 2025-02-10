from typing import AsyncIterator

from pydantic import BaseModel
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.padding import Padding
from rich.pretty import Pretty
from rich.syntax import Syntax

from liteagent import Message, AssistantMessage, ToolRequest, UserMessage, ToolMessage

console = Console()
live = Live(console=console, refresh_per_second=10)
live.start()

import atexit


def exit_handler():
    live.stop()


atexit.register(exit_handler)


def minimal(truncate: int = 80):
    async def auditor(agent, messages: AsyncIterator[Message]) -> AsyncIterator[Message]:
        def msg(text: str) -> str:
            return f'({agent.name}) {text}'

        outputs = []
        assistant_index = None
        current_assistant_message = ""
        last = None

        def add_output(renderable):
            outputs.append(renderable)
            live.update(Group(*outputs))

        async for current in messages:
            yield current

            match current:
                case UserMessage(content=str() as content):
                    add_output(msg("👤 ▷ 🤖:"))
                    add_output(Padding(Markdown(content, code_theme="ansi-light"), pad=(0, 0, 0, 4)))

                case AssistantMessage(content=ToolRequest(name="python_runner") as tool_request):
                    prefix = "🤖 ▷ 🐍:" if tool_request.origin == "model" else "↪ 🐍:"
                    add_output(msg(prefix))
                    add_output(
                        Padding(
                            Syntax(tool_request.arguments["script"], "python", theme="ansi-light"),
                            pad=(0, 0, 0, 4),
                        )
                    )

                case AssistantMessage(content=ToolRequest() as tool_request):
                    if tool_request.arguments is None or tool_request.arguments == "{}":
                        args_as_str = ""
                    else:
                        args_as_str = ",".join(
                            [f"{k}={v}" for k, v in tool_request.arguments.items()]
                        )
                    as_str = f"{tool_request.name}({args_as_str})"
                    prefix = "🤖 ▷ 🔧:" if tool_request.origin == "model" else "↪ 🔧:"
                    add_output(msg(prefix))
                    add_output(Padding(as_str, pad=(0, 0, 0, 4)))

                case AssistantMessage(content=BaseModel() as content) if agent.respond_as:
                    add_output(msg("🤖 ▷ 👤:"))
                    add_output(Padding(Pretty(content), pad=(0, 0, 0, 4)))

                case AssistantMessage(content=str() as content) if not agent.respond_as:
                    if len(content.strip()) == 0:
                        continue

                    if not last or (last.role != "assistant" or isinstance(last.content, ToolRequest)):
                        add_output(msg("🤖 ▷ 👤:"))
                        assistant_index = len(outputs)
                        outputs.append(Padding(Markdown("", code_theme="ansi-light"), pad=(0, 0, 0, 4)))
                        live.update(Group(*outputs))
                        current_assistant_message = ""

                    current_assistant_message += content
                    outputs[assistant_index] = Padding(
                        Markdown(current_assistant_message, code_theme="ansi-light"), pad=(0, 0, 0, 4)
                    )
                    live.update(Group(*outputs))

                case ToolMessage(content=BaseModel() as content, name="python_runner"):
                    add_output(msg("🐍 ▷ 🤖:"))
                    add_output(Padding(content, pad=(0, 0, 0, 4)))

                case ToolMessage(content=content, name=name):
                    content = str(content)
                    if len(content) > truncate:
                        content = content[:truncate] + " [bold]...[/bold]"
                    add_output(msg("🔧 ▷ 🤖:"))
                    add_output(Padding(f"{name}() = {content}", pad=(0, 0, 0, 4)))

            last = current

    return auditor
