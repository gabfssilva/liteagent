from . import openalex
from . import websearch
from . import wikipedia

from .http_decorator import http
from .openalex import openalex
from .duckduckgo import duckduckgo
# from .crawl4ai import crawl4ai
from .memoria import memoria
from .openmeteo import openmeteo
from .pdf import read_pdf_from_url
from .vision import vision
from .calc import calculator
from .clock import clock
from .py import python_runner
from .vector import vector_store
from .apis import ipify, chuck_norris
from .brasil_api import brasil_api
from .currency_api import currency_api
from .email_sender import email_sender
from .yfinance import yfinance
from .reddit import reddit
from .arxiv import arxiv
from .semantic_scholar import semantic_scholar
from .scopus import scopus
from .web_of_science import web_of_science
from .confluence import confluence
from .jira import jira
from .files import files
from .browser import browser

__all__ = [
    'openalex',
    'read_pdf_from_url',
    'websearch',
    'wikipedia',
    "duckduckgo",
    "crawl4ai",
    'py',
    'memoria',
    'ipify',
    'openmeteo',
    'vision',
    'calculator',
    'clock',
    'python_runner',
    'vector_store',
    'http',
    'currency_api',
    'chuck_norris',
    'brasil_api',
    'email_sender',
    'yfinance',
    'reddit',
    'arxiv',
    'semantic_scholar',
    'scopus',
    'web_of_science',
    'confluence',
    'jira',
    'files',
    'browser'
]
