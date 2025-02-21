from liteagent import Tools, tool, ToolDef
from liteagent.vector.vector_store import VectorStore, Chunk, Document, Chunks


class VectorSearch(Tools):
    store: VectorStore

    def __init__(self, store: VectorStore):
        super().__init__()
        self.store = store

    @tool(emoji='🔎')
    async def search(self, query: str, count: int) -> Chunks:
        """ use this tool to search in the vector store """

        result = []

        async for chunk in self.store.search(query=query, count=count):
            result.append(chunk)

        return Chunks(chunks=result)

    @tool(emoji='💾')
    async def store(self, id: str, content: str) -> str:
        """ use this tool to store a document in the vector store """

        async def single():
            yield Document(id=id, content=content, metadata={})

        await self.store.store(single())

        return "saved"

def vector(store: VectorStore) -> ToolDef:
    return VectorSearch(store)
