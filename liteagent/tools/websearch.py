from pydantic import Field

from liteagent import tool
from liteagent.internal import depends_on


@tool(emoji='🔎')
@depends_on({"googlesearch": "googlesearch"})
def google(
    query: str = Field(..., description="The query for Google Web Search"),
    results: int = Field(10, description="The maxium result number to be returned. Defaults to 20."),
    language: str = Field(
        default=...,
        description=(
            "The language of the search. "
            "Either use the language the user explicitly tells you to, or the language they used in the prompt. "
        ),
        examples=["en", "fr", "pt", "es"]
    ),
    region: str = Field(
        default=...,
        description=(
            "The region of the search. The format is a lowercase country code."
            "Either use the region the user explicitly tells you to, or the region they used in the prompt. "
        ),
        examples=["us", "br", "jp"]
    )
) -> list[dict]:
    """ Use this tool for Google Searching. """
    from googlesearch import search

    return list(
        map(lambda r: dict(
            title=r.title,
            url=r.url,
            description=r.description
        ), search(
            query,
            num_results=results,
            lang=language,
            region=region,
            advanced=True
        ))
    )
