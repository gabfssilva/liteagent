from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING
import time

from overrides import overrides

from liteagent import UserMessage

if TYPE_CHECKING:
    from liteagent.agent import Agent
    from liteagent.tool import Tool

from liteagent.message import Message, AssistantMessage, SystemMessage, ToolMessage

@dataclass(eq=False, kw_only=True)
class Event:
    """Base class for all events"""
    agent: 'Agent'
    timestamp: float = field(default_factory=time.time)
    loop_id: str | None = None

    @property
    def event_type(self) -> str:
        return type(self).__name__

    @overrides
    def __hash__(self) -> int:
        return hash((self.event_type, self.id))

    @overrides
    def __eq__(self, other: Event) -> bool:
        return self.event_type == other.event_type and self.id == other.id

    @property
    def id(self) -> str:
        raise NotImplementedError()


@dataclass(eq=False, kw_only=True)
class AgentCallEvent(Event):
    messages: List[Message]

    @property
    def id(self) -> str:
        return ','.join(m.id for m in self.messages)


@dataclass(eq=False, kw_only=True)
class MessageEvent(Event):
    message: Message

    @property
    def id(self) -> str:
        return self.message.id


@dataclass(eq=False, kw_only=True)
class SystemMessageEvent(MessageEvent):
    message: SystemMessage

@dataclass(eq=False, kw_only=True)
class UserMessageEvent(MessageEvent):
    message: UserMessage

@dataclass(eq=False, kw_only=True)
class AssistantMessageEvent(MessageEvent):
    message: AssistantMessage

    def is_tool_use(self) -> bool:
        return isinstance(self.message.content, AssistantMessage.ToolUseStream)

    def is_text(self) -> bool:
        return isinstance(self.message.content, AssistantMessage.TextStream)

@dataclass(eq=False, kw_only=True)
class ToolMessageEvent(MessageEvent):
    message: ToolMessage
    tool: 'Tool'
    tool_use_id: str
