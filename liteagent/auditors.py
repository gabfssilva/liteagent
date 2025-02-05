from typing import AsyncIterator

from pydantic import BaseModel, JsonValue
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.pretty import Pretty
from rich.rule import Rule
from rich.text import Text
from typing_extensions import Callable

from liteagent import Message, AssistantMessage, ToolRequest, UserMessage, ToolMessage
from liteagent.agent import AsyncInterceptor

styles = {
    "user": "bold blue",
    "assistant": "bold green",
    "system": "bold yellow",
    "tool": "bold magenta",
}


def minimal(console: Console = Console(), truncate: int = 80):
    async def auditor(agent, messages: AsyncIterator[Message]) -> AsyncIterator[Message]:
        def msg(text: str) -> str:
            return f'({agent.name}) {text}'

        with Live(console=console, refresh_per_second=10) as live:
            current_assistant_message = msg('🤖 ▷ 👤: ')

            async for current in messages:
                yield current

                match current:
                    case UserMessage(content=str() as content):
                        console.print(Markdown(msg(f'👤 ▷ 🤖: {content}'), code_theme="ansi-light"))

                    case AssistantMessage(content=ToolRequest() as tool_request):
                        if tool_request.arguments is None or tool_request.arguments == '{}':
                            args_as_str = ''
                        else:
                            args_as_str = ','.join([f'{k}={v}' for k, v in tool_request.arguments.items()])

                        as_str = f'{tool_request.name}({args_as_str})'

                        prefix = '🤖 ▷ 🔧' if tool_request.origin == 'model' else '↪ 🔧'

                        console.print(msg(f'{prefix}: {as_str}'))

                    case AssistantMessage(content=str() as content):
                        current_assistant_message += content

                        live.update(Markdown(current_assistant_message, code_theme="ansi-light"))
                    case ToolMessage(content=content, name=name):
                        content = str(content)

                        if len(content) > truncate:
                            content = str(content)[:truncate]
                            content = content + " [bold]...[/bold]"

                        console.print(msg(f'🔧 ▷ 🤖: {name}() = {content}'))

    return auditor


def console(
    console: Console = Console(),
    ignore: list[Callable[[Message], bool]] = None,
) -> AsyncInterceptor:
    if ignore is None:
        ignore = [
            lambda m: m.role == "system"
        ]

    async def auditor(agent, messages: AsyncIterator[Message]) -> AsyncIterator[Message]:
        assistant_message = ""

        async for current in messages:
            yield current

            if ignore and any(f(current) for f in ignore):
                continue

            if current.role == 'assistant' and not isinstance(current.content, ToolRequest):
                if agent.respond_as and not isinstance(current.content, agent.respond_as):
                    continue

                if isinstance(current, AssistantMessage) and isinstance(current.content, str) and len(
                    current.content) > 0:
                    assistant_message = assistant_message + current.content
                    continue

            title, pretty = current.pretty()
            separator = Rule(style="dim", title=title)

            if len(assistant_message) > 0:
                console.print(
                    Group(
                        Rule(style="dim", title='Assistant'),
                        Markdown(assistant_message),
                    )
                )

                assistant_message = ""

            if pretty:
                console.print(
                    Group(separator, pretty),
                    style=styles[current.role]
                )

        if assistant_message != "":
            console.print(
                Group(
                    Rule(style="dim", title='Assistant'),
                    Markdown(assistant_message),
                )
            )

    return auditor
