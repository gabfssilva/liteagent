import asyncio

from liteagent import agent, chat
from liteagent.providers import openai
from liteagent.tools import duckduckgo, files, browser


# @chat.terminal(logo="Chatbot")
@agent(provider=openai(model="gpt-4.1"), tools=[
    duckduckgo,
    files("/Users/gabriel.fdossantos/Downloads/test"),
    browser
])
async def chatbot() -> str: pass

async def main():
    session = chatbot.stateful()

    async for message in session("go to google.com"):
        print(message.acontent())

    async for message in session("now to uol.com.br"):
        print(message.acontent())


if __name__ == "__main__":
    print(asyncio.run(chatbot("go to google.com")))
    print(asyncio.run(chatbot("go to uol.com.br")))
