import asyncio

from liteagent import agent
from liteagent.providers import openai, deepseek
from liteagent.tools import duckduckgo, vision


@agent(provider=deepseek(), tools=[duckduckgo()])
async def searcher() -> str: pass


@agent(provider=deepseek(), tools=[vision(provider=openai(model='gpt-4.1'))])
async def viewer() -> str: pass


@agent(provider=deepseek(), team=[searcher, viewer])
async def chatbot() -> str: pass


if __name__ == "__main__":
    asyncio.run(chatbot("search about trump"))
