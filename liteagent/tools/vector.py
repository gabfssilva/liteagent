from typing import Callable, Awaitable, List, AsyncIterator

from pydantic import Field

from liteagent import Tools, tool, ToolDef
from liteagent.vector import VectorDatabase, Document, Chunks, ChunkingStrategy, word_chunking


class VectorStore(Tools):
    store: VectorDatabase
    chunking_strategy: ChunkingStrategy

    def __init__(self, store: VectorDatabase, chunking_strategy: ChunkingStrategy):
        super().__init__()
        self.store = store
        self.chunking_strategy = chunking_strategy

    @tool(emoji='💾')
    async def store(self, id: str, content: str) -> str:
        """Stores a document in the vector store using chunking."""

        async def inner(): yield Document(id=id, content=content)

        await self.store_documents(inner())
        return "saved"

    async def store_documents(self, documents: AsyncIterator[Document]):
        async def generate_chunks():
            async for document in documents:
                chunks = await self.chunking_strategy.chunk(document.content)

                for part, chunk in enumerate(chunks):
                    yield Document(
                        id=document.id if part == 0 else f'{document.id}-{part}',
                        content=chunk,
                        metadata={
                            **document.metadata,
                            "part": part,
                            "total": len(chunks),
                            "original_id": document.id,
                        }
                    )

        await self.store.store(generate_chunks())

    @tool(emoji='🔎')
    async def search(
        self,
        query: str = Field(..., description="A concise search query based on the user's intent."),
        k: int | None = Field(
            description="The number of nearest neighbors to retrieve. Must be between 5 and 10. Defaults to 5."
        )
    ) -> Chunks:
        """This tool searches for semantically relevant information using a vector store.

        **Guidelines:**
        - Construct `query` using **concise yet meaningful phrases** rather than overly verbose questions.
        - If results are unsatisfactory:
            - **Retry with a refined `query`**, adjusting length and specificity.
            - **Modify `k` (number of results retrieved)** if too few or too many results appear.

        **Examples:**
        1. **User input:** "What was the name of Amanda's best friend?"
           - ✅ **Good queries:**
             - `"Amanda best friend"`
             - `"Amanda's closest friend"`
             - `"Amanda friend"`
           - ❌ **Bad queries:**
                - `"Who was Amanda's best friend?"`  (Too verbose, likely won't work)
                - `"The name of Amanda's best friend"` (Even worse)

        2. **User input:** "What are the symptoms of diabetes?"
           - ✅ **Good queries:**
             - `"Diabetes symptoms"`
             - `"Diabetes signs"`
           - ❌ **Bad queries:**
                - `"The symptoms people with diabetes have"`"""

        result = []

        async for chunk in self.store.search(query=query, k=k or 5):
            result.append(chunk)

        result = list(sorted(result, key=lambda chunk: chunk.distance, reverse=False))

        return Chunks(chunks=result)


async def vector_store(
    store: VectorDatabase | Callable[[...], Awaitable[VectorDatabase]],
    initial: List[Document] = None,
    chunking_strategy: ChunkingStrategy = word_chunking()
) -> ToolDef:
    vector_database: VectorDatabase

    match store:
        case VectorDatabase():
            vector_database = store
        case _:
            vector_database = await store()

    async def docs():
        for doc in initial:
            yield doc

    store = VectorStore(vector_database, chunking_strategy)

    if initial:
        await store.store_documents(docs())

    return store
