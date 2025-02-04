import asyncio

from liteagent import Agent, tools, providers, agent
from liteagent.tools import OpenAlex


@agent(
    description="An agent specialized in interacting with OpenAlex APIs",
    provider=providers.openai(model="o3-mini"),
    tools=[OpenAlex(), tools.read_pdf_from_url]
)
async def openalex_agent(subject: str) -> str:
    """
    I want you to search for 3 pagers on {subject}.
    Based on their abstract, choose one of them, the one you find the most amusing.
    After that, I want you to:

    - Download their PDF (for arxiv urls, you must change the /abs/ to /pdf/ before downloading the PDF)
    - Summarize it for me
    - Elaborate some key points of your own.

    Your response must be in markdown format.
    """


async def main():
    await openalex_agent(subject='large language models')


if __name__ == '__main__':
    asyncio.run(main())
