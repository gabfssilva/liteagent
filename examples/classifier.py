import asyncio
from typing import Literal, AsyncIterator, Iterable, List

from pydantic import BaseModel, Field, conlist

from liteagent import agent
from liteagent.providers import openai

Sentiment = Literal["positive", "negative", "neutral"]
Flag = Literal["applicative", "slow", "investment", "experience"]


class NPSResult(BaseModel):
    nps: str
    sentiment: Sentiment
    flags: List[Flag] = conlist(Flag, min_length=1, max_length=3)


async def nps_classifier(nps: Iterable[str]) -> AsyncIterator[NPSResult]:
    @agent(provider=openai(model='o3-mini'))
    async def classifier(comment: str) -> Sentiment:
        """ evaluate the comment and categorize it: {comment} """

    @agent(provider=openai(model='o3-mini'))
    async def flags(comment: str) -> List[Flag]:
        """ evaluate the comment and flag it (at most 3 flags): {comment} """

    for sentence in nps:
        yield NPSResult(
            nps=sentence,
            sentiment=await classifier(sentence),
            flags=await flags(sentence)
        )


async def main():
    async for result in nps_classifier([
        "This app is slow as fuck!",
        "I love this investment app.",
        "It is useful, but lots of things to improve."
    ]):
        print(result)


if __name__ == '__main__':
    asyncio.run(main())
