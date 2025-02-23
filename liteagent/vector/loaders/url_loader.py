import httpx
import markdownify

from liteagent import Provider
from liteagent.providers import openai
from liteagent.vector import Document
from liteagent.vector.loaders.document_loader import DocumentLoader


class URLDocumentLoader(DocumentLoader):
    def __init__(self, url: str, id: str = None, metadata: dict = None, infer_metadata: bool = True,
                 metadata_infer_provider: Provider = openai()):
        self.url = url
        self.id = id
        self.metadata = metadata
        self.infer_metadata = infer_metadata
        self.metadata_infer_provider = metadata_infer_provider

    async def __call__(self) -> Document:
        metadata = self.metadata or {}

        if self.infer_metadata:
            metadata.update(await self.extract_metadata(self.url, self.metadata_infer_provider))

        async with httpx.AsyncClient() as client:
            response = await client.get(self.url)
            response.raise_for_status()

            return Document(
                id=self.id or self.url,
                content=markdownify.markdownify(response.text).strip(),
                metadata={"link": self.url, **metadata}
            )
