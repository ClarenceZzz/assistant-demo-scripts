"""Implementation of the PDF cleaner leveraging pdfplumber."""

from __future__ import annotations

import logging
import re
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
    x1: float
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
        x1 = float(raw_word.get("x1", x0))
        size = float(raw_word.get("size", 0.0))
        fontname = str(raw_word.get("fontname", ""))
        return cls(
            text=text,
            x1=x1,
            top=top,
            bottom=bottom,
            x0=x0,
            size=size,
            fontname=fontname,
        )

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
    COLUMN_GAP_MULTIPLIER = 4.0
    MIN_COLUMN_GAP = 40.0
    COLUMN_SPLIT_THRESHOLD_RATIO = 0.18
    MIN_COLUMN_SPLIT_GAP = 120.0
    COLUMN_SEGMENT_RATIO = 0.12
    MAX_COLUMN_SEGMENT_THRESHOLD = 110.0
    PARAGRAPH_TERMINATORS = ("。", "！", "?", "？", "!", "；", ";", "：", ":", ".", "…")
    BULLET_PREFIXES = ("-", "*", "•", "●", "·")
    NUMERIC_NOISE_PATTERN = re.compile(r"^[0-9\s]+$")
    UPPER_LETTER_PATTERN = re.compile(r"^[A-Z]\.?$")
    BULLET_PATTERN = re.compile(r"^(?:\d+[).]|[ivxlcdm]+\.)", re.IGNORECASE)

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
        line_gap_threshold = self._estimate_line_gap(words)
        lines = self._group_words_by_line(words)
        normalized_lines = self._split_line_segments(lines, baseline_size, page.width)
        ordered_columns = self._order_lines_into_columns(normalized_lines, page.width)

        assembled_lines: List[str] = []
        for idx, column_lines in enumerate(ordered_columns):
            column_output: List[str] = []
            previous_top: float | None = None
            for top, line_words in column_lines:
                if previous_top is not None and (top - previous_top) > line_gap_threshold:
                    last_line = self._last_non_empty_line(column_output)
                    if last_line and not last_line.startswith("## "):
                        self._append_blank_line(column_output)
                text = self._assemble_line(line_words, baseline_size)
                self._append_line_with_continuation(column_output, text)
                if text:
                    previous_top = top
            assembled_lines.extend(column_output)
            if idx < len(ordered_columns) - 1 and column_output:
                self._append_blank_line(assembled_lines)

        return "\n".join(line for line in assembled_lines if line is not None).strip()

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

    def _split_line_segments(
        self,
        lines: Sequence[tuple[float, List[_Word]]],
        baseline_size: float,
        page_width: float,
    ) -> List[tuple[float, List[_Word]]]:
        """Split lines containing multiple columns into separate segments."""

        normalized: List[tuple[float, List[_Word]]] = []
        gap_threshold = max(baseline_size * self.COLUMN_GAP_MULTIPLIER, self.MIN_COLUMN_GAP)
        width_threshold = max(
            gap_threshold,
            min(page_width * self.COLUMN_SEGMENT_RATIO, self.MAX_COLUMN_SEGMENT_THRESHOLD),
        )

        for top, line_words in lines:
            if not line_words:
                continue
            segments: List[List[_Word]] = []
            current_segment: List[_Word] = [line_words[0]]
            previous_word = line_words[0]

            for word in line_words[1:]:
                gap = word.x0 - previous_word.x1
                if gap > width_threshold:
                    segments.append(current_segment)
                    current_segment = [word]
                else:
                    current_segment.append(word)
                previous_word = word

            segments.append(current_segment)

            for segment in segments:
                if segment:
                    normalized.append((top, segment))

        normalized.sort(key=lambda item: (item[0], item[1][0].x0))
        return normalized

    def _order_lines_into_columns(
        self,
        lines: Sequence[tuple[float, List[_Word]]],
        page_width: float,
    ) -> List[List[tuple[float, List[_Word]]]]:
        """Group lines into columns when multi-column layout is detected."""

        if not lines:
            return []

        line_meta: List[tuple[float, List[_Word], float]] = []
        for top, line_words in lines:
            centroid = self._line_centroid(line_words)
            line_meta.append((top, line_words, centroid))

        boundary = self._detect_column_boundary(
            [meta[2] for meta in line_meta],
            page_width,
        )

        if boundary is None:
            single_column = sorted(line_meta, key=lambda item: item[0])
            return [[(top, words) for top, words, _ in single_column]]

        columns: Dict[int, List[tuple[float, List[_Word]]]] = defaultdict(list)
        column_centers: Dict[int, List[float]] = defaultdict(list)

        for top, line_words, centroid in line_meta:
            column_idx = 0 if centroid <= boundary else 1
            columns[column_idx].append((top, line_words))
            column_centers[column_idx].append(centroid)

        ordered_columns: List[tuple[float, List[tuple[float, List[_Word]]]]] = []
        for column_idx, column_lines in columns.items():
            column_lines.sort(key=lambda item: (item[0], item[1][0].x0))
            average_centroid = (
                sum(column_centers[column_idx]) / len(column_centers[column_idx])
                if column_centers[column_idx]
                else float(column_idx)
            )
            ordered_columns.append((average_centroid, column_lines))

        ordered_columns.sort(key=lambda item: item[0])
        return [column_lines for _, column_lines in ordered_columns]

    def _line_centroid(self, line_words: Sequence[_Word]) -> float:
        """Return the median horizontal position of the words composing a line."""

        positions = [(word.x0 + word.x1) / 2 for word in line_words]
        return float(median(positions)) if positions else 0.0

    def _detect_column_boundary(
        self,
        centroids: Sequence[float],
        page_width: float,
    ) -> float | None:
        """Detect the column boundary using the widest gap between line centroids."""

        unique_centroids = sorted(set(centroids))
        if len(unique_centroids) < 2:
            return None

        max_gap = 0.0
        boundary = None
        for left, right in zip(unique_centroids, unique_centroids[1:]):
            gap = right - left
            if gap > max_gap:
                max_gap = gap
                boundary = (left + right) / 2

        min_required_gap = max(
            self.MIN_COLUMN_SPLIT_GAP,
            page_width * self.COLUMN_SPLIT_THRESHOLD_RATIO,
        )
        if max_gap < min_required_gap:
            return None

        return boundary

    def _estimate_line_gap(self, words: Sequence[_Word]) -> float:
        """Estimate a threshold to detect paragraph gaps between lines."""

        heights = [word.bottom - word.top for word in words if word.bottom >= word.top]
        if not heights:
            return 12.0
        baseline_height = median(heights)
        return float(baseline_height * 2.0)

    def _assemble_line(self, line_words: Sequence[_Word], baseline_size: float) -> str:
        """Assemble words into a single line and decorate headings when detected."""

        text = " ".join(word.text for word in line_words).strip()
        if not text:
            return ""

        if self._is_heading_line(line_words, baseline_size):
            normalized = text.lstrip("# ")
            text = f"## {normalized}".strip()

        return text

    def _append_line_with_continuation(self, lines: List[str], text: str) -> None:
        """Append text to the list while merging sentence fragments when appropriate."""

        if not text or self._is_noise_line(text):
            return
        if not lines:
            lines.append(text)
            return
        previous = lines[-1]
        if previous and previous != "" and self._should_merge_with_previous(previous, text):
            lines[-1] = f"{previous} {text}"
        else:
            lines.append(text)

    def _append_blank_line(self, lines: List[str]) -> None:
        """Append a blank separator avoiding duplicated empty lines."""

        if not lines or lines[-1] != "":
            lines.append("")

    def _last_non_empty_line(self, lines: Sequence[str]) -> str:
        """Return the most recent non-empty line if available."""

        for line in reversed(lines):
            if line:
                return line
        return ""

    def _should_merge_with_previous(self, previous: str, current: str) -> bool:
        """Return whether the current line should continue the previous one."""

        if previous.startswith("## ") or current.startswith("## "):
            return False
        if previous.endswith(self.PARAGRAPH_TERMINATORS):
            return False
        if previous[-1].isdigit():
            return False
        if self._starts_with_bullet(current):
            return False
        return True

    def _starts_with_bullet(self, text: str) -> bool:
        """Check whether the provided text looks like a bullet point."""

        stripped = text.lstrip()
        if not stripped:
            return False
        if stripped.startswith(self.BULLET_PREFIXES):
            return True
        return bool(self.BULLET_PATTERN.match(stripped))

    def _is_noise_line(self, text: str) -> bool:
        """Detect lines that should be discarded before assembling the result."""

        stripped = text.strip()
        if not stripped:
            return True
        if self.NUMERIC_NOISE_PATTERN.fullmatch(stripped):
            return True
        if self.UPPER_LETTER_PATTERN.fullmatch(stripped):
            return True
        return False

    def _is_heading_line(self, line_words: Sequence[_Word], baseline_size: float) -> bool:
        """Determine whether the provided line qualifies as a heading."""

        if not line_words:
            return False
        return any(
            word.is_heading_candidate(baseline_size, self.HEADING_SIZE_MULTIPLIER)
            for word in line_words
        )

    # TODO: future enhancement - incorporate embedded images or figures extraction.
