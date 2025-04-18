import os
from functools import partial

from google import genai
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from liteagent import Provider
from liteagent.providers import OpenAICompatible, Ollama
from liteagent.providers.gemini_provider import Gemini
from liteagent.providers.claude_provider import Claude
from liteagent.providers.azure_ai import AzureAI
from liteagent.internal.cleanup import register_provider

@register_provider
def gemini(
    client: genai.Client = None,
    model: str = "gemini-2.0-flash"
) -> Provider: return Gemini(client or genai.Client(), model)

@register_provider
def ollama(
    model: str = 'llama3.2',
    automatic_download: bool = True
) -> Provider: return Ollama(model=model, automatic_download=automatic_download)

@register_provider
def openai_compatible(
    model: str,
    client: AsyncOpenAI = None,
    base_url: str = None,
    api_key: str = None,
    **kwargs
) -> Provider:
    return OpenAICompatible(
        client=client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=5
        ),
        model=model,
        **kwargs
    )

@register_provider
def azureai(
    model: str = 'gpt-4o-mini',
    base_url: str = 'https://models.inference.ai.azure.com',
    api_key: str = None,
    **kwargs
) -> Provider:
    return AzureAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        **kwargs
    )

@register_provider
def claude(
    model: str = 'claude-3-7-sonnet-20250219',
    client: AsyncAnthropic = None,
    api_key: str = None,
    **kwargs
) -> Provider:
    return Claude(
        client=client or AsyncAnthropic(
            api_key=api_key or os.getenv('ANTHROPIC_API_KEY'),
        ),
        model=model,
        max_tokens=32768,
        **kwargs
    )

openai: partial[Provider] = partial(
    openai_compatible,
    model='gpt-4o-mini',
    api_key=os.getenv('OPENAI_API_KEY')
)

openrouter: partial[Provider] = partial(
    openai_compatible,
    base_url='https://api.openrouter.ai/v1',
    model='openai/gpt-3.5-turbo',
    api_key=os.getenv('OPENROUTER_API_KEY'),
    max_tokens=8192
)

deepseek: partial[Provider] = partial(
    openai_compatible,
    base_url='https://api.deepseek.com/v1',
    model='deepseek-chat',
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    max_tokens=8192
)

github: partial[Provider] = partial(azureai, api_key=os.getenv('GITHUB_TOKEN'))
