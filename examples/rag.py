import asyncio

from liteagent import agent
from liteagent.misc.document_metadata import get_metadata
from liteagent.providers import openai
from liteagent.tools import vector
from liteagent.vector import Document, Chroma

async def main():
    chroma = Chroma(
        initial=[
            Document.from_pdf(
                id="arxiv@2501.13946",
                url="https://arxiv.org/pdf/2501.13946",
                metadata=await get_metadata(openai(), "https://arxiv.org/pdf/2501.13946")
            )
        ]
    )

    @agent(
        provider=openai(),
        description="You are a RAG agent. Use your vector store to search for information about a given topic.",
        tools=[vector(store=chroma)]
    )
    async def rag_agent() -> str:
        """ tell me about the paper Deborah and Diego wrote """

    await rag_agent()

if __name__ == '__main__':
    asyncio.run(main())
