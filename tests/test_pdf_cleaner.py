"""Tests covering PdfCleaner core behaviours."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

import pytest

from cleaners.pdf import PdfCleaner


@dataclass
class _FakePage:
    """Lightweight pdfplumber page stand-in for unit tests."""

    width: float
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
    x1: float | None = None,
    size: float,
    fontname: str = "Helvetica",
) -> Dict[str, object]:
    if x1 is None:
        x1 = x0 + max(size, 1.0)
    return {
        "text": text,
        "top": top,
        "bottom": bottom,
        "x0": x0,
        "x1": x1,
        "size": size,
        "fontname": fontname,
    }


def _patch_pdf(monkeypatch: pytest.MonkeyPatch, fake_pdf: _FakePDF) -> None:
    monkeypatch.setattr("cleaners.pdf.pdfplumber.open", lambda _path: fake_pdf)


def test_pdf_cleaner_filters_header_and_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        width=600.0,
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
        width=600.0,
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

    assert result == "## Annual Report\nOverview details"


def test_pdf_cleaner_normalizes_unicode(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        width=500.0,
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


def test_pdf_cleaner_handles_multicolumn_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        width=800.0,
        height=600.0,
        words=[
            _word("安装说明", top=80.0, bottom=92.0, x0=80.0, x1=160.0, size=14.0, fontname="Helvetica-Bold"),
            _word(
                "步骤一、接通电源，将按摩椅座架下方的电源开关按至“I”的位置，按",
                top=100.0,
                bottom=108.0,
                x0=80.0,
                x1=320.0,
                size=10.0,
            ),
            _word("摩椅自动调节到复位状态。", top=115.0, bottom=123.0, x0=80.0, x1=220.0, size=10.0),
            _word("产品移动说明", top=80.0, bottom=92.0, x0=420.0, x1=520.0, size=14.0, fontname="Helvetica-Bold"),
            _word("拖起小腿垫，将椅背倾斜约45度。", top=100.0, bottom=108.0, x0=420.0, x1=640.0, size=10.0),
            _word("注意:", top=115.0, bottom=123.0, x0=420.0, x1=460.0, size=10.0),
        ],
    )
    _patch_pdf(monkeypatch, _FakePDF(pages=[page]))

    result = cleaner.clean("ignored.pdf")

    expected = (
        "## 安装说明\n"
        "步骤一、接通电源,将按摩椅座架下方的电源开关按至“I”的位置,按 摩椅自动调节到复位状态。\n\n"
        "## 产品移动说明\n"
        "拖起小腿垫,将椅背倾斜约45度。\n"
        "注意:"
    )
    assert result == expected


def test_pdf_cleaner_merges_sentence_fragments(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        width=500.0,
        height=600.0,
        words=[
            _word("请确保电源线完好", top=200.0, bottom=208.0, x0=100.0, x1=220.0, size=10.0),
            _word("否则可能导致故障。", top=214.0, bottom=222.0, x0=100.0, x1=220.0, size=10.0),
        ],
    )
    _patch_pdf(monkeypatch, _FakePDF(pages=[page]))

    result = cleaner.clean("ignored.pdf")

    assert result == "请确保电源线完好 否则可能导致故障。"


def test_pdf_cleaner_filters_numeric_noise(monkeypatch: pytest.MonkeyPatch) -> None:
    cleaner = PdfCleaner()
    page = _FakePage(
        width=500.0,
        height=600.0,
        words=[
            _word("1 2 3", top=200.0, bottom=208.0, x0=50.0, x1=120.0, size=10.0),
            _word("A", top=220.0, bottom=228.0, x0=50.0, x1=60.0, size=10.0),
            _word("正常文本", top=240.0, bottom=248.0, x0=50.0, x1=110.0, size=10.0),
        ],
    )
    _patch_pdf(monkeypatch, _FakePDF(pages=[page]))

    result = cleaner.clean("ignored.pdf")

    assert result == "正常文本"
