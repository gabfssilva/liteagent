import asyncio

from liteagent import agent, chat
from liteagent.providers import openai
from liteagent.tools import duckduckgo, files, terminal


@chat.terminal(logo="Chatbot")
@agent(provider=openai(model="gpt-4.1"), tools=[
    duckduckgo,
    files("/Users/gabrielfrancisco/Downloads/test"),
    terminal("/Users/gabrielfrancisco/Downloads/test")
])
async def chatbot() -> str: pass


if __name__ == "__main__":
    asyncio.run(chatbot())
