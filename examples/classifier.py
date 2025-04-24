import asyncio
from typing import Literal, AsyncIterable, Iterable, List

from pydantic import BaseModel
from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table, Column

from liteagent import agent
from liteagent.providers import google

Sentiment = Literal["positive", "negative", "neutral"]

Flag = Literal[
    "app", "slow", "investment", "experience", "performance", "usability",
    "design", "support", "security", "stability", "ambiguous"
]


class ReviewResult(BaseModel):
    review: str
    sentiment: Sentiment
    flags: List[Flag]

async def review_classifier(reviews: Iterable[str]) -> AsyncIterable[ReviewResult]:
    @agent(provider=google(), intercept=None)
    async def sentiment_classifier(comment: str) -> Sentiment:
        """Evaluate the comment and categorize it: {comment}"""

    @agent(provider=google(), intercept=None)
    async def flag_classifier(comment: str) -> List[Flag]:
        """Evaluate the comment and flag it: {comment}"""

    for sentence in reviews:
        sentiment, flags = await asyncio.gather(
            sentiment_classifier(sentence),
            flag_classifier(sentence)
        )

        yield ReviewResult(review=sentence, sentiment=sentiment, flags=flags)


async def main():
    sample_comments = [
        "Interface is simple and elegant, love the minimal design.",
        "Customer support really knows their stuff, solved my issue fast.",
        "App crashes everytime i open it, total waste of time.",
        "Interface is confuseing and not user frendly.",
        "Loading times is ridiculously slow, frustation builds up fast.",
        "Search function works perfect, finds all i need.",
        "App logs me out unexpectedly, very frustrating experince.",
        "Design is modern and sleek, really appealing look.",
        "Customer support was helpful and responded quickly.",
        "App drains my battery too fast, extremely inefficent.",
        "Account login issues persists every time i try, so annoying.",
        "App freezes on me without reason, extremely annoying experince.",
        "Navigation is a nightmare, i get lost in the menus.",
        "Battery usage is efficient, i can use the app all day.",
    ]

    table = Table(
        Column("Review", vertical='middle'),
        Column("Sentiment", vertical='middle'),
        Column("Flags", vertical='middle'),
        title="Sentiment Classifier",
        box=box.ROUNDED,
        expand=True,
        row_styles=['dim'],
        show_lines=True
    )

    with Live(table, console=Console(), refresh_per_second=4):
        async for result in review_classifier(sample_comments):
            table.add_row(result.review, result.sentiment, "\n".join(result.flags))

if __name__ == '__main__':
    asyncio.run(main())
