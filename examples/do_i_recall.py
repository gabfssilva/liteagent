import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import memoria, ipify


@agent(
    provider=openai(model='gpt-4o-mini'),
    tools=[memoria(), ipify]
)
async def memorizer() -> str: ...


async def main():
    await memorizer("Check my IP address. Also, my name is Gabriel. You have to remember both for me.")
    await memorizer("what was my name again? what about my IP?")

if __name__ == "__main__":
    asyncio.run(main())
