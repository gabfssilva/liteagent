import asyncio

from liteagent import agent
from liteagent.providers import ollama
from liteagent.tools import py


@agent(
    description="You are a python runner. You resolve all of your tasks using Python.",
    tools=[py.python_runner],
    provider=ollama(model='llama3.2:3b')
)
async def code_runner() -> str:
    """ Send a get to https://api64.ipify.org?format=json, and retrieve my ip address. """


if __name__ == '__main__':
    asyncio.run(code_runner())
