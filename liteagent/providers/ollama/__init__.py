try:
    from .provider import Ollama, ollama

    __all__ = ["Ollama", "ollama"]
except ImportError:
    __all__ = []
