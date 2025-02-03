import asyncio

from liteagent import Agent, agent
from liteagent.providers.providers import openai, ollama
from liteagent.tools import py


@agent(
    description="You are a python runner. You resolve all of your tasks using Python.",
    tools=[py.python_runner],
    provider=ollama(model='qwen2.5-coder:7b')
)
async def code_runner() -> str: ...


async def main():
    await code_runner("using py_runner, send a get to https://api64.ipify.org?format=json and get my ip")


if __name__ == '__main__':
    asyncio.run(main())
