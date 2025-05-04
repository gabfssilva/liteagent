from typing import AsyncIterable, List

from . import Image
from .agent import Agent
from .message import Message, UserMessage


class Session:
    agent: Agent
    conversation: List[Message]

    def __init__(self, agent: Agent):
        self.agent = agent
        self.conversation = []

    def _wrap_user_input(
        self,
        *content: str | Image | Message,
        **kwargs,
    ) -> List[Message]:
        if kwargs and self.agent.user_prompt_template:
            bound = self.agent.signature.bind(**kwargs)
            bound.apply_defaults()

            return [
                UserMessage(content=self.agent.user_prompt_template.format(**bound.arguments))
            ]

        if kwargs:
            content = list(kwargs.values())

        if not content:
            raise ValueError("No content provided.")

        def to_message(c: str | Image | Message) -> Message:
            return c if isinstance(c, Message) else UserMessage(content=c)

        return [to_message(c) for c in content]

    async def summarize(self, prompt: str = "Summarize in detail all the conversation so far."):
        user_message = UserMessage(content=prompt)

        async for message in self(user_message):
            yield message

        summarization = list(filter(lambda m: m.role == 'assistant', self.conversation))[-1]
        self.reset()
        self.conversation.append(summarization)

    def __call__(
        self,
        *content: str | Image | Message,
        loop_id: str = None,
        **kwargs,
    ) -> AsyncIterable[Message]:
        async def stream_and_track():
            user_input = self._wrap_user_input(*content, **kwargs)

            full_conversation = self.conversation + user_input

            async for message in await self.agent(*full_conversation, loop_id=loop_id, stream=True):
                if message.role == "system":
                    continue

                if message in self.conversation:
                    continue

                yield message

                if message.complete():
                    self.conversation.append(message)

        return stream_and_track()

    def reset(self):
        self.conversation = []


def session(agent: Agent) -> Session:
    return Session(agent)
