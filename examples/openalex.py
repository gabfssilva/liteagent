import asyncio

from liteagent import tools, providers, agent
from liteagent.tools import openalex, read_pdf_from_url


@agent(
    description="An agent specialized in interacting with OpenAlex APIs",
    provider=providers.openai(model="o3-mini"),
    tools=[openalex, read_pdf_from_url]
)
async def openalex_agent(subject: str) -> str:
    """
    I want you to search for 5 papers on {subject}.
    Based on their abstract, choose one of them, the one you find the most amusing.
    After that, I want you to:

    - Download their PDF (for arxiv urls, you must change the /abs/ to /pdf/ before downloading the PDF)
    - Summarize it for me
    - Elaborate some key points of your own.

    Your response must be in markdown format, following the template:

    ```
    # Papers
    [All the papers you found, in a markdown table, containing the title, authors and url]

    # [Title]

    [Why you chose this paper]

    ## Summary
    [The summary you elaborated]

    ## Discoveries
    [The discoveries of the paper]

    ## Key Points
    [The extracted key points]
    ```

    Do not use backquotes in your response.
    """


async def main():
    await openalex_agent(subject='synthetic biology')

asyncio.run(main())
