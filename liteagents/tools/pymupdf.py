import pymupdf4llm
import requests
from pydantic import Field
from pymupdf import pymupdf

from liteagents import tool


@tool
def read_pdf_from_url(url: str = Field(..., description="The PDF URL location")):
    """ downloads a PDF and returns its content as markdown """

    doc = pymupdf.Document(stream=requests.get(url).content)
    return pymupdf4llm.to_markdown(doc, show_progress=False).strip()
