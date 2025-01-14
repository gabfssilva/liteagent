from typing import List, Callable

import httpx

from liteagents import Tool, Agent, tool
from liteagents.agent import AsyncInterceptor
from liteagents.auditors import console
from liteagents.providers import Provider, openai


def agent(
    name: str,
    provider: Provider = openai(),
    description: str = None,
    system_message: str = None,
    tools: List[Tool | Callable] = None,
    team: List[Agent | Callable[[], Agent]] = None,
    intercept: AsyncInterceptor = console()
):
    def decorator(*args, **kwargs) -> Agent:
        return Agent(
            name,
            provider,
            description,
            system_message,
            tools,
            team,
            intercept
        )

    return decorator


def http_call(
    url: str,
    method: str = "GET",
    headers: dict = None,
    timeout: int = 10,
    body: dict = None
) -> Callable[[...], Tool]:
    """
    Decorator to create a tool that performs an HTTP call.
    Supports dynamic formatting of the URL, headers, and body.
    """

    def decorator(func: Callable) -> Tool:
        async def http_function(**kwargs) -> dict:
            # Format URL, headers, and body with provided kwargs
            formatted_url = url.format(**kwargs)
            formatted_headers = {k: v.format(**kwargs) for k, v in (headers or {}).items()}
            formatted_body = {k: v.format(**kwargs) for k, v in (body or {}).items()}

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=formatted_url,
                    headers=formatted_headers,
                    json=formatted_body if method in {"POST", "PUT", "PATCH"} else None,
                )
                response.raise_for_status()
                return response.json()

        http_tool = tool(func)

        # Assign the new HTTP function with extended formatting capabilities
        http_tool.function = http_function

        return http_tool

    return decorator
