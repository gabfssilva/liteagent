import asyncio

from liteagent import agent, chat
from liteagent.providers import ollama
from liteagent.tools import duckduckgo, files, terminal


@chat.terminal(logo="Chatbot")
@agent(provider=ollama(), tools=[
    duckduckgo,
    files("/Users/gabrielfrancisco/Downloads/test"),
    terminal("/Users/gabrielfrancisco/Downloads/test")
])
async def chatbot() -> str: pass


if __name__ == "__main__":
    asyncio.run(chatbot())
