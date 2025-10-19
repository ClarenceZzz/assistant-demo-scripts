"""Placeholder cleaner implementations used during framework bootstrap."""

from __future__ import annotations

from pathlib import Path

from .base import BaseCleaner


class _BaseFileReader(BaseCleaner):
    """Utility base class to offer shared helpers for placeholder cleaners."""

    def clean(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)
        return path.read_text(encoding="utf-8", errors="ignore")


class PDFCleaner(_BaseFileReader):
    """Placeholder PDF cleaner until real implementation is provided."""


class HTMLCleaner(_BaseFileReader):
    """Placeholder HTML cleaner until real implementation is provided."""


class MarkdownCleaner(_BaseFileReader):
    """Placeholder Markdown cleaner until real implementation is provided."""

