import json
from collections.abc import Iterable, AsyncIterable
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

JsonNull = None
JsonPrimitive = str | int | float | bool | JsonNull
JsonObject = dict[str, 'JsonValue']
JsonArray = list['JsonValue']

JsonValue = JsonPrimitive | JsonObject | JsonArray


@runtime_checkable
class JsonConvertable(Protocol):
    async def __json__(self) -> JsonValue: pass


JsonLike = JsonConvertable | JsonValue | BaseModel | Iterable['JsonValue'] | AsyncIterable['JsonValue']


async def to_json(content: JsonLike) -> JsonValue:
    match content:
        case JsonConvertable():
            parsed = await content.__json__()
            
            if isinstance(parsed, dict):
                return {k: await to_json(v) for k, v in parsed.items()}
            elif isinstance(parsed, list):
                return [await to_json(item) for item in parsed]

            return parsed
        case BaseModel() as model:
            return model.model_dump()
        case dict() as dict_value:
            return {k: await to_json(v) for k, v in dict_value.items()}
        case str() | int() | float() | bool() | None as json_value:
            return json_value
        case Iterable() as items:
            return [await to_json(item) for item in items]
        case AsyncIterable() as items:
            return [await to_json(item) async for item in items]
        case _:
            raise TypeError(f"Unsupported type for serialization: {type(content)}")


async def to_json_str(content: JsonLike, **kwargs) -> str:
    return json.dumps(await to_json(content), **kwargs)
