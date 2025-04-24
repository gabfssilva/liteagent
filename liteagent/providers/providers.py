import os
from functools import partial

from liteagent import Provider
from liteagent.internal.cleanup import register_provider


@register_provider
def google(
    model: str = "gemini-2.0-flash",
    **kwargs
) -> Provider:
    try:
        from google import genai
        from liteagent.providers.google.provider import Google

        return Google(genai.Client(
            api_key=os.getenv('GEMINI_API_KEY'),
        ), model, **kwargs)
    except ImportError:
        raise ImportError(
            "The google-genai package is required to use Google provider. "
            "Please install it with 'pip install \"liteagents[google]\"'"
        )


@register_provider
def ollama(
    model: str = 'llama3.2',
    automatic_download: bool = True,
    **kwargs
) -> Provider:
    try:
        from liteagent.providers.ollama.provider import Ollama
        return Ollama(model=model, automatic_download=automatic_download, **kwargs)
    except ImportError:
        raise ImportError(
            "The ollama package is required to use Ollama provider. "
            "Please install it with 'pip install \"liteagents[ollama]\"'"
        )


@register_provider
def openai_compatible(
    model: str,
    base_url: str = None,
    api_key: str = None,
    **kwargs
) -> Provider:
    try:
        from openai import AsyncOpenAI
        from liteagent.providers.openai.provider import openai_compatible

        return openai_compatible(
            client=AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                max_retries=5
            ),
            model=model,
            **kwargs
        )
    except ImportError:
        raise ImportError(
            "The openai package is required to use OpenAI compatible providers. "
            "Please install it with 'pip install \"liteagents[openai]\"'"
        )


@register_provider
def azureai(
    model: str = 'gpt-4o-mini',
    base_url: str = 'https://models.inference.ai.azure.com',
    api_key: str = None,
    **kwargs
) -> Provider:
    try:
        from liteagent.providers.azure.provider import AzureAI
        return AzureAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            **kwargs
        )
    except ImportError:
        raise ImportError(
            "The azure-ai-inference package is required to use Azure AI provider. "
            "Please install it with 'pip install \"liteagents[azure]\"'"
        )


def anthropic(
    model: str = 'claude-3-7-sonnet-20250219',
    api_key: str = None,
    **kwargs
) -> Provider:
    try:
        from anthropic import AsyncAnthropic
        from liteagent.providers.anthropic.provider import anthropic
        return anthropic(
            client=AsyncAnthropic(
                api_key=api_key or os.getenv('ANTHROPIC_API_KEY'),
            ),
            model=model,
            max_tokens=32768,
            **kwargs
        )
    except ImportError:
        raise ImportError(
            "The anthropic package is required to use the Anthropic provider. "
            "Please install it with 'pip install \"liteagents[anthropic]\"'"
        )


openai = partial(
    openai_compatible,
    model='gpt-4.1-mini',
    api_key=os.getenv('OPENAI_API_KEY')
)

openrouter = partial(
    openai_compatible,
    base_url='https://api.openrouter.ai/v1',
    model='openai/gpt-3.5-turbo',
    api_key=os.getenv('OPENROUTER_API_KEY'),
    max_tokens=8192
)

deepseek = partial(
    openai_compatible,
    base_url='https://api.deepseek.com/v1',
    model='deepseek-chat',
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    max_tokens=8192
)

github: partial[Provider] = partial(azureai, api_key=os.getenv('GITHUB_TOKEN'))
