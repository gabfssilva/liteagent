from typing import AsyncIterator, List

from .agent import Agent
from .internal.as_coroutine import isolated_loop
from .logger import log
from .message import Message, UserMessage, MessageContent, AssistantMessage, ToolMessage, ToolRequest


class Session:
    agent: Agent
    conversation: List[Message]

    def __init__(self, agent: Agent):
        self.agent = agent
        self.conversation = []
        log.info("session_created", agent=agent.name)

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

    def ordered_conversation(self) -> List[Message]:
        reordered: List[Message] = []
        tool_response_map = {}

        for msg in self.conversation:
            if isinstance(msg, ToolMessage):
                tool_response_map[msg.id] = msg

        skip_ids = set()

        for msg in self.conversation:
            if isinstance(msg, AssistantMessage) and isinstance(msg.content, ToolRequest):
                reordered.append(msg)
                tool_msg = tool_response_map.get(msg.content.id)
                if tool_msg:
                    reordered.append(tool_msg)
                    skip_ids.add(tool_msg.id)
            elif isinstance(msg, ToolMessage) and msg.id in skip_ids:
                continue
            else:
                reordered.append(msg)

        return reordered

    def __call__(
        self,
        *content: MessageContent | Message,
        **kwargs,
    ) -> AsyncIterator[Message]:
        session_logger = log.bind(agent=self.agent.name, session_id=id(self))
        session_logger.info("session_called")

        @isolated_loop
        async def stream_and_track():
            session_logger.debug("wrapping_user_input")
            user_input = self._wrap_user_input(*content, **kwargs)
            session_logger.debug("user_input_wrapped", message_count=len(user_input))

            ordered_conv = self.ordered_conversation()
            session_logger.debug("conversation_ordered", message_count=len(ordered_conv))

            full_conversation = ordered_conv + user_input
            session_logger.debug("full_conversation_prepared", message_count=len(full_conversation))

            # Replace the print with structured logging
            session_logger.debug("sending_to_agent",
                                 conversation_size=len(full_conversation),
                                 user_messages=len([m for m in full_conversation if m.role == "user"]),
                                 assistant_messages=len([m for m in full_conversation if m.role == "assistant"]),
                                 tool_messages=len([m for m in full_conversation if m.role == "tool"]))

            session_logger.debug("streaming_from_agent_started")
            async for message in await self.agent(*full_conversation, stream=True):
                if message in self.conversation:
                    session_logger.debug("skipping_duplicate_message", role=message.role)
                    continue

                if message.role == "system":
                    session_logger.debug("skipping_system_message")
                    continue

                session_logger.debug("message_received",
                                     role=message.role,
                                     content_type=type(message.content).__name__)

                yield message
                self.conversation.append(message)
                session_logger.debug("message_added_to_conversation",
                                     conversation_size=len(self.conversation))

            session_logger.debug("streaming_from_agent_completed")

        return stream_and_track()

    def reset(self):
        session_logger = log.bind(agent=self.agent.name, session_id=id(self))
        session_logger.info("session_reset", previous_conversation_size=len(self.conversation))
        self.conversation = []


def session(agent: Agent) -> Session:
    return Session(agent)
