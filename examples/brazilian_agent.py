import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import brasil_api


@agent(
    tools=[brasil_api],
    provider=openai(),
)
async def brazilian_agent() -> str:
    """ what's the current CDI rate?  """

if __name__ == "__main__":
    asyncio.run(brazilian_agent())
