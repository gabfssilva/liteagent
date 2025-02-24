import numpy as np
from transformers import AutoTokenizer

from liteagent.tokenizers import Tokenizer


class TransformersTokenizer(Tokenizer):
    def __init__(self, model_name="bert-base-uncased"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    async def encode(self, text: str) -> np.ndarray:
        tokens = self.tokenizer(text, return_tensors="np")
        return tokens["input_ids"]

    async def decode(self, tokens: np.ndarray) -> str:
        return self.tokenizer.decode(tokens.flatten().tolist(), skip_special_tokens=True)


def transformers_tokenizer(model: str = "bert-base-uncased") -> Tokenizer:
    return TransformersTokenizer(model)
