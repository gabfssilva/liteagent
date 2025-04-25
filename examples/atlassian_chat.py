import asyncio
import os

from atlassian import Confluence, Jira
from pydantic.v1 import Field

from liteagent import agent, chat
from liteagent.providers import openai
from liteagent.tools import confluence, jira


@chat.terminal(logo="Atlassian")
@agent(
    tools=[
        jira(client=Jira(
            url=os.getenv("ATLASSIAN_JIRA_URL"),
            username=os.getenv("ATLASSIAN_USERNAME"),
            password=os.getenv("ATLASSIAN_API_TOKEN"),
            cloud=True
        )),
        confluence(client=Confluence(
            url=os.getenv("ATLASSIAN_CONFLUENCE_URL"),
            username=os.getenv("ATLASSIAN_USERNAME"),
            password=os.getenv("ATLASSIAN_API_TOKEN"),
            cloud=True
        ))
    ],
    provider=openai(model="gpt-4.1"),
    description="""
        You are an Atlassian Meta-Agent that combines Confluence (documentation) and Jira (issue tracking) insights.

        Your behavior:
        - If needed, ask the user to clarify missing context: team name, Jira project key, or Confluence space name. Double check if you need more context first.
        - Use the appropriate tool for each sub-task, e.g.:
            - Use `confluence.search_pages(...)` to retrieve docs, decisions, or onboarding info.
            - Use `jira.search_issues(...)` or other methods to get ticket progress or status.
        - Return a summary:
            • Highlight relevant findings from all the tool calls.
            • Provide links or references when available.
            • Clarify if any information is missing, outdated, or contradictory.
        - Stay within the boundaries of Atlassian systems — do not guess or hallucinate.
    """
)
async def atlassian_agent() -> str: pass

if __name__ == "__main__":
    asyncio.run(atlassian_agent())
