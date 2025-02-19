import asyncio

from liteagent import agent, ImageURL
from liteagent.providers import openai, ollama
from liteagent.tools import vision


@agent(
    description="You're a vision agent. You explain what you see based on the user input.",
    provider=openai(model='o3-mini'),
    tools=[vision()]
)
async def vision_via_tool_agent() -> str: ...

@agent(
    description="You're a vision agent. You explain what you see based on the user input.",
    provider=openai(model='gpt-4o-mini'),
)
async def vision_agent(question: str, image: ImageURL) -> str: ...


async def main():
    # some models do not have vision capabilities
    # you can use the vision tool instead, and the tool itself delegates the task for a vision-enabled model.
    await vision_via_tool_agent(
        "what is the cat wearing on this picture? https://img.buzzfeed.com/buzzfeed-static/static/2022-09/6/17/asset/15e2b0da8566/sub-buzz-677-1662483766-1.jpg",
    )

    # vision-ready agents must receive the ImageURL or ImageBase64 classes to be provided in the content.
    await vision_agent(
        "what is the cat wearing on this picture?",
        ImageURL(url="https://img.buzzfeed.com/buzzfeed-static/static/2022-09/6/17/asset/15e2b0da8566/sub-buzz-677-1662483766-1.jpg"),
    )

asyncio.run(main())
