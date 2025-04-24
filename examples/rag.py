import asyncio

from liteagent import agent
from liteagent.providers import openai, anthropic
from liteagent.tools import vector_store
from liteagent.vector import in_memory, token_chunking
from liteagent.vector.loaders import from_url


async def main():
    documents = await asyncio.gather(
        from_url(
            url="https://www.gutenberg.org/cache/epub/1513/pg1513-images.html",
            infer_metadata=False,
            metadata={
                "title": "THE TRAGEDY OF ROMEO AND JULIET",
                "author": "William Shakespeare"
            },
        ),
        from_url(
            url='https://www.gutenberg.org/cache/epub/84/pg84-images.html',
            infer_metadata=False,
            metadata={
                "title": "Frankenstein; or, the Modern Prometheus",
                "author": "Mary Wollstonecraft"
            },
        ),
        from_url(
            url='https://www.gutenberg.org/cache/epub/11/pg11-images.html',
            infer_metadata=False,
            metadata={
                "title": "Alice’s Adventures in Wonderland",
                "author": "Lewis Carroll"
            },
        )
    )

    vector_search = await vector_store(
        store=in_memory(),
        initial=list(documents),
        chunking_strategy=token_chunking(),
    )

    @agent(
        provider=anthropic(),
        description="""
            You are a RAG agent. 
            **ALWAYS** use your vector store to look up the answer.
            **ALWAYS** include reference.
        """,
        tools=[vector_search]
    )
    async def rag_agent() -> str:  pass

    await rag_agent(
        "What does Juliet says right after: 'My ears have yet not drunk...'? What was **EXACTLY** Romeo's answer then?"
    )
    await rag_agent("Which book is the Mock Turtle from?")
    await rag_agent("What's Victor Frankenstein father's name?")
    await rag_agent("In Frankenstein, which people got the scarlet fever?")


if __name__ == '__main__':
    asyncio.run(main())
