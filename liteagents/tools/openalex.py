import json
from typing import Optional

from pyalex import Works, Authors, Sources, Institutions, Topics
from pydantic import Field

from liteagents import tool


@tool
def get_single_work(
    ref: str = Field(
        ...,
        description="Work's ID, DOI or ROR",
    )
) -> dict:
    """ A tool for fetching OpenAlex's works. """

    work = Works()[ref]

    return {
        "id": work['id'],
        "title": work['title'],
        "abstract": work['abstract'],
        "open_access": work['open_access'],
    }


@tool
def get_single_author(
    ref: str = Field(
        ..., description="Author's ID, ORCID or ROR",

    )
) -> dict:
    """ A tool for fetching OpenAlex's authors. """
    author = Authors()[ref]

    return {
        "id": author['id'],
        "name": author['display_name'],
        "works": author['works_count'],
    }


@tool
def get_single_source(
    ref: str = Field(
        ..., description="Source's ID, DOI or ROR"
    )
) -> dict:
    """ A tool for fetching OpenAlex's sources. """

    source = Sources()[ref]
    return {
        "id": source['id'],
        "name": source['display_name'],
        "works": source['works_count'],
    }


@tool
def get_single_institution(
    ref: str = Field(
        ..., description="Institution's ID, DOI or ROR",
    )
) -> dict:
    """ A tool for fetching OpenAlex's institutions. """
    institution = Institutions()[ref]

    return {
        "id": institution['id'],
        "name": institution['display_name'],
        "works": institution['works_count'],
    }


@tool
def get_single_topic(
    ref: str = Field(
        ..., description="Topic's ID, DOI or ROR",
    )
) -> dict:
    """ A tool for fetching OpenAlex's topics. """
    topic = Topics()[ref]
    return {
        "id": topic['id'],
        "name": topic['display_name'],
        "works": topic['works_count'],
    }


@tool
def search_works(
    abstract: Optional[str] = Field(..., description="Search by the paper's abstract"),
    title: Optional[str] = Field(..., description="Search by the paper's title"),
    display_name: Optional[str] = Field(..., description="Search by the paper's display name"),
    fulltext: Optional[str] = Field(..., description="Search by the paper's fulltext"),
    title_and_abstract: Optional[str] = Field(..., description="Search by the paper's title and abstract"),
    max_works: int = Field(..., description="The max number of works to be returned in the result")
) -> list[dict]:
    """ a tool for searching works by OpenAlex's criteria """

    filters = {
        "abstract": abstract,
        "title": title,
        "display_name": display_name,
        "fulltext": fulltext,
        "title_and_abstract": title_and_abstract,
    }

    filters = dict({
        (k, v) for k, v in filters.items() if v is not None
    })

    works = Works().search_filter(**filters)

    def iterator():
        for page in works.paginate(n_max=max_works):
            for work in page:
                yield work

    return list(map(lambda work: {
        "id": work['id'],
        "title": work['title'],
        "abstract": work['abstract'],
        "open_access": work['open_access'],
    }, iterator()))


all = [
    get_single_work,
    get_single_author,
    get_single_source,
    get_single_institution,
    get_single_topic,
    search_works,
]
