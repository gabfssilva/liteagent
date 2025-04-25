import asyncio

from liteagent import agent, chat
from liteagent.providers import github, openai
from liteagent.tools import duckduckgo, vision


@chat.terminal(logo="Chatbot")
@agent(provider=github(), tools=[
    duckduckgo(),
    vision(provider=openai(model='gpt-4.1'))
])
async def chatbot() -> str: pass


if __name__ == "__main__":
    asyncio.run(chatbot())
