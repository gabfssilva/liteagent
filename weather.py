from pydantic import Field

from liteagents import tool, Agent, auditors
from liteagents.providers import OpenAICompatible

if __name__ == '__main__':
    markdown_agent = Agent(
        name="Weather Agent",
        provider=OpenAICompatible(),
        description="An agent for explaining markdown stuff.",
        intercept=auditors.console()
    )

    *_, _ = markdown_agent.sync("Show me 10 markdown features")
