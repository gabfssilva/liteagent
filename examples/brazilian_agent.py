import asyncio
from asyncio import sleep

from liteagent import agent, bus
from liteagent.events import MessageEvent, AssistantMessageEvent
from liteagent.providers import deepseek
from liteagent.tools import brasil_api


@bus.on(AssistantMessageEvent)
async def on_message(event: AssistantMessageEvent):
    print(f"{event.event_type} ({event.id}): {event.message.content}")


@agent(
    tools=[brasil_api],
    provider=deepseek(),
)
async def brazilian_agent() -> str: pass


async def main():
    session = brazilian_agent.stateful()

    async for _ in session("what's the current CDI rate?"):
        pass

    async for _ in session("the current CDI times 0.1 is...?"):
        pass

    await sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
