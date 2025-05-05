import asyncio
from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import vector_store
from liteagent.vector import chroma_in_memory, token_chunking
from liteagent.vector.loaders import from_url


async def main():
    # Load documents from URLs
    documents = await asyncio.gather(
        from_url(
            url="https://en.wikipedia.org/wiki/Artificial_intelligence",
            infer_metadata=False,
            metadata={
                "title": "Artificial Intelligence",
                "source": "Wikipedia"
            }
        ),
        from_url(
            url="https://en.wikipedia.org/wiki/Machine_learning",
            infer_metadata=False,
            metadata={
                "title": "Machine Learning",
                "source": "Wikipedia"
            }
        ),
        from_url(
            url="https://en.wikipedia.org/wiki/Python_(programming_language)",
            infer_metadata=False,
            metadata={
                "title": "Python Programming Language",
                "source": "Wikipedia"
            }
        )
    )

    @agent(
        provider=openai(model="gpt-4.1-mini"),
        tools=[
            await vector_store(
                store=chroma_in_memory(),
                initial=list(documents),
                chunking_strategy=token_chunking(),
            )
        ],
        description="You are a helpful assistant that answers questions based on the provided documents."
    )
    async def rag_assistant(query: str) -> str:
        """
        Answer the user's question: {query}

        Use the vector search tool to find relevant information in the loaded documents.
        Provide a comprehensive answer based on the document content.
        If the information is not in the documents, politely say so.
        """

    await rag_assistant(query="What is the difference between AI and Machine Learning?")
    await rag_assistant(query="Tell me about Python programming language")


if __name__ == "__main__":
    asyncio.run(main())
