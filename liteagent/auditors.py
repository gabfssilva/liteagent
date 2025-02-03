from typing import AsyncIterator

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.pretty import Pretty
from rich.rule import Rule
from typing_extensions import Callable

from liteagent import Message, AssistantMessage, ToolRequest
from liteagent.agent import AsyncInterceptor

styles = {
    "user": "bold blue",
    "assistant": "bold green",
    "system": "bold yellow",
    "tool": "bold magenta",
}


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
