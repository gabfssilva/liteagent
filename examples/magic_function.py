import asyncio

from liteagent import auto_function
from liteagent.providers import ollama

@auto_function(provider=ollama('qwen2.5-coder:7b'))
async def my_ip() -> str:
    """a function that sends a request to: https://api.ipify.org?format=json and extracts the ip."""

@auto_function(provider=ollama('qwen2.5-coder:7b'))
async def add(x: int, y: int) -> int:
    """a function that adds two numbers."""

async def main():
    # the decorator extracts the function’s description and signature,
    # uses an AI agent to asynchronously generate and cache the function implementation.
    #
    # the function body is left blank on purpose as the agent is the one responsible for implementing it.
    # for the user, it's designed to work as if it's a normal function.
    print(await my_ip())

    # much faster, as it only sends the http request, and not the function generation itself.
    print(await my_ip())
    print(await my_ip())

    # once again slower
    print(await add(1, 2))

    # and then faster again. ;)
    print(await add(5, 5))
    print(await add(10, 10))

if __name__ == "__main__":
    asyncio.run(main())
