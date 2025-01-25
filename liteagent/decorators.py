from functools import wraps
from typing import List, Callable

import inspect

from pydantic import Field, create_model
from pydantic.fields import FieldInfo

from .agent import Agent, AsyncInterceptor
from .auditors import console
from .providers import Provider
from .tool import Tool


def tool(name: str = None) -> Tool:
    def decorator(function) -> Tool:
        sig = inspect.signature(function)
        input_fields = [
            (n,
             param.annotation,
             param.default if param.default != param.empty else Field(...))
            for n, param in sig.parameters.items() if n != 'self'
        ]

        field_definitions = {}

        for field_name, field_type, field_default in input_fields:
            if isinstance(field_default, FieldInfo):
                field_definitions[field_name] = (field_type, field_default)
            else:
                field_definitions[field_name] = (field_type, Field(default=field_default))

        function_name = name or function.__name__

        return Tool(
            name=function_name,
            description=(function.__doc__ or f"Tool {function_name}").strip(),
            input=create_model(function_name.capitalize(), **field_definitions),
            handler=function
        )

    if callable(name):
        func = name
        name = None
        return decorator(func)

    return decorator


def agent(
    provider: Provider,
    name: str = None,
    description: str = None,
    system_message: str = None,
    tools: List[Tool | Callable] = None,
    team: List[Agent | Callable[[], Agent]] = None,
    intercept: AsyncInterceptor = console()
) -> Agent:
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
    provider: Provider,
    system_message: str = None,
    tools: List[Tool | Callable] = None,
    intercept: AsyncInterceptor = console()
) -> Agent:
    return agent(
        name=name,
        provider=provider,
        system_message=system_message,
        tools=tools,
        team=team,
        intercept=intercept
    )
