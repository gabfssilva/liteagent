from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, TYPE_CHECKING
import time

from overrides import overrides

from liteagent import UserMessage

if TYPE_CHECKING:
    from liteagent.agent import Agent
    from liteagent.tool import Tool

from liteagent.message import Message, AssistantMessage, SystemMessage
from liteagent.codec import JsonLike, JsonObject, JsonNull


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
class AssistantMessagePartialEvent(MessageEvent):
    message: AssistantMessage


@dataclass(eq=False, kw_only=True)
class AssistantMessageCompleteEvent(MessageEvent):
    message: AssistantMessage


@dataclass(eq=False, kw_only=True)
class ToolEvent(MessageEvent):
    tool: 'Tool'
    tool_id: str


@dataclass(eq=False, kw_only=True)
class ToolRequestPartialEvent(ToolEvent):
    chunk: AssistantMessage.ToolUseChunk


@dataclass(eq=False, kw_only=True)
class ToolRequestCompleteEvent(ToolEvent):
    name: str
    arguments: JsonObject | JsonNull


@dataclass(eq=False, kw_only=True)
class ToolExecutionEvent(ToolEvent):
    arguments: Dict[str, Any]


@dataclass(eq=False, kw_only=True)
class ToolExecutionStartEvent(ToolExecutionEvent):
    pass


@dataclass(eq=False, kw_only=True)
class ToolExecutionCompleteEvent(ToolExecutionEvent):
    result: JsonLike


@dataclass(eq=False, kw_only=True)
class ToolExecutionErrorEvent(ToolExecutionEvent):
    error: Exception


@dataclass(eq=False, kw_only=True)
class TeamEvent(ToolEvent):
    target_agent: 'Agent'


@dataclass(eq=False, kw_only=True)
class TeamDispatchPartialEvent(TeamEvent):
    accumulated_arguments: JsonObject | str | JsonNull


@dataclass(eq=False, kw_only=True)
class TeamDispatchedEvent(TeamEvent):
    arguments: JsonObject


@dataclass(eq=False, kw_only=True)
class TeamDispatchFinishedEvent(TeamEvent):
    arguments: JsonObject
    messages: List[Message]


@dataclass(eq=False, kw_only=True)
class SessionResetEvent(Event):
    previous_conversation_size: int

    @property
    def id(self) -> str:
        return f"session_reset_{self.timestamp}"
