from typing import Dict

import httpx
from pydantic import Field

from liteagent import tool, Tools


class Scopus(Tools):
    """Tools for interacting with the Elsevier Scopus API to search and retrieve academic papers."""

    _client: httpx.AsyncClient

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.elsevier.com/content"
    ):
        """
        Initialize the Scopus API client.
        
        Args:
            api_key: The Elsevier API key required for authentication
            base_url: The base URL for the Scopus API
        """
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "X-ELS-APIKey": api_key,
                "Accept": "application/json"
            }
        )

    @tool(emoji='🔍')
    async def search(
        self,
        query: str = Field(..., description="Search query string using Scopus search syntax"),
        start: int = Field(0, description="Starting index for returned results"),
        count: int = Field(25, description="Maximum number of results to return (max 200)"),
        sort: str = Field("relevancy", description="Sorting criteria (relevancy, date, cited)")
    ) -> Dict:
        """
        Search for academic papers on Scopus using advanced query syntax.
        
        Example queries:
        - "TITLE-ABS-KEY(machine learning)"
        - "AU-NAME(Smith) AND PUBYEAR > 2020"
        - "SRCTITLE(Nature) AND TITLE(quantum)"
        
        Returns metadata about matching documents including title, authors, source, citation info.
        """
        params = {
            "query": query,
            "start": start,
            "count": min(count, 200),  # API limit
            "sort": sort
        }

        url = "/search/scopus"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @tool(emoji='📄')
    async def abstract(
        self,
        scopus_id: str = Field(..., description="Scopus Document ID"),
        view: str = Field("FULL", description="View type: STANDARD, COMPLETE or FULL")
    ) -> Dict:
        """
        Retrieve detailed abstract information for a specific document by Scopus ID.
        
        Returns comprehensive metadata including abstract, authors, affiliations,
        keywords, funding, and citation information.
        """
        params = {"view": view}

        url = f"/abstract/scopus_id/{scopus_id}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @tool(emoji='📚')
    async def citations(
        self,
        scopus_id: str = Field(..., description="Scopus Document ID"),
        start: int = Field(0, description="Starting index for returned results"),
        count: int = Field(25, description="Maximum number of results to return (max 200)")
    ) -> Dict:
        """
        Retrieve articles that cite the specified document.
        
        Returns a list of citing documents with their metadata.
        """
        params = {
            "start": start,
            "count": min(count, 200)  # API limit
        }

        url = f"/abstract/citations/{scopus_id}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @tool(emoji='👤')
    async def author(
        self,
        author_id: str = Field(..., description="Scopus Author ID"),
        view: str = Field("COMPLETE", description="View type: LIGHT, STANDARD or COMPLETE")
    ) -> Dict:
        """
        Retrieve detailed information about a specific author by Scopus Author ID.
        
        Returns comprehensive author profile including name, affiliations, 
        publication history, h-index, and citation metrics.
        """
        params = {"view": view}

        url = f"/author/author_id/{author_id}"
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client session."""
        await self._client.aclose()


def scopus(api_key: str) -> Scopus:
    """
    Create and return a Scopus API client instance.
    
    Args:
        api_key: The Elsevier API key required for authentication
        
    Returns:
        A configured Scopus API client
    """
    return Scopus(api_key=api_key)
