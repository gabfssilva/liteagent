import asyncio

from liteagent import Agent, tools, providers, agent
from liteagent.tools import OpenAlex


@agent(
    description="An agent specialized in interacting with OpenAlex APIs",
    provider=providers.openai(model="o3-mini"),
    tools=[OpenAlex(), tools.read_pdf_from_url]
)
async def openalex_agent() -> str: ...


async def main():
    await openalex_agent("""
        I want you to search for 3 pagers on large language models.
        Based on their abstract, choose one of them, the one you find the most amusing.
        After that, I want you to:

        - Download their PDF
        - Summarize it for me
        - Elaborate some key points of your own.

        (for arxiv urls, you must change the /abs/ to /pdf/ before downloading the PDF)
    """)


if __name__ == '__main__':
    asyncio.run(main())
