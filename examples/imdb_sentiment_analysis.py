import asyncio
from typing import Literal, AsyncIterator, Iterator, Tuple

from datasets import load_dataset

from liteagent import agent
from liteagent.providers import openai

Sentiment = Literal['positive', 'negative']

Review = Tuple[str, Sentiment]
Result = Tuple[Sentiment, Sentiment]


async def workflow(
    data: Iterator[Review],
) -> AsyncIterator[Result]:
    @agent(provider=openai(), intercept=None)
    async def classifier(review: str) -> Sentiment:
        """Evaluate the following review: {review}"""

    for review, expected in data:
        predicted = await classifier(review=review)
        yield predicted, expected

async def main():
    imdb = load_dataset('scikit-learn/imdb', split='all')

    reviews = imdb['review']
    labels = imdb['sentiment']

    data = zip(reviews, labels)

    async for predicted, expected in workflow(data):
        print(f"Predicted: {predicted} | Expected: {expected}")


if __name__ == "__main__":
    asyncio.run(main())
