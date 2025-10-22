"""Recursive text splitter implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class RecursiveTextSplitter:
    """Split text into overlapping chunks of a fixed size.

    Parameters
    ----------
    chunk_size:
        Maximum length of each chunk. Must be a positive integer.
    overlap:
        Number of characters to overlap between consecutive chunks.
        Must be a non-negative integer strictly smaller than ``chunk_size``.
    """

    chunk_size: int
    overlap: int

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.overlap < 0:
            raise ValueError("overlap must be non-negative")
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

    def split(self, text: str | None) -> List[str]:
        """Split the provided text into overlapping chunks.

        Parameters
        ----------
        text:
            The text that should be split. ``None`` and empty strings
            result in an empty list.
        """

        if not text:
            return []

        length = len(text)
        if length <= self.chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        while start < length:
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            if end >= length:
                break
            start = end - self.overlap
        return chunks
