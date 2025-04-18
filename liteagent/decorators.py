import inspect
from typing import List, Callable

from .agent import Agent, AsyncInterceptor
from .provider import Provider
from .tool import Tool, ToolDef, parse_tool


def tool(name: str = None, eager: bool = False, emoji: str = '🔧') -> Tool:
    def decorator(function) -> Tool:
        return parse_tool(
            name=name,
            function=function,
            eager=eager,
            emoji=emoji
        )

    if callable(name):
        func = name
        name = None
        return decorator(func)

    return decorator


def agent[Out](
    provider: Provider,
    name: str = None,
    description: str = None,
    system_message: str = None,
    tools: List[ToolDef] = None,
    team: List[Agent | Callable[[], Agent]] = None,
    intercept: AsyncInterceptor | None = None
) -> Callable[..., Agent[Out]]:
    def decorator(func: Callable) -> Agent[Out]:
        signature = inspect.signature(func)
        user_prompt_template = inspect.getdoc(func)
        default_return_types = [inspect.Signature.empty]
        respond_as = None if signature.return_annotation in default_return_types else signature.return_annotation

        agent_instance = Agent[Out](
            name=name or func.__name__,
            provider=provider,
            description=description,
            system_message=system_message,
            tools=tools,
            team=team,
            intercept=intercept,
            respond_as=respond_as,
            signature=signature,
            user_prompt_template=user_prompt_template
        )

        return inspect.markcoroutinefunction(agent_instance)

    return decorator


def team(
    name: str,
    agents: List[Agent | Callable[[], Agent]],
    provider: Provider,
    system_message: str = None,
    tools: List[ToolDef] = None,
    intercept: AsyncInterceptor | None = None,
    description: str = None
) -> Callable[..., Agent]:
    return agent(
        name=name,
        provider=provider,
        system_message=system_message,
        tools=tools,
        team=agents,
        intercept=intercept,
        description=description
    )
