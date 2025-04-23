import asyncio

from liteagent import agent, chat
from liteagent.providers import openai
from liteagent.tools import duckduckgo, files, browser


@chat.terminal(logo="Chatbot")
@agent(provider=openai(model="gpt-4.1"), tools=[
    duckduckgo,
    files("/Users/gabriel.fdossantos/Downloads/test"),
    browser
])
async def chatbot() -> str: pass


if __name__ == "__main__":
    asyncio.run(chatbot())
