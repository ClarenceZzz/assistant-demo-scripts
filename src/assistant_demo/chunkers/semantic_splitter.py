"""Semantic text splitter based on Markdown headings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


_HEADING_PATTERN = re.compile(r"^(?P<hashes>#{1,6})\s+.*$", re.MULTILINE)


@dataclass
class SemanticSplitter:
    """Split text into sections according to Markdown headings.

    Parameters
    ----------
    min_heading_level:
        Smallest heading level (inclusive) that should trigger a new chunk.
    max_heading_level:
        Largest heading level (inclusive) to consider while splitting.
    """

    min_heading_level: int = 2
    max_heading_level: int = 6

    def __post_init__(self) -> None:
        if not 1 <= self.min_heading_level <= self.max_heading_level <= 6:
            raise ValueError("Heading levels must satisfy 1 <= min <= max <= 6.")

    def split(self, text: str | None) -> List[str]:
        """Split ``text`` into semantic chunks based on Markdown headings."""

        if text is None:
            return []

        if text.strip() == "":
            return []

        matches = [
            match
            for match in _HEADING_PATTERN.finditer(text)
            if self.min_heading_level <= len(match.group("hashes")) <= self.max_heading_level
        ]

        if not matches:
            return [text]

        chunks: List[str] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

        return chunks
