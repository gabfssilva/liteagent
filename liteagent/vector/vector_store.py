from abc import abstractmethod
from typing import List, AsyncIterator, AsyncIterable

import markdownify
import pymupdf4llm
import requests
from pydantic import BaseModel
from pymupdf import pymupdf

class AutomaticMetadata(BaseModel):
    id: str
    title: str
    source: str
    keywords: List[str]
    categories: List[str]
    authors: List[str]
    date: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "keywords": f'[{",".join(self.keywords)}]',
            "categories": f'[{",".join(self.categories)}]',
            "authors": f'[{",".join(self.authors)}]',
            "date": self.date,
        }


class Document(BaseModel):
    id: str
    content: str
    metadata: dict = {}

    @staticmethod
    def from_pdf(
        url: str,
        id: str = None,
        metadata: dict = {},
    ) -> "Document":
        doc = pymupdf.Document(stream=requests.get(url).content)

        return Document(
            id=id or url,
            content=pymupdf4llm.to_markdown(doc, show_progress=False).strip(),
            metadata={
                "link": url,
                **metadata
            }
        )

    @staticmethod
    def from_link(url: str) -> "Document":
        return Document(
            id=url,
            content=markdownify.markdownify(requests.get(url).content),
            metadata={
                "link": url,
            }
        )

class Chunk(BaseModel):
    content: str
    metadata: dict = {}
    distance: float = 0.0

class Chunks(BaseModel):
    chunks: List[Chunk]

class VectorStore:
    @abstractmethod
    async def store(self, documents: AsyncIterator[Document]):
        pass

    @abstractmethod
    async def search(self, text: str, count: int) -> AsyncIterable[Chunk]:
        pass

    @abstractmethod
    async def delete(self, document: Document):
        pass
