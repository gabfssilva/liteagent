import asyncio

from liteagent import agent
from liteagent.providers import github
from liteagent.tools import arxiv


@agent(
    description="An agent specialized in searching and explaining arXiv papers",
    provider=github(model="Llama-3.3-70B-Instruct"),
    tools=[arxiv]
)
async def arxiv_agent(topic: str) -> str:
    """
    I want you to search for recent papers on {topic} using the arXiv API.
    Find 3-5 interesting papers and provide their details.
    For the most interesting paper, get the full details and explain:
    
    1. What problem does this paper address?
    2. What is the proposed approach or solution?
    3. What are the key findings or results?
    4. Why is this significant in the field?
    
    Format your response as a well-structured markdown document with sections for:
    - Overview of search results
    - Detailed analysis of the most interesting paper
    - How this connects to the broader field
    """


if __name__ == "__main__":
    asyncio.run(arxiv_agent(topic="quantum machine learning"))
