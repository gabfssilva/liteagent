import json
from collections.abc import AsyncIterable
from dataclasses import dataclass, field
from typing import Literal, Iterator

from pydantic import BaseModel, JsonValue

from liteagent import Tool
from liteagent.codec import to_json
from liteagent.internal.memoized import MemoizedAsyncIterable


@dataclass
class ExecutionError:
    exception: str
    error: str
    should_tell_user: bool
    should_retry: Literal["yes", "no", "maybe"]


@dataclass
class ToolRequest:
    id: str
    name: str
    arguments: dict | list | str
    origin: Literal["local", "model"] = "model"
    tool: Tool | None = field(default=None)


@dataclass
class ImageURL:
    url: str


@dataclass
class ImageBase64:
    base64: str


Image = ImageURL | ImageBase64
Text = str

Content = Text | Image | dict | JsonValue | ToolRequest | BaseModel

PartialContent = MemoizedAsyncIterable[Content] | AsyncIterable[Content] | Iterator[Content]
CompleteContent = Content | list[Content]
MessageContent = CompleteContent | PartialContent

Role = Literal["user", "assistant", "system", "tool"]


@dataclass
class Message:
    role: Role
    content: MessageContent
    agent: str | None = field(init=False, default=None)

    def __post_init__(self):
        if isinstance(self.content, MemoizedAsyncIterable):
            return

        if isinstance(self.content, AsyncIterable):
            self.content = MemoizedAsyncIterable.from_async_iterable(self.content)

    async def acontent(self) -> MessageContent:
        if isinstance(self.content, MemoizedAsyncIterable):
            return await self.content.collect()

        return self.content

    async def __json__(self) -> JsonValue:
        return {
            "role": self.role,
            "content": await self.content_as_string(),
        }

    async def content_as_json(self) -> JsonValue:
        return await to_json(await self.acontent())

    async def content_as_string(self) -> str:
        return json.dumps(await self.content_as_json())


@dataclass
class UserMessage(Message):
    role: Literal['user'] = field(init=False, default="user")


@dataclass
class AssistantMessage(Message):
    role: Literal['assistant'] = field(init=False, default="assistant")
    content: MemoizedAsyncIterable[str] | ToolRequest | BaseModel

    async def acontent(self) -> MessageContent:
        if isinstance(self.content, MemoizedAsyncIterable):
            return ''.join(await self.content.collect())

        return self.content


@dataclass
class SystemMessage(Message):
    role: Literal['system'] = field(init=False, default="system")
    content: str


@dataclass
class ToolMessage(Message):
    id: str
    name: str
    content: MessageContent | ExecutionError
    role: Literal['tool'] = field(init=False, default="tool")
    tool: Tool
    elapsed_time: float

    async def acontent(self) -> MessageContent:
        match await super().acontent():
            case list() as items if any(filter(lambda item: isinstance(item, Message), items)):
                return items[-1]
            case content:
                return content
