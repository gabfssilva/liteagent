from abc import ABCMeta, abstractmethod, ABC
from typing import Callable, Awaitable, List, Any, Coroutine

from pydantic import BaseModel
from liteagent import agent, Provider
from liteagent.providers import openai
from liteagent.tools import read_pdf_from_url, crawl4ai
from liteagent.vector import Document

class DocumentLoader(ABC):
    @abstractmethod
    async def __call__(self) -> Document:
        raise NotImplementedError

    def __await__(self):
        return self.__call__().__await__()

    async def extract_metadata(self, url: str, metadata_infer_provider: Provider = openai()) -> dict:
        @agent(provider=metadata_infer_provider, tools=[read_pdf_from_url, crawl4ai], intercept=None)
        async def metadata_extractor(url: str) -> AutomaticMetadata:
            """
            Extract metadata from the following document: {url}

            Use the tools in this order:

            First:

            - read_pdf_from_url
            - if you get some error, try using crawl4ai
            """

        return (await metadata_extractor(url=url)).to_dict()


class AutomaticMetadata(BaseModel):
    id: str
    title: str
    source: str
    summary: str
    keywords: List[str]
    categories: List[str]
    authors: List[str]
    date: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "keywords": f'[{",".join(self.keywords)}]',
            "categories": f'[{",".join(self.categories)}]',
            "authors": f'[{",".join(self.authors)}]',
            "date": self.date,
        }
