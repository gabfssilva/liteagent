from liteagent import agent, Provider
from liteagent.tools import read_pdf_from_url, crawl4ai
from liteagent.vector.vector_store import AutomaticMetadata


async def get_metadata(provider: Provider, url: str) -> dict:
    @agent(provider=provider, tools=[read_pdf_from_url, crawl4ai])
    async def metadata_extractor(url: str) -> AutomaticMetadata:
        """
        Extract metadata from the following document: {url}

        Use the tools in this order:

        First:

        - read_pdf_from_url
        - if you get some error, try using crawl4ai
        """

    return (await metadata_extractor(url=url)).to_dict()
