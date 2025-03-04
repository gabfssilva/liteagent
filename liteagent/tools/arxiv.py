from typing import List, Literal, Optional, Union
import httpx
from pydantic import Field

from liteagent import tool, Tools
from liteagent.tools.http_decorator import http


class ArXiv(Tools):
    """Tools for interacting with the arXiv API to search and retrieve academic papers."""
    
    def base_name(self):
        return "arxiv"

    @tool(emoji='📚')
    @http(
        url="http://export.arxiv.org/api/query",
        method="GET",
        params={
            "search_query": "{query}",
            "start": "{start}",
            "max_results": "{max_results}"
        },
        accept='rss'
    )
    async def search(
        self,
        query: str = Field(..., description="Search query string in the format 'term:value'. Use prefixes like 'ti:' for title, 'au:' for author, 'abs:' for abstract, 'cat:' for category, etc."),
        start: int = Field(..., description="Starting index for returned results"),
        max_results: int | None = Field(..., description="Maximum number of results to return. Defaults to 100, cannot be higher than 100."),
    ) -> dict:
        """
        Search for papers on arXiv based on query parameters.
        
        Example queries:
        - "ti:machine learning" (search in title)
        - "au:Hinton" (search for author)
        - "cat:cs.AI" (search in category Computer Science AI)
        - "all:quantum" (search in all fields)
        """
    
    @tool(emoji='📄')
    async def get_paper_details(
        self,
        paper_id: str = Field(..., description="arXiv paper ID (e.g., '2101.00123' or full URL)")
    ) -> dict:
        """
        Get detailed information about a specific arXiv paper by ID.
        
        Returns paper metadata including title, authors, abstract, categories,
        publication date, and links to PDF and abstract pages.
        """
        # Extract ID if a full URL was provided
        if "arxiv.org" in paper_id:
            # Handle different URL formats
            if "/abs/" in paper_id:
                paper_id = paper_id.split("/abs/")[1].split("v")[0]
            elif "/pdf/" in paper_id:
                paper_id = paper_id.split("/pdf/")[1].split("v")[0].split(".pdf")[0]
        
        # Format the query to search by ID
        url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Process XML response to extract paper details
            # For simplicity, we'll use a basic approach to extract information
            # In a production environment, consider using a proper XML parser
            
            xml = response.text
            
            # Basic extraction of paper details
            title = self._extract_between(xml, "<title>", "</title>", start_after="<entry>")
            abstract = self._extract_between(xml, "<summary>", "</summary>")
            
            # Extract authors
            authors = []
            author_start = 0
            while True:
                author_tag_start = xml.find("<author>", author_start)
                if author_tag_start == -1:
                    break
                    
                name_start = xml.find("<name>", author_tag_start) + 6
                name_end = xml.find("</name>", name_start)
                authors.append(xml[name_start:name_end])
                author_start = name_end
            
            # Extract categories
            categories = []
            category_start = 0
            while True:
                category_tag_start = xml.find('term="', category_start)
                if category_tag_start == -1 or category_tag_start > xml.find("</entry>"):
                    break
                    
                category_start = category_tag_start + 6
                category_end = xml.find('"', category_start)
                categories.append(xml[category_start:category_end])
                category_start = category_end
            
            # Extract URLs
            abstract_url = self._extract_between(xml, '<link href="', '"', start_after='rel="alternate"')
            pdf_url = self._extract_between(xml, '<link href="', '"', start_after='rel="related"')
            
            # Published date
            published = self._extract_between(xml, "<published>", "</published>")
            updated = self._extract_between(xml, "<updated>", "</updated>")
            
            return {
                "id": paper_id,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "categories": categories,
                "published": published,
                "updated": updated,
                "urls": {
                    "abstract": abstract_url,
                    "pdf": pdf_url
                }
            }
    
    def _extract_between(self, text: str, start_tag: str, end_tag: str, start_after: Union[str, None] = None) -> str:
        """Helper method to extract text between tags in XML."""
        if start_after:
            start_pos = text.find(start_after)
            if start_pos == -1:
                return ""
            text = text[start_pos:]
            
        start_pos = text.find(start_tag)
        if start_pos == -1:
            return ""
            
        start_pos += len(start_tag)
        end_pos = text.find(end_tag, start_pos)
        
        if end_pos == -1:
            return ""
            
        return text[start_pos:end_pos].strip()


# Create an instance of the ArXiv tools class
arxiv = ArXiv()