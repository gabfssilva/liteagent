import asyncio

from liteagent import agent, providers
from liteagent.tools import semantic_scholar


@agent(
    description="An agent specialized in academic paper research using Semantic Scholar",
    provider=providers.openai(model="gpt-4.1-mini"),
    tools=[semantic_scholar()]
)
async def academic_research_agent(query: str) -> str:
    """
    Research academic papers on {query}.
    
    Use the semantic scholar tools to:
    - Search for relevant papers about the topic
    - Find key authors in the field
    - Extract detailed information about specific papers or authors
    - If paper IDs or author IDs are mentioned, retrieve their specific details
    
    Format your response in markdown with:
    
    # Research Results
    
    ## Papers
    [Table of papers with title, authors, year, and URL]
    
    ## Authors
    [Key authors in this field with publication count and citation impact]
    
    ## Detailed Analysis
    [Analysis of the most relevant papers or authors from the query]
    """


# Example usage
async def main():
    await academic_research_agent(query="large language models and ethics")

if __name__ == "__main__":
    asyncio.run(main())
