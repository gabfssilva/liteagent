from pydantic import Field

from liteagent import agent, tool, ToolDef, ImageURL, ImagePath
from liteagent.provider import Provider


def vision(
    provider: Provider = None,
    *,
    name: str = 'Vision Agent',
    system_message: str = 'Your job is to make accurate statements on a particular image based on the provided instructions.',
) -> ToolDef:
    if not provider:
        from ..providers.providers import ollama
        provider = ollama(model='moondream:1.8b')

    @tool(
        name='vision',
        emoji='👀',
        description='Analyzes the specified image and provides a detailed explanation of its contents.'
    )
    @agent(
        name=name,
        system_message=system_message,
        provider=provider
    )
    async def vision_agent(
        instructions: str = Field(...,
                                  description='A comprehensive instruction of what you need to know about the picture. Do not spare words.'),
        image: ImageURL | ImagePath = Field(..., description='The image content.')
    ) -> str: pass

    return vision_agent
