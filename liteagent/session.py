from typing import AsyncIterator, List

from .agent import Agent
from .message import Message, UserMessage, MessageContent, AssistantMessage

class Session:
    agent: Agent
    conversation: List[Message]

    def __init__(self, agent: Agent):
        self.agent = agent
        self.conversation = list(agent.initial_messages)

    def _wrap_user_input(
        self,
        *content: MessageContent | Message,
        **kwargs,
    ) -> List[Message]:
        if kwargs:
            if not self.agent.signature or not self.agent.user_prompt_template:
                raise ValueError("Agent missing signature or prompt template.")

            bound = self.agent.signature.bind(**kwargs)
            bound.apply_defaults()

            return [
                UserMessage(content=self.agent.user_prompt_template.format(**bound.arguments))
            ]

        if not content:
            raise ValueError("No user content provided.")

        def to_message(c: MessageContent | Message) -> Message:
            return c if isinstance(c, Message) else UserMessage(content=c)

        return [to_message(c) for c in content]

    def __call__(
        self,
        *content: MessageContent | Message,
        **kwargs,
    ) -> AsyncIterator[Message]:
        async def stream_and_track():
            messages = self.conversation + self._wrap_user_input(*content, **kwargs)
            last_assistant_message = None

            async for message in await self.agent(*messages, stream=True):
                if message in self.conversation:
                    continue

                if message.role == "system":
                    continue

                yield message

                if message.role == "assistant" and isinstance(message.content, str):
                    last_assistant_message = last_assistant_message + message.content if last_assistant_message else message.content
                    continue

                if last_assistant_message and (message.role != "assistant" or not isinstance(message.content, str)):
                    self.conversation.append(AssistantMessage(content=last_assistant_message))
                    last_assistant_message = None

                self.conversation.append(message)

            if last_assistant_message:
                self.conversation.append(AssistantMessage(content=last_assistant_message))

        return stream_and_track()

    def reset(self):
        self.conversation = list(self.agent.initial_messages)

def session(agent: Agent) -> Session:
    return Session(agent)
