"""Cleaner package exposing available cleaner classes."""

from .base import BaseCleaner
from .html import HtmlCleaner
from .pdf import PdfCleaner
from .placeholders import MarkdownCleaner

__all__ = [
    "BaseCleaner",
    "HtmlCleaner",
    "HTMLCleaner",
    "MarkdownCleaner",
    "PdfCleaner",
    "PDFCleaner",
]

HTMLCleaner = HtmlCleaner
PDFCleaner = PdfCleaner
