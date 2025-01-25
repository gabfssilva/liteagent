from typing import Callable

import httpx

from liteagent import Tool, tool


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

        http_tool.function = http_function

        return http_tool

    return decorator
