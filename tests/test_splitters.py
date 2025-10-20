"""Tests for the recursive and semantic text splitters."""

from __future__ import annotations

import pytest

from chunkers.recursive_splitter import RecursiveTextSplitter
from chunkers.semantic_splitter import SemanticSplitter


def test_recursive_splitter_long_text() -> None:
    splitter = RecursiveTextSplitter(chunk_size=10, overlap=2)
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = splitter.split(text)

    assert len(chunks) == 3
    assert chunks[0] == "abcdefghij"
    assert chunks[1].startswith("ijklmnop")
    assert chunks[2].endswith("uvwxyz")

    for i in range(len(chunks) - 1):
        overlap = chunks[i][-2:]
        assert chunks[i + 1].startswith(overlap)


def test_recursive_splitter_short_text() -> None:
    splitter = RecursiveTextSplitter(chunk_size=10, overlap=1)
    text = "short"
    assert splitter.split(text) == [text]


def test_recursive_splitter_edge_cases() -> None:
    with pytest.raises(ValueError):
        RecursiveTextSplitter(chunk_size=0, overlap=0)

    with pytest.raises(ValueError):
        RecursiveTextSplitter(chunk_size=5, overlap=5)

    splitter = RecursiveTextSplitter(chunk_size=5, overlap=1)
    assert splitter.split("") == []
    assert splitter.split(None) == []


def test_semantic_splitter_multiple_headings() -> None:
    splitter = SemanticSplitter()
    text = """## Introduction
This is the introduction section.

## Details
Here are more details about the topic.

## Conclusion
Summary of the discussion."""

    chunks = splitter.split(text)

    assert len(chunks) == 3
    assert chunks[0].startswith("## Introduction")
    assert "This is the introduction section." in chunks[0]
    assert chunks[1].startswith("## Details")
    assert "Here are more details" in chunks[1]
    assert chunks[2].startswith("## Conclusion")
    assert "Summary of the discussion." in chunks[2]


def test_semantic_splitter_no_headings() -> None:
    splitter = SemanticSplitter()
    text = "Plain paragraph without any Markdown headings."

    chunks = splitter.split(text)

    assert chunks == [text]
