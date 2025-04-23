import inspect
from typing import List, Callable, Any

from .agent import Agent, AsyncInterceptor
from .provider import Provider
from .tool import ToolDef, FunctionToolDef


def tool(name: str = None, eager: bool = False, emoji: str = '🔧') -> ToolDef | Callable[..., ToolDef]:
    def decorator(function) -> ToolDef:
        return FunctionToolDef(function, name, eager, emoji)

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

        if len(signature.parameters) == 0:
            from inspect import Parameter

            signature = signature.replace(parameters=[
                Parameter("prompt", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
            ])

            if user_prompt_template is None or user_prompt_template.strip() == "" :
                user_prompt_template = "{prompt}"

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
