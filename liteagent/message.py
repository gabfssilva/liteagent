from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass, field
from typing import Literal

import aiofiles

from liteagent.codec import JsonValue, to_json, JsonLike, JsonObject, JsonNull


@dataclass
class Image:
    type: Literal["url", 'path']

    async def __json__(self) -> JsonValue: pass


@dataclass
class ImageURL(Image):
    type: Literal["url"] = field(init=False, default="url")
    url: str

    async def __json__(self) -> JsonValue:
        return {"type": self.type, "url": self.url}


@dataclass
class ImagePath(Image):
    type: Literal["path"] = field(init=False, default="path")
    path: str

    async def __json__(self) -> JsonValue:
        return {"type": self.type, "path": self.path}

    def image_type(self) -> str:
        return self.path.split('.')[-1]

    async def as_base64(self) -> str:
        async with aiofiles.open(self.path, "rb") as image_file:
            content = await image_file.read()
            return base64.b64encode(content).decode("utf-8")


@dataclass(kw_only=True, eq=True, frozen=True)
class Message:
    id: str = field(init=False, default_factory=lambda: str(uuid.uuid4()))
    role: Literal['system', 'assistant', 'user', 'tool']
    content: JsonLike
    loop_id: str | None = None

    def __hash__(self) -> int:
        return hash(self.id)

    async def content_json(self) -> JsonValue:
        return await to_json(self.content)

    async def __json__(self) -> JsonValue:
        return {
            'role': self.role,
            'content': self.content,
            'loop_id': self.loop_id,
        }

    def complete(self) -> bool: return True


@dataclass(kw_only=True, eq=True, frozen=True)
class SystemMessage(Message):
    role: Literal['system'] = field(init=False, default="system")
    content: str


@dataclass(kw_only=True, eq=True, frozen=True)
class UserMessage(Message):
    role: Literal['user'] = field(init=False, default="user")
    content: str | Image


@dataclass(kw_only=True, eq=True, frozen=True)
class ToolMessage(Message):
    role: Literal['tool'] = field(init=False, default="tool")
    tool_use_id: str
    tool_name: str
    arguments: JsonObject | JsonNull
    content: JsonLike | ExecutionError

    @dataclass(kw_only=True)
    class ExecutionError:
        exception: str
        message: str
        should_retry: Literal['yes', 'no', 'maybe']

        async def __json__(self) -> JsonValue:
            return {
                'exception': self.exception,
                'message': self.message,
                'should_retry': self.should_retry,
            }


@dataclass(kw_only=True, eq=True, frozen=True)
class AssistantMessage(Message):
    role: Literal['assistant'] = field(init=False, default="assistant")
    content: TextComplete | JsonLike | ToolUse | TextChunk | ToolUseChunk

    @dataclass(kw_only=True, eq=True, frozen=True)
    class TextComplete:
        stream_id: str
        accumulated: str

        async def __json__(self) -> JsonValue:
            return self.accumulated

    @dataclass(kw_only=True, eq=True, frozen=True)
    class TextChunk:
        stream_id: str
        value: str
        accumulated: str = field(default="")

    @dataclass(kw_only=True, eq=True, frozen=True)
    class ToolUseChunk:
        tool_use_id: str
        name: str
        accumulated_arguments: JsonObject | str | JsonNull

    @dataclass(kw_only=True, eq=True, frozen=True)
    class ToolUse:
        tool_use_id: str
        name: str
        arguments: JsonObject | JsonNull

        async def __json__(self) -> JsonValue:
            return {
                "tool_use_id": self.tool_use_id,
                "name": self.name,
                "arguments": self.arguments
            }

    def complete(self) -> bool:
        match self.content:
            case AssistantMessage.TextChunk() | AssistantMessage.ToolUseChunk():
                return False
            case _:
                return True
