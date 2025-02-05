import asyncio

from liteagent import agent
from liteagent.providers import openai, ollama, deepseek
from liteagent.tools import memoria, ipify


@agent(
    provider=openai(model='gpt-4o'),
    tools=[memoria(), ipify]
)
async def memorizer() -> str: ...


async def main():
    await memorizer(
        "my name is Gabriel. can I count on you to remember it later? Also, can you also check my IP address and also remember it for me later?")
    print()
    print('-' * 100)
    await memorizer("what was my name again? what about my IP?")


asyncio.run(main())
