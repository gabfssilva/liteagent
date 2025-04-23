import asyncio
import os

from atlassian import Confluence, Jira
from pydantic.v1 import Field

from liteagent import agent, chat
from liteagent.providers import openai
from liteagent.tools import confluence, jira

@agent(
    tools=[
        confluence(client=Confluence(
            url=os.getenv("ATLASSIAN_CONFLUENCE_URL"),
            username=os.getenv("ATLASSIAN_USERNAME"),
            password=os.getenv("ATLASSIAN_API_TOKEN"),
            cloud=True
        ))
    ],
    provider=openai(model='gpt-4.1-mini'),
    description="""
        You are a specialized Confluence agent.

        Your task:
        - Receive a rewritten prompt that focuses **exclusively on documentation** and internal knowledge stored in Confluence.
        - Use the Confluence tool to search across pages, spaces, and labels.
        - Use the optional 'space' argument, if provided, to narrow your search.
        - Extract summaries, decisions, instructions, and references relevant to the topic.
        - Do NOT answer questions beyond Confluence’s scope.
        - Return clean, clear, factual summaries with page titles or links when available.
    """
)
async def confluence_agent(
    prompt: str = Field(..., description="Prompt rewritten to target documentation or knowledge sources"),
) -> str:
    """{prompt}"""


@agent(
    tools=[
        jira(client=Jira(
            url=os.getenv("ATLASSIAN_JIRA_URL"),
            username=os.getenv("ATLASSIAN_USERNAME"),
            password=os.getenv("ATLASSIAN_API_TOKEN"),
            cloud=True
        ))
    ],
    provider=openai(model='gpt-4.1-mini'),
    description="""
        You are a specialized Jira agent.

        Your task:
        - Receive a rewritten prompt that focuses **only on issue tracking and delivery**.
        - Use the Jira tool to search for issues, epics, sprints, and task statuses.
        - Use the optional 'project' argument, if provided, to narrow your search.
        - Retrieve issue summaries, assignments, deadlines, blockers, and overall progress.
        - Do NOT answer documentation-related questions.
        - Return structured, clear summaries with links or ticket keys when available.
    """
)
async def jira_agent(
    prompt: str = Field(..., description="Prompt rewritten to target Jira issues and execution status"),
) -> str:
    """{prompt}"""


@chat.terminal(logo="Atlassian")
@agent(
    provider=openai(model="gpt-4.1"),
    team=[jira_agent, confluence_agent],
    description="""
        You are an Atlassian Meta-Agent that orchestrates both documentation and issue tracking insights.

        Your behavior:
        - Ask the user to clarify missing context: team name, Jira project key, or Confluence space name.
        - Rewrite the user’s question into TWO separate prompts:
            1. One targeting documentation-related content for Confluence.
            2. One targeting issue tracking and task status for Jira.
        - Call **both agents concurrently** with their specialized prompts and the relevant context.
        - Wait for both responses and compare findings.
        - Merge answers into a single, structured summary — prioritize clarity, consistency, and insight.
        - If answers conflict, explain the discrepancies and provide a best-effort conclusion.
    """
)
async def atlassian_agent(): pass

if __name__ == "__main__":
    # confluence = Confluence(
    #     url=os.getenv("ATLASSIAN_CONFLUENCE_URL"),
    #     username=os.getenv("ATLASSIAN_USERNAME"),
    #     password=os.getenv("ATLASSIAN_API_TOKEN"),
    #     cloud=True
    # )
    #
    # # Get list of all spaces
    # spaces = confluence.get_all_spaces(start=0, limit=50, space_type="global", expand='description.plain')
    #
    # # Print space keys and names
    # for space in spaces['results']:
    #     print(f"{space['key']}: {space['name']}")

    asyncio.run(atlassian_agent())
