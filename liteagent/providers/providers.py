import os
from functools import partial

from google import genai
from llama_cpp import Llama
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from liteagent.providers import OpenAICompatible, Provider, Ollama, LlamaCpp, Transformer
from liteagent.providers.gemini_provider import Gemini
from liteagent.providers.claude_provider import Claude


def gemini(
    client: genai.Client = genai.Client(),
    model: str = "gemini-2.0-flash"
) -> Provider: return Gemini(client, model)


def transformer(
    model: str = "meta-llama/Llama-3.2-3B",
    **kwargs
) -> Provider: return Transformer(model=model, **kwargs)


def llamacpp(
    llm: Llama = None
) -> Provider:
    return LlamaCpp(llm=llm or Llama.from_pretrained(
        repo_id="bartowski/Mistral-Small-24B-Instruct-2501-GGUF",
        filename="*IQ2_XS.gguf",
        verbose=False,
        n_ctx=131072,
        device="mps",
        # chat_format='chatml-function-calling'
    ))


def ollama(
    model: str = 'llama3.2',
    automatic_download: bool = True
) -> Provider:
    return Ollama(model=model, automatic_download=automatic_download)


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
