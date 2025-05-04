import asyncio

from liteagent import agent, bus
from liteagent.events import Event
from liteagent.providers import openai
from liteagent.tools import duckduckgo, vision


@agent(provider=openai(), tools=[duckduckgo()])
async def searcher() -> str: pass


@agent(provider=openai(), tools=[vision(provider=openai(model='gpt-4.1'))])
async def viewer() -> str: pass


@agent(provider=openai(model='gpt-4.1'), team=[searcher, viewer])
async def chatbot() -> str: pass


@bus.on(Event)
async def listen(event: Event):
    print(event)


if __name__ == "__main__":
    asyncio.run(chatbot("search about trump"))
