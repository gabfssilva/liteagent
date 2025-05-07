"""Terminal-based chat interface using Textual."""
from typing import Optional, AsyncIterable

from ..agent import Agent
from ..bus.eventbus import bus
from ..message import Message


def terminal(
    agent_f: Optional[Agent[AsyncIterable[Message]]] = None,
    *,
    theme: str = "nord",
    logo: str = None,
):
    """
    Create a terminal-based chat interface for an agent.
    
    Args:
        agent_f: The agent to chat with
        theme: The theme to use for syntax highlighting
        logo: The initial message to display
    
    Returns:
        A decorator that can be used to wrap an agent function
    """

    def decorator(agent: Agent[AsyncIterable[Message]]):
        async def chat_loop():
            from .textual.app import ChatApp

            app = ChatApp(
                agent=agent,
                theme=theme,
                logo=logo,
            )

            try:
                await app.run_async()
            finally:
                await bus.stop()

        return chat_loop

    if agent_f is None:
        return decorator

    return decorator(agent_f)
