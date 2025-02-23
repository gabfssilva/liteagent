from typing import Callable, Awaitable, List

from pydantic import Field

from liteagent import Tools, tool, ToolDef
from liteagent.vector import VectorDatabase, Document, Chunks


class VectorStore(Tools):
    store: VectorDatabase

    def __init__(self, store: VectorDatabase):
        super().__init__()
        self.store = store

    @tool(emoji='🔎')
    async def search(
        self,
        query: str = Field(..., description="Based on the user intent, the query for the search."),
        k: int | None = Field(description="The number of close neighbors to return. Minimum 5, maximum 10. Defaults to 5.")
    ) -> Chunks:
        """ use this tool to search in the vector store """

        result = []

        async for chunk in self.store.search(query=query, k=k or 5):
            result.append(chunk)

        return Chunks(chunks=result)

    @tool(emoji='💾')
    async def store(self, id: str, content: str) -> str:
        """ use this tool to store a document in the vector store """

        async def single():
            yield Document(id=id, content=content, metadata={})

        await self.store.store(single())

        return "saved"

async def vector(
    store: VectorDatabase | Callable[[...], Awaitable[VectorDatabase]],
    initial: List[Document] = None
) -> ToolDef:
    vector_store: VectorDatabase

    match store:
        case VectorDatabase():
            vector_store = store
        case _:
            vector_store = await store()

    async def docs():
        for doc in initial:
            yield doc

    if initial:
        await vector_store.store(docs())

    return VectorStore(vector_store)
