import httpx
from pydantic import Field

from liteagent import tool
from liteagent.internal import depends_on


@tool(emoji='📖')
@depends_on({
    "pymupdf4llm": "pymupdf4llm",
    "pymupdf": "pymupdf"
})
def read_pdf_from_url(url: str = Field(..., description="The PDF URL location")) -> str:
    """ downloads a PDF and returns its content as markdown """
    from pymupdf4llm import to_markdown
    from pymupdf import pymupdf

    doc = pymupdf.Document(stream=httpx.get(url).content)
    return to_markdown(doc, show_progress=False).strip()
