from typing import Dict

import httpx
from pydantic import Field

from liteagent import tool, Tools


class WebOfScience(Tools):
    """Tools for interacting with the Clarivate Web of Science API to search and retrieve academic papers."""

    _client: httpx.AsyncClient

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://wos-api.clarivate.com/api/wos"
    ):
        """
        Initialize the Web of Science API client.
        
        Args:
            api_key: The Clarivate API key required for authentication
            base_url: The base URL for the Web of Science API
        """
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "X-ApiKey": api_key,
                "Accept": "application/json"
            }
        )

    @tool(emoji='🔍')
    async def search(
        self,
        query: str = Field(..., description="Search query using Web of Science query syntax"),
        database: str = Field("WOS", description="Database ID: WOS, BCI, DRCI, etc."),
        count: int = Field(25, description="Maximum number of results to return (max 100)"),
        first_record: int = Field(1, description="First record to return, 1-based indexing"),
        sort_field: str = Field("RS",
                                description="Field to sort by: RS (relevance), TC (citations), PY (publication year)")
    ) -> Dict:
        """
        Search for academic papers in Web of Science using advanced query syntax.
        
        Example queries:
        - "TS=(artificial intelligence AND machine learning)"
        - "AU=(Smith J*) AND PY=2020-2023"
        - "SO=Nature AND OG=Stanford"
        
        Returns metadata about matching documents including title, authors, source, times cited.
        """
        params = {
            "databaseId": database,
            "usrQuery": query,
            "count": min(count, 100),  # API limit
            "firstRecord": first_record,
            "sortField": sort_field
        }

        url = "/query"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @tool(emoji='📄')
    async def retrieve(
        self,
        ut: str = Field(..., description="Unique identifier (UT) for the Web of Science record"),
        unique_id_type: str = Field("UT", description="ID type: UT (WoS unique ID), DOI, PMID, etc.")
    ) -> Dict:
        """
        Retrieve detailed information for a specific document by its unique identifier.
        
        Returns comprehensive metadata including document data, funding, categories,
        cited references, and more.
        """
        params = {
            "uniqueId": ut,
            "uniqueIdType": unique_id_type
        }

        url = "/retrieved"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @tool(emoji='📊')
    async def cited_references(
        self,
        ut: str = Field(..., description="Unique identifier (UT) for the Web of Science record"),
        count: int = Field(25, description="Maximum number of results to return (max: 100)"),
        first_record: int = Field(1, description="First record to return, 1-based indexing")
    ) -> Dict:
        """
        Retrieve cited references for a specific document by its unique identifier.
        
        Returns detailed information about works cited by the specified document.
        """
        params = {
            "uniqueId": ut,
            "count": min(count, 100),  # API limit
            "firstRecord": first_record
        }

        url = "/citedReferences"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @tool(emoji='🔬')
    async def citing_articles(
        self,
        ut: str = Field(..., description="Unique identifier (UT) for the Web of Science record"),
        count: int = Field(25, description="Maximum number of results to return (max: 100)"),
        first_record: int = Field(1, description="First record to return, 1-based indexing"),
        sort_field: str = Field("RS", description="Field to sort by: RS (relevance), TC (times cited), PY (pub year)")
    ) -> Dict:
        """
        Retrieve articles that cite the specified document.
        
        Returns a list of citing documents with their metadata.
        """
        params = {
            "uniqueId": ut,
            "count": min(count, 100),  # API limit
            "firstRecord": first_record,
            "sortField": sort_field
        }

        url = "/citingArticles"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @tool(emoji='🌐')
    async def related_records(
        self,
        ut: str = Field(..., description="Unique identifier (UT) for the Web of Science record"),
        count: int = Field(25, description="Maximum number of results to return (max: 100)"),
        first_record: int = Field(1, description="First record to return, 1-based indexing")
    ) -> Dict:
        """
        Find records related to the specified document based on shared references.
        
        Returns a list of related documents with their metadata.
        """
        params = {
            "uniqueId": ut,
            "count": min(count, 100),  # API limit
            "firstRecord": first_record
        }

        url = "/relatedRecords"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client session."""
        await self._client.aclose()


def web_of_science(api_key: str) -> WebOfScience:
    """
    Create and return a Web of Science API client instance.
    
    Args:
        api_key: The Clarivate API key required for authentication
        
    Returns:
        A configured Web of Science API client
    """
    return WebOfScience(api_key=api_key)
