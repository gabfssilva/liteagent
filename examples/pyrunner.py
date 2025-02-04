import asyncio

from liteagent import Agent, agent
from liteagent.providers.providers import openai, ollama
from liteagent.tools import py


@agent(
    description="You are a python runner. You resolve all of your tasks using Python.",
    tools=[py.python_runner],
    provider=ollama(model='llama3.2')
)
async def code_runner() -> str:
    """ Send a get to https://api64.ipify.org?format=json, and retrieve my ip address. """


asyncio.run(code_runner())
