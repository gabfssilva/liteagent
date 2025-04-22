import asyncio

from liteagent import agent, chat
from liteagent.providers import openai
from liteagent.tools import duckduckgo, crawl4ai, memoria


@chat.terminal(logo="Chatbot")
@agent(provider=openai(model="gpt-4.1"), tools=[duckduckgo, crawl4ai, memoria()])
async def chatbot(): pass


if __name__ == "__main__":
    asyncio.run(chatbot())
