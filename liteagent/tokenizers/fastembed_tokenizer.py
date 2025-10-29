from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
else:
    import numpy as np

from fastembed import TextEmbedding
from liteagent.tokenizers import Tokenizer


class FastEmbedTokenizer(Tokenizer):
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = TextEmbedding(model_name)

    async def encode(self, text: str) -> 'np.ndarray':
        embeddings = list(self.model.embed([text]))
        return np.array(embeddings).squeeze(0)

    async def decode(self, tokens: 'np.ndarray') -> str:
        raise NotImplementedError("FastEmbed does not support decoding.")


def fastembed_tokenizer(model: str = "sentence-transformers/all-MiniLM-L6-v2") -> Tokenizer:
    return FastEmbedTokenizer(model)
