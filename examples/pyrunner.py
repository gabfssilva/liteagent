from liteagent import Agent, agent
from liteagent.providers import ollama
from liteagent.tools import py

import asyncio


@agent(
    description="You're a python runner",
    tools=[py.python_runner],
    provider=ollama(model='qwen2.5-coder:7b')
)
def code_runner() -> Agent: ...


async def main():
    await code_runner("2+2=?")
    await code_runner("Send a get to https://api.ipify.org?format=json and get my ip")


if __name__ == '__main__':
    asyncio.run(main())
