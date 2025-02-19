import asyncio
from liteagent.reasoning import Reasoning, reasoner

from liteagent.providers import openai

@reasoner(provider=openai(model='gpt-4o-mini'))
async def reasoner_agent() -> str: ...

reasoning = asyncio.run(reasoner_agent(
    prompt="Alice has four sisters and a brother, Bob. How many sisters does Bob have?"
))

print(reasoning)
