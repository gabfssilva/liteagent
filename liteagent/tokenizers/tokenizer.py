from abc import ABC, abstractmethod

import numpy as np
import tiktoken
from fastembed import TextEmbedding
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer


class Tokenizer(ABC):
    @abstractmethod
    async def encode(self, text: str) -> np.ndarray:
        pass

    @abstractmethod
    async def decode(self, tokens: np.ndarray) -> str:
        pass
