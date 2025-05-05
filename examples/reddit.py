import asyncio
import os

from liteagent import agent
from liteagent.providers import openai
from liteagent.tools.reddit import reddit


@agent(
    provider=openai(model="gpt-4.1-mini"),
    tools=[
        reddit(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_SECRET"]
        )
    ],
    description="You are a Reddit research assistant. You help find and summarize information from Reddit."
)
async def reddit_agent(topic: str) -> str:
    """
    Search Reddit for information about {topic} and provide a summary of the most relevant posts.
    Include links to the original posts and mention which subreddits have the most discussion on this topic.
    """


if __name__ == "__main__":
    asyncio.run(reddit_agent(topic="machine learning"))
