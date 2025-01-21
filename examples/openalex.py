from liteagents import Agent, tools, auditors, providers
from liteagents.agent_decorator import agent

import asyncio


@agent(
    description="An agent specialized in interacting with OpenAlex APIs",
    provider=providers.openai(),
    tools=tools.openalex.all + [tools.read_pdf_from_url]
)
def openalex_agent() -> Agent: ...


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
