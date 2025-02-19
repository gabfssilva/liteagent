import inspect
from typing import List, Callable

from pydantic import Field, create_model
from pydantic.fields import FieldInfo

from .agent import Agent, AsyncInterceptor
from .auditors import console, minimal
from .providers import Provider
from .tool import Tool, ToolDef


def tool(name: str = None, eager: bool = False, emoji: str = '🔧') -> Tool:
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
            handler=function,
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
    intercept: AsyncInterceptor | None = minimal()
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
    tools: List[Tool | Callable] = None,
    intercept: AsyncInterceptor | None = minimal(),
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
