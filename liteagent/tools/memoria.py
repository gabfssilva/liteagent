import asyncio
import json
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

from liteagent import tool, Tools


class MemoryEntry(BaseModel):
    content: str
    type: Literal["semantic", "episodic", "procedural"] = "semantic"


class Storage(ABC):
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        pass

    @abstractmethod
    async def retrieve(self) -> dict[str, MemoryEntry]:
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        pass

    @abstractmethod
    async def update(self, memory_id: str, new_content: str) -> bool:
        pass


class FileStorage(Storage):
    def __init__(self, file_path: str, similarity_threshold: float = 0.85):
        from fastembed import TextEmbedding

        self.file_path = file_path
        self.similarity_threshold = similarity_threshold
        self.embedder = TextEmbedding()
        self._lock = asyncio.Lock()

    async def store(self, entry: MemoryEntry) -> str:
        import numpy as np

        memories = await self.retrieve()
        new_embedding = np.array(list(self.embedder.embed([entry.content]))[0])

        for memory_id, existing_entry in memories.items():
            existing_embedding = np.array(list(self.embedder.embed([existing_entry.content]))[0])
            similarity = np.dot(new_embedding, existing_embedding) / (
                np.linalg.norm(new_embedding) * np.linalg.norm(existing_embedding)
            )
            if similarity >= self.similarity_threshold:
                return memory_id

        new_id = str(len(memories))
        async with self._lock:
            memories[new_id] = entry
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({k: v.model_dump() for k, v in memories.items()}, f, indent=4, default=str)

        return new_id

    async def retrieve(self) -> dict[str, MemoryEntry]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                return {k: MemoryEntry(**v) for k, v in raw.items()}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def update(self, memory_id: str, new_content: str) -> bool:
        memories = await self.retrieve()

        if memory_id not in memories:
            return False

        async with self._lock:
            entry = memories[memory_id]
            entry.content = new_content
            memories[memory_id] = entry
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({k: v.model_dump() for k, v in memories.items()}, f, indent=2, default=str)

        return True

    async def delete(self, memory_id: str) -> bool:
        memories = await self.retrieve()

        if memory_id not in memories:
            return False

        async with self._lock:
            memories.pop(memory_id)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({k: v.model_dump() for k, v in memories.items()}, f, indent=4, default=str)

        return True


class Memoria(Tools):
    def __init__(self, storage: Storage):
        self.storage = storage

    @tool(emoji='💭')
    async def store(self, memories: list[MemoryEntry] = Field(...,
                                                              description='The memories the user requested you to keep.')) -> \
        list[str]:
        """
        Stores a list of structured memories and returns their assigned IDs.
        Every time the user shares something meaningful, you can use this tool to store it in your long-term memory.
        """
        ids = []
        for memory in memories:
            ids.append(await self.storage.store(memory))
        return ids

    @tool(eager=True, emoji='🧠')
    async def retrieve(self) -> dict[str, MemoryEntry]:
        """
        retrieves all stored memories as structured entries.
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
