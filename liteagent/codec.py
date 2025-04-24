from collections.abc import Iterable, AsyncIterable
from dataclasses import asdict, Field
from typing import Protocol, overload, runtime_checkable, final, Any, TYPE_CHECKING, ClassVar

from pydantic import BaseModel, JsonValue


@final
@runtime_checkable
class DataclassLike(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]] = {}

    if not TYPE_CHECKING:
        def __init_subclass__(cls):
            raise TypeError(
                "Use the @dataclass decorator to create dataclasses, "
                "rather than subclassing dataclasses.DataclassLike"
            )


@runtime_checkable
class JsonLike(Protocol):
    async def __json__(self) -> JsonValue: pass


@overload
async def to_json(value: JsonLike) -> JsonValue: pass


@overload
async def to_json[T: str | int | float | bool | None](value: T) -> JsonValue: pass


@overload
async def to_json[T](value: Iterable[T]) -> JsonValue: pass


@overload
async def to_json[T](value: AsyncIterable[T]) -> JsonValue: pass


@overload
async def to_json(value: dict) -> JsonValue: pass


@overload
async def to_json(value: BaseModel) -> JsonValue: pass


@overload
async def to_json(value: DataclassLike) -> JsonValue: pass


async def to_json(content) -> JsonValue:
    match content:
        case JsonLike():
            return await content.__json__()
        case DataclassLike() as dt:
            return asdict(dt)
        case BaseModel() as model:
            return model.model_dump()
        case dict() as dict_value:
            return {k: await to_json(v) for k, v in dict_value.items()}
        case str() | int() | float() | bool() | None as json_value:
            return json_value
        case list() as items:
            return [await to_json(item) for item in items]
        case Iterable() as items:
            return [await to_json(item) for item in items]
        case AsyncIterable() as items:
            return [await to_json(item) async for item in items]
        case _:
            raise TypeError(f"Unsupported type for serialization: {type(content)}")
