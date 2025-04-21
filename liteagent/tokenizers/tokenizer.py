from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

from abc import ABC, abstractmethod


class Tokenizer(ABC):
    @abstractmethod
    async def encode(self, text: str) -> 'np.ndarray':
        pass

    @abstractmethod
    async def decode(self, tokens: 'np.ndarray') -> str:
        pass
