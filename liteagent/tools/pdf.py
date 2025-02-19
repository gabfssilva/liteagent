import pymupdf4llm
import requests
from pydantic import Field
from pymupdf import pymupdf

from liteagent import tool


@tool(emoji='📖')
def read_pdf_from_url(url: str = Field(..., description="The PDF URL location")) -> str:
    """ downloads a PDF and returns its content as markdown """

    doc = pymupdf.Document(stream=requests.get(url).content)
    return pymupdf4llm.to_markdown(doc, show_progress=False).strip()
