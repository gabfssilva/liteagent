"""Terminal-based chat interface using Textual."""
from typing import Optional, AsyncIterator

from ..agent import Agent
from ..message import Message


def terminal(
    agent_f: Optional[Agent[AsyncIterator[Message]]] = None,
    *,
    theme: str = "gruvbox",
    logo: str = None,
):
    """
    Create a terminal-based chat interface for an agent.
    
    Args:
        agent_f: The agent to chat with
        exit_command: The command to exit the chat
        theme: The theme to use for syntax highlighting
        logo: The initial message to display
    
    Returns:
        A decorator that can be used to wrap an agent function
    """

    def decorator(agent: Agent[AsyncIterator[Message]]):
        async def chat_loop():
            from .textual.app import ChatApp

            app = ChatApp(
                agent=agent,
                theme=theme,
                logo=logo,
            )

            await app.run_async()

        return chat_loop

    if agent_f is None:
        return decorator
    return decorator(agent_f)
