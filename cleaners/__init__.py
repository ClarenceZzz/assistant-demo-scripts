"""Cleaner package exposing available cleaner classes."""

from .base import BaseCleaner
from .pdf import PdfCleaner
from .placeholders import HTMLCleaner, MarkdownCleaner

__all__ = [
    "BaseCleaner",
    "HTMLCleaner",
    "MarkdownCleaner",
    "PdfCleaner",
    "PDFCleaner",
]

PDFCleaner = PdfCleaner
