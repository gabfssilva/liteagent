try:
    from .provider import OpenAICompatible, openai, openai_compatible, openrouter, deepseek

    __all__ = ["OpenAICompatible", "openai", "openai_compatible", "openrouter", "deepseek"]
except ImportError:
    __all__ = []
