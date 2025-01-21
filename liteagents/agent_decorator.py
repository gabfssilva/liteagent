from typing import List, Callable

import httpx

from liteagents import Tool, Agent, tool
from liteagents.agent import AsyncInterceptor
from liteagents.auditors import console
from liteagents.providers import Provider, openai

from functools import wraps


def agent(
    name: str = None,
    description: str = None,
    provider: Provider = openai(),
    system_message: str = None,
    tools: List[Tool | Callable] = None,
    team: List[Agent | Callable[[], Agent]] = None,
    intercept: AsyncInterceptor = console()
):
    def decorator(func: Callable) -> Agent:
        @wraps(func)
        def wrapper(*args, **kwargs):
            agent_instance = Agent(
                name=name or func.__name__,
                provider=provider,
                description=func.__doc__ or description,
                system_message=system_message,
                tools=tools,
                team=team,
                intercept=intercept,
            )

            return agent_instance

        return wrapper()

    return decorator


def team(
    name: str,
    team: List[Agent | Callable[[], Agent]],
    provider: Provider = openai(),
    system_message: str = None,
    tools: List[Tool | Callable] = None,
    intercept: AsyncInterceptor = console()
):
    return agent(
        name=name,
        provider=provider,
        system_message=system_message,
        tools=tools,
        team=team,
        intercept=intercept
    )
