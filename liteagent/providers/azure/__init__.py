try:
    from .provider import AzureAI, azureai, github

    __all__ = ["AzureAI", "azureai", "github"]
except ImportError:
    __all__ = []
