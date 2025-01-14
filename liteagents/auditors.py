from time import sleep
from typing import List, AsyncIterator

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.rule import Rule
from typing_extensions import Callable

from liteagents import Agent, Message, AssistantMessage
from liteagents.agent import AsyncInterceptor
from liteagents.misc import markdown

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

    async def auditor(agent: Agent, messages: AsyncIterator[Message]) -> AsyncIterator[Message]:
        assistant_message = ""

        async for current in messages:
            yield current

            if ignore and any(f(current) for f in ignore):
                continue

            if isinstance(current, AssistantMessage) and isinstance(current.content, str):
                assistant_message = assistant_message + current.content
                continue

            title, pretty = current.pretty()
            separator = Rule(style="dim", title=title)

            if len(assistant_message) > 0:
                console.print(
                    Group(
                        separator,
                        Markdown(assistant_message),
                    )
                )

                assistant_message = ""

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
