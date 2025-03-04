from pydantic import Field

from liteagent import tool, Tools
import httpx
from typing import Optional, Union, Dict, List, Literal

# Semantic Scholar field types
SemanticScholarField = Literal[
    'title', 'year', 'abstract', 'authors', 'authors.name', 'openAccessPdf.url', 
    'citationCount', 'referenceCount', 'url', 'references', 'citations',
    'name', 'paperCount', 'papers'
]


class SemanticScholar(Tools):
    _client: httpx.AsyncClient

    def __init__(
        self,
        base_url: str = "https://api.semanticscholar.org/graph/v1",
        api_key: Union[str, None] = None
    ):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"x-api-key": api_key} if api_key else {}
        )
    
    @tool(emoji='🔍')
    async def search(
        self, 
        query: str, 
        limit: Optional[int] = 10,
        fields: List[SemanticScholarField] = [
            "title",
            "year",
            "abstract",
            "authors.name",
            "openAccessPdf.url",
            "citationCount",
            "referenceCount"
        ]
    ) -> Dict:
        """
        Search for academic papers on Semantic Scholar.
        """
        fields_str = ",".join(fields)
        url = f"/paper/search?query={query}&limit={limit}&fields={fields_str}"
        
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()
    
    @tool(emoji='📄')
    async def paper(
        self, 
        paper_id: str, 
        fields: List[SemanticScholarField] = [
            "title",
            "year",
            "authors",
            "abstract",
            "url",
            "references",
            "citations"
        ]
    ) -> Dict:
        """
        Get detailed information about a specific paper on Semantic Scholar.
        """
        fields_str = ",".join(fields)
        url = f"/paper/{paper_id}?fields={fields_str}"
        
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()
    
    @tool(emoji='👤')
    async def author(
        self, 
        author_id: str, 
        fields: List[SemanticScholarField] = [
            "name",
            "paperCount",
            "citationCount",
            "papers"
        ]
    ) -> Dict:
        """
        Get information about a specific author on Semantic Scholar.
        """
        fields_str = ",".join(fields)
        url = f"/author/{author_id}?fields={fields_str}"
        
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()
    
    @tool(emoji='👥')
    async def author_search(
        self, 
        query: str = Field(..., description="The author's name"),
        limit: Optional[int] = 10,
        fields: List[SemanticScholarField] = [
            "name",
            "paperCount",
            "citationCount"
        ]
    ) -> Dict:
        """
        Search for authors on Semantic Scholar.
        """
        fields_str = ",".join(fields)
        url = f"/author/search?query={query}&limit={limit}&fields={fields_str}"
        
        response = await self._client.get(url)
        response.raise_for_status()
        return response.json()


def semantic_scholar(api_key: Union[str, None] = None) -> SemanticScholar:
    return SemanticScholar(api_key=api_key)
