import asyncio

from liteagent import agent
from liteagent.providers import openai, deepseek
from liteagent.tools import duckduckgo, vision


@agent(provider=deepseek(), tools=[duckduckgo()])
async def searcher() -> str: pass


@agent(provider=deepseek(), description="Evaluate from 1-5 the story provided to you.")
async def story_evaluator() -> str: pass


@agent(provider=openai(), tools=[vision(provider=openai(model='gpt-4.1'))])
async def viewer() -> str: pass


@agent(provider=openai(), team=[searcher, viewer, story_evaluator])
async def chatbot() -> str: pass


if __name__ == "__main__":
    asyncio.run(chatbot())
