import asyncio
import json
from abc import ABC, abstractmethod

import numpy as np
from fastembed import TextEmbedding
from pydantic import Field

from liteagent import tool, Tools


class Storage(ABC):
    @abstractmethod
    async def store(self, content: str) -> str:
        pass

    @abstractmethod
    async def retrieve(self) -> dict[str, str]:
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass

    @abstractmethod
    async def update(self, memory_id: str, new_content: str) -> bool:
        pass


class FileStorage(Storage):
    def __init__(self, file_path: str, similarity_threshold: float = 0.85):
        self.file_path = file_path
        self.similarity_threshold = similarity_threshold
        self.embedder = TextEmbedding()

    async def store(self, content: str) -> str:
        memories = await self.retrieve()

        new_embedding = np.array(list(self.embedder.embed([content]))[0])

        # Check similarity with existing memories
        for memory_id, existing_content in memories.items():
            existing_embedding = np.array(list(self.embedder.embed([existing_content]))[0])
            similarity = np.dot(new_embedding, existing_embedding) / (
                np.linalg.norm(new_embedding) * np.linalg.norm(existing_embedding))

            if similarity >= self.similarity_threshold:  # If sufficiently similar, return existing ID
                return memory_id

        new_id = str(len(memories))
        async with asyncio.Lock():
            memories[new_id] = content
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=4)

        return new_id

    async def retrieve(self) -> dict[str, str]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def update(self, memory_id: str, new_content: str) -> bool:
        memories = await self.retrieve()

        if memory_id not in memories:
            return False

        async with asyncio.Lock():
            memories[memory_id] = new_content

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=2)

        return True

    async def delete(self, memory_id: str) -> bool:
        memories = await self.retrieve()

        if memory_id not in memories:
            return False

        async with asyncio.Lock():
            memories.pop(memory_id)

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=4)

        return True


class Memoria(Tools):
    def __init__(self, storage: Storage):
        self.storage = storage

    @tool(emoji='💭')
    async def store(self, memories: list[str] = Field(...,
                                                      description='The memories the user requested you to keep, in a concise manner. It is possible to save multiple memories at once, so, always do it when you can.')) -> str:
        """
        stores the memories and responds the saved IDs.
        """

        ids = []

        for memory in memories:
            ids.append(await self.storage.store(memory))

        return f'Memories successfully stored with ids: {ids}'

    @tool(eager=True, emoji='🧠')
    async def retrieve(self) -> dict[str, str]:
        """
        retrieves all stored memories. check the available memories before asking for more information.
        """

        return await self.storage.retrieve()

    @tool(emoji='💭')
    async def update(self, memory_id: str, new_content: str) -> str:
        """
        updates a memory by ID and returns confirmation.
        """

        success = await self.storage.update(memory_id, new_content)
        return "Memory updated successfully." if success else "Memory not found."

    @tool(emoji='🤯')
    async def delete(self, memory_id: str) -> str:
        """
        deletes a memory by ID and returns confirmation.
        """

        success = await self.storage.delete(memory_id)
        return "Memory deleted successfully." if success else "Memory not found."


def memoria(storage: Storage = None) -> Tools:
    return Memoria(storage=storage or FileStorage('./brain.json'))
