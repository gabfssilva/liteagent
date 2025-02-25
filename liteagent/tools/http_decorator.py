import httpx
import functools
import inspect

def http(url: str, method: str = "GET", headers: dict = None, params: dict = None, body: str = None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            formatted_url = url.format(**bound_args.arguments)
            formatted_headers = {k: v.format(**bound_args.arguments) for k, v in (headers or {}).items()}
            formatted_params = {k: v.format(**bound_args.arguments) for k, v in (params or {}).items()}
            formatted_body = body.format(**bound_args.arguments) if body else None

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    formatted_url,
                    headers=formatted_headers,
                    params=formatted_params,
                    json=formatted_body if method in ["POST", "PUT", "PATCH"] else None
                )
                response.raise_for_status()
                return response.json()

        return wrapper
    return decorator
