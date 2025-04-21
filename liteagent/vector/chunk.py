from abc import ABC, abstractmethod
from typing import List

from liteagent.tokenizers import Tokenizer, transformers_tokenizer


class ChunkingStrategy(ABC):
    @abstractmethod
    async def chunk(self, text: str) -> List[str]:
        """Splits text into chunks based on the defined strategy."""
        pass


class WordChunking(ChunkingStrategy):
    def __init__(self, chunk_size: int = 3000, overlap: int = 500):
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def chunk(self, text: str) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        return chunks


class TokenChunking(ChunkingStrategy):
    def __init__(self, tokenizer: Tokenizer, max_tokens: int = 3000, overlap: int = 500):
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.overlap = overlap

    async def chunk(self, text: str) -> List[str]:
        import numpy as np

        tokens = await self.tokenizer.encode(text)
        tokens = tokens.flatten().tolist()

        chunks = []
        for i in range(0, len(tokens), self.max_tokens - self.overlap):
            chunk_tokens = tokens[i:i + self.max_tokens]
            chunk_text = await self.tokenizer.decode(np.array(chunk_tokens))
            chunks.append(chunk_text)

        return chunks


def token_chunking(
    tokenizer: Tokenizer = None,
    max_tokens: int = 5000,
    overlap: int = 500
) -> ChunkingStrategy: return TokenChunking(tokenizer or transformers_tokenizer(), max_tokens, overlap)


def word_chunking(
    chunk_size: int = 3000,
    overlap: int = 500
) -> ChunkingStrategy: return WordChunking(chunk_size, overlap)
