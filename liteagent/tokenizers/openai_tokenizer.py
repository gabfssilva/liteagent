import numpy as np
import tiktoken

from liteagent.tokenizers import Tokenizer


class OpenAITokenizer(Tokenizer):
    def __init__(self, model_name="gpt-4o"):
        self.tokenizer = tiktoken.encoding_for_model(model_name)

    async def encode(self, text: str) -> np.ndarray:
        tokens = self.tokenizer.encode(text)
        return np.array(tokens)

    async def decode(self, tokens: np.ndarray) -> str:
        return self.tokenizer.decode(tokens.tolist())


def openai_tokenizer(model: str = "gpt-4o") -> Tokenizer:
    return OpenAITokenizer(model)
