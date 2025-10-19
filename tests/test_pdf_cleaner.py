"""Tests covering PdfCleaner core behaviours."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pytest

from cleaners.pdf import PdfCleaner


@dataclass
class _FakePage:
    """Lightweight pdfplumber page stand-in for unit tests."""

    height: float
    words: List[Dict[str, object]]
    fallback_text: str = ""

    def extract_words(self, *args, **kwargs) -> List[Dict[str, object]]:
        return self.words

    def extract_text(self) -> str:
        return self.fallback_text


@dataclass
class _FakePDF:
    """Context manager mimicking pdfplumber.open return type."""

    pages: Iterable[_FakePage]

    def __enter__(self) -> "_FakePDF":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def _word(
    text: str,
    *,
    top: float,
    bottom: float,
    x0: float,
    size: float,
    fontname: str = "Helvetica",
) -> Dict[str, object]:
    return {
        "text": text,
        "top": top,
        "bottom": bottom,
        "x0": x0,
        "size": size,
        "fontname": fontname,
    }


def _patch_pdf(monkeypatch: pytest.MonkeyPatch, fake_pdf: _FakePDF) -> None:
    monkeypatch.setattr("cleaners.pdf.pdfplumber.open", lambda _path: fake_pdf)


def test_pdf_cleaner_filters_header_and_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        height=1000.0,
        words=[
            _word("Header", top=40.0, bottom=70.0, x0=10.0, size=10.0),
            _word("Body", top=200.0, bottom=230.0, x0=50.0, size=10.0),
            _word("content", top=200.0, bottom=230.0, x0=120.0, size=10.0),
            _word("Footer", top=930.0, bottom=970.0, x0=15.0, size=10.0),
        ],
    )
    _patch_pdf(monkeypatch, _FakePDF(pages=[page]))

    result = cleaner.clean("ignored.pdf")

    assert result == "Body content"


def test_pdf_cleaner_marks_headings(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        height=800.0,
        words=[
            _word("Annual", top=120.0, bottom=155.0, x0=40.0, size=15.0, fontname="Helvetica-Bold"),
            _word("Report", top=120.0, bottom=155.0, x0=120.0, size=15.0, fontname="Helvetica-Bold"),
            _word("Overview", top=220.0, bottom=250.0, x0=40.0, size=10.0),
            _word("details", top=220.0, bottom=250.0, x0=120.0, size=10.0),
        ],
    )
    _patch_pdf(monkeypatch, _FakePDF(pages=[page]))

    result = cleaner.clean("ignored.pdf")

    assert result == "## Annual Report\n\nOverview details"


def test_pdf_cleaner_normalizes_unicode(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        height=600.0,
        words=[
            _word("\uFF21", top=200.0, bottom=220.0, x0=40.0, size=11.0),
            _word("中文", top=200.0, bottom=220.0, x0=90.0, size=11.0),
        ],
    )
    _patch_pdf(monkeypatch, _FakePDF(pages=[page]))

    result = cleaner.clean("ignored.pdf")

    assert result == "A 中文"
    result.encode("utf-8")
