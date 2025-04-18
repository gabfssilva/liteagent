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
    provider=openai(model='gpt-4o-mini')
)
async def confluence_agent(prompt: str = Field(..., description="A extremally detailed prompt based on the user's intent")) -> str:
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
    provider=openai(model='gpt-4o-mini')
)
async def jira_agent(prompt: str = Field(..., description="A extremally detailed prompt based on the user's intent")) -> str:
    """{prompt}"""

@chat.terminal(initial_message="Atlassian Agent")
@agent(
    provider=openai(model="gpt-4.1"),
    team=[jira_agent, confluence_agent]
)
async def atlassian_agent(): pass

if __name__ == "__main__":
    asyncio.run(atlassian_agent())
