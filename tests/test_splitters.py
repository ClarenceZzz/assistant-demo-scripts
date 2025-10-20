"""Tests for the recursive text splitter."""

from __future__ import annotations

import pytest

from chunkers.recursive_splitter import RecursiveTextSplitter


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
