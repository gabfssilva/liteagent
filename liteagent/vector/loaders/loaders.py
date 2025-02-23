from liteagent import Provider
from liteagent.providers import openai
from liteagent.vector.loaders import DocumentLoader, URLDocumentLoader, PDFDocumentLoader


def from_url(
    url: str,
    id: str = None,
    metadata: dict = None,
    infer_metadata: bool = True,
    metadata_infer_provider: Provider = openai()
) -> DocumentLoader:
    return URLDocumentLoader(
        url,
        id=id,
        metadata=metadata,
        infer_metadata=infer_metadata,
        metadata_infer_provider=metadata_infer_provider
    )


def from_pdf(
    url: str,
    id: str = None,
    metadata: dict = None,
    infer_metadata: bool = True,
    metadata_infer_provider: Provider = openai()
) -> DocumentLoader:
    return PDFDocumentLoader(
        url,
        id=id,
        metadata=metadata,
        infer_metadata=infer_metadata,
        metadata_infer_provider=metadata_infer_provider
    )
