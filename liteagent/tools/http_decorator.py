import functools
import inspect
from typing import Literal

import httpx


def http(
    url: str,
    method: str = "GET",
    headers: dict = None,
    params: dict = None,
    body: str = None,
    accept: Literal["json", "xml", "rss", "text", "binary"] = "json"
):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import xml.etree.ElementTree as ET
            import feedparser
            
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Add self attributes to format context if available
            format_context = dict(bound_args.arguments)
            if args and hasattr(args[0], "__dict__"):
                self_obj = args[0]
                for attr_name, attr_value in self_obj.__dict__.items():
                    if attr_name not in format_context:
                        format_context[attr_name] = attr_value

            formatted_url = url.format(**format_context)
            formatted_headers = {k: v.format(**format_context) for k, v in (headers or {}).items()}
            formatted_params = {k: v.format(**format_context) for k, v in (params or {}).items()}
            formatted_body = body.format(**format_context) if body else None

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    formatted_url,
                    headers=formatted_headers,
                    params=formatted_params,
                    json=formatted_body if method in ["POST", "PUT", "PATCH"] else None
                )
                response.raise_for_status()

                if accept == "json":
                    return response.json()
                elif accept == "xml":
                    return ET.fromstring(response.text)
                elif accept == "rss":
                    return feedparser.parse(response.text)
                elif accept == "text":
                    return response.text
                elif accept == "binary":
                    return response.content

        return wrapper

    return decorator
