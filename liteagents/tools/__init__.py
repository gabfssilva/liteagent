from .openalex import search_works, get_single_author, get_single_institution, get_single_source, get_single_work, \
    get_single_topic, all

from . import websearch
from . import wikipedia
from . import py

from .pymupdf import read_pdf_from_url

__all__ = [
    'search_works',
    'get_single_author',
    'get_single_institution',
    'get_single_source',
    'get_single_work',
    'get_single_topic',
    'read_pdf_from_url',
    'websearch',
    'wikipedia',
    'py'
]
