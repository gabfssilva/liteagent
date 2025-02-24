import numpy as np
from sentence_transformers import SentenceTransformer

from liteagent.tokenizers import Tokenizer


class SentenceTransformerTokenizer(Tokenizer):
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    async def encode(self, text: str) -> np.ndarray:
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    async def decode(self, tokens: np.ndarray) -> str:
        raise NotImplementedError("SentenceTransformer does not support decoding.")


def sentence_transformer_tokenizer(model: str = "sentence-transformers/all-MiniLM-L6-v2") -> Tokenizer:
    return SentenceTransformerTokenizer(model)
