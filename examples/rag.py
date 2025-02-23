import asyncio

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools import vector
from liteagent.vector import InMemory
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

    vector_search = await vector(store=InMemory(), initial=list(documents))

    @agent(
        provider=openai(model="gpt-4o"),
        description="""
            You are a RAG agent. 
            **ALWAYS** use your vector store to look up the answer.
            **ALWAYS** include reference.
        """,
        tools=[vector_search]
    )
    async def rag_agent() -> str:  pass

    await rag_agent("Juliet says: 'My ears have yet not drunk...', what did she say next? What about Romeo's answer?")

    await rag_agent("Which book is the Mock Turtle from?")

    await rag_agent("What's Victor Frankenstein father's name?")


if __name__ == '__main__':
    asyncio.run(main())
