import os
from functools import partial

from openai import AsyncOpenAI

from liteagents.providers import OpenAICompatible, Provider


def openai_compatible(
    model: str,
    client: AsyncOpenAI = None,
    base_url: str = None,
    api_key: str = None,
    max_tokens: int = 16384,
    temperature: float = 0.7,
    top_p: float = 1,
    frequency_penalty: float = 0,
    presence_penalty: float = 0,
) -> Provider:
    return OpenAICompatible(
        client=client or AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        ),
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty
    )


openai: partial[Provider] = partial(
    openai_compatible,
    model='gpt-4o',
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
