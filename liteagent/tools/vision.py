

from functools import partial
from typing import Callable

from pydantic import Field
from liteagent import Agent, agent, tool, Tool
from liteagent.message import ImageURL, TextContent
from liteagent.providers import Provider
from liteagent.providers import ollama


def vision(
    name: str='Vision Agent', 
    system_message: str='Your job is to make accurate statements on a particular image based on the provided instructions.',
    provider: Provider=ollama(model='moondream:1.8b')
) -> Tool:
    @agent(
        name=name,
        system_message=system_message,
        provider=provider,
        intercept=None
    )
    async def vision_agent() -> str: ...

    @tool(name='vision', emoji='👀')
    async def vision_tool(
        instructions: str = Field(..., description='A comprehensive instruction of what you need to know about the picture. Do not spare words.'),
        image_url: str = Field(..., description='The image URL.')
    ) -> str:
        """ use this tool for vision capabilities. """

        return await vision_agent(instructions, ImageURL(url=image_url))

    return vision_tool
