"""Implementation of the PDF cleaner leveraging pdfplumber."""

from __future__ import annotations

import logging
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Dict, List, Sequence

import pdfplumber

try:  # pragma: no cover - fallback for environments missing optional symbols
    from pdfminer.pdfparser import PDFSyntaxError as PdfMinerSyntaxError
except Exception:  # noqa: BLE001 - pdfminer is an optional dependency of pdfplumber
    PdfMinerSyntaxError = type("PdfMinerSyntaxError", (Exception,), {})

try:  # pragma: no cover - some pdfplumber versions expose PDFSyntaxError
    from pdfplumber.pdf import PDFSyntaxError as PdfPlumberSyntaxError  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 - fallback to pdfminer error type when unavailable
    PdfPlumberSyntaxError = PdfMinerSyntaxError

from .base import BaseCleaner

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Word:
    """Internal representation of a PDF word enriched with metadata."""

    text: str
    top: float
    bottom: float
    x0: float
    size: float
    fontname: str

    @classmethod
    def from_pdfplumber(cls, raw_word: Dict[str, object]) -> "_Word":
        """Build a word instance from the dictionary returned by pdfplumber."""

        text = str(raw_word.get("text", "")).strip()
        top = float(raw_word.get("top", 0.0))
        bottom = float(raw_word.get("bottom", 0.0))
        x0 = float(raw_word.get("x0", 0.0))
        size = float(raw_word.get("size", 0.0))
        fontname = str(raw_word.get("fontname", ""))
        return cls(text=text, top=top, bottom=bottom, x0=x0, size=size, fontname=fontname)

    def is_heading_candidate(self, baseline_size: float, size_multiplier: float) -> bool:
        """Return whether the word should be considered part of a heading."""

        if not self.text:
            return False
        larger_font = baseline_size > 0 and self.size >= baseline_size * size_multiplier
        bold_font = "bold" in self.fontname.lower()
        return larger_font or bold_font


class PdfCleaner(BaseCleaner):
    """Cleaner implementation dedicated to PDF documents."""

    HEADER_RATIO = 0.1
    FOOTER_RATIO = 0.9
    HEADING_SIZE_MULTIPLIER = 1.2

    def __init__(self) -> None:
        self._logger = LOGGER

    def clean(self, file_path: str) -> str:
        """Clean the provided PDF file and return normalized UTF-8 text."""

        try:
            with pdfplumber.open(file_path) as pdf:
                pages_content: List[str] = []
                for page_number, page in enumerate(pdf.pages, start=1):
                    page_text = self._process_page(page, page_number)
                    if page_text:
                        pages_content.append(page_text)
                cleaned = "\n\n".join(pages_content)
        except (PdfPlumberSyntaxError, PdfMinerSyntaxError) as exc:
            msg = f"Failed to parse PDF file: {file_path}"
            self._logger.exception(msg)
            raise ValueError(msg) from exc
        except OSError as exc:
            msg = f"Unable to open PDF file: {file_path}"
            self._logger.exception(msg)
            raise ValueError(msg) from exc

        normalized = unicodedata.normalize("NFKC", cleaned)
        return normalized.strip()

    def _process_page(self, page: pdfplumber.page.Page, page_number: int) -> str:
        """Process a single PDF page and return the cleaned textual representation."""

        words = self._extract_filtered_words(page)
        if not words:
            self._logger.debug("Page %s yielded no words after filtering", page_number)
            fallback = page.extract_text() or ""
            return fallback.strip()

        baseline_size = self._determine_body_font_size(words)
        lines = self._group_words_by_line(words)

        assembled_lines: List[str] = []
        previous_top: float | None = None
        line_gap_threshold = self._estimate_line_gap(words)

        for top, line_words in lines:
            if previous_top is not None and (top - previous_top) > line_gap_threshold:
                assembled_lines.append("")
            text = self._assemble_line(line_words, baseline_size)
            if text:
                assembled_lines.append(text)
                previous_top = top

        return "\n".join(assembled_lines).strip()

    def _extract_filtered_words(self, page: pdfplumber.page.Page) -> List[_Word]:
        """Extract words from the page while removing header and footer content."""

        raw_words = page.extract_words(
            keep_blank_chars=False,
            use_text_flow=True,
            extra_attrs=["fontname", "size"],
        )
        header_cutoff = page.height * self.HEADER_RATIO
        footer_cutoff = page.height * self.FOOTER_RATIO

        filtered: List[_Word] = []
        for raw_word in raw_words:
            word = _Word.from_pdfplumber(raw_word)
            if not word.text:
                continue
            if word.top < header_cutoff:
                continue
            if word.bottom > footer_cutoff:
                continue
            filtered.append(word)
        return filtered

    def _determine_body_font_size(self, words: Sequence[_Word]) -> float:
        """Estimate the baseline body font size using the median of all words."""

        sizes = [word.size for word in words if word.size > 0]
        if not sizes:
            return 0.0
        return float(median(sizes))

    def _group_words_by_line(self, words: Sequence[_Word]) -> List[tuple[float, List[_Word]]]:
        """Group words into lines based on their vertical positioning."""

        lines: Dict[float, List[_Word]] = defaultdict(list)
        for word in words:
            line_key = round(word.top, 1)
            lines[line_key].append(word)

        sorted_lines: List[tuple[float, List[_Word]]] = []
        for top in sorted(lines.keys()):
            line_words = sorted(lines[top], key=lambda item: item.x0)
            sorted_lines.append((top, line_words))
        return sorted_lines

    def _estimate_line_gap(self, words: Sequence[_Word]) -> float:
        """Estimate a threshold to detect paragraph gaps between lines."""

        heights = [word.bottom - word.top for word in words if word.bottom >= word.top]
        if not heights:
            return 12.0
        baseline_height = median(heights)
        return float(baseline_height * 1.5)

    def _assemble_line(self, line_words: Sequence[_Word], baseline_size: float) -> str:
        """Assemble words into a single line and decorate headings when detected."""

        text = " ".join(word.text for word in line_words).strip()
        if not text:
            return ""

        if self._is_heading_line(line_words, baseline_size):
            normalized = text.lstrip("# ")
            text = f"## {normalized}".strip()

        return text

    def _is_heading_line(self, line_words: Sequence[_Word], baseline_size: float) -> bool:
        """Determine whether the provided line qualifies as a heading."""

        if not line_words:
            return False
        return any(
            word.is_heading_candidate(baseline_size, self.HEADING_SIZE_MULTIPLIER)
            for word in line_words
        )

    # TODO: future enhancement - incorporate embedded images or figures extraction.
