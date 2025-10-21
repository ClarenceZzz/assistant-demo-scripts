from __future__ import annotations

from typing import Any, Dict, List

import pytest

from chunkers.pipeline import Chunker
from embedders import EmbeddingClientError


def test_chunking_pipeline_complex_doc(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: List[List[str]] = []

    def fake_generate(self, texts: List[str]) -> List[str]:
        calls.append(texts)
        return ["自动摘要" for _ in texts]

    monkeypatch.setattr(
        "chunkers.pipeline.EmbeddingClient.generate_section_titles", fake_generate
    )

    chunker = Chunker(chunk_size=120, overlap=20)
    document_content = (
        "## 引言\n"
        "这是一段简介内容，用于说明文档背景。\n"
        "## 深度解析\n"
        + "详细内容。" * 50  # force recursive splitting
    )
    result = chunker.chunk(
        document_content=document_content,
        document_id="DOC001",
        metadata_base={"title": "示例文档"},
    )

    assert len(result) >= 2
    assert result[0]["metadata"]["section"] == "引言"
    assert all(chunk["metadata"]["title"] == "示例文档" for chunk in result)
    assert [chunk["metadata"]["chunk_index"] for chunk in result] == list(
        range(len(result))
    )
    assert [
        chunk["chunk_id"] for chunk in result
    ] == [f"DOC001-{idx}" for idx in range(len(result))]
    assert calls  # recursive splits should trigger LLM for overflow segments
    assert any(
        chunk["metadata"]["section"] == "深度解析" for chunk in result
    ), "First segment of heading should retain original title"
    assert any(
        chunk["metadata"]["section"] == "自动摘要" for chunk in result
    ), "Overflow segments should receive generated titles"


def test_chunking_pipeline_output_format(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_texts: List[List[str]] = []

    def fake_generate(self, texts: List[str]) -> List[str]:
        captured_texts.append(texts)
        return ["自动生成标题" for _ in texts]

    monkeypatch.setattr(
        "chunkers.pipeline.EmbeddingClient.generate_section_titles", fake_generate
    )

    chunker = Chunker(chunk_size=200, overlap=30)
    content = "这是没有标题的段落，需要生成节选标题。"
    result = chunker.chunk(
        document_content=content,
        document_id="DOC-LLM",
        metadata_base={"title": "无标题文档"},
    )

    assert len(result) == 1
    chunk = result[0]
    assert chunk.keys() == {"document_id", "chunk_id", "content", "metadata"}
    assert chunk["metadata"] == {
        "title": "无标题文档",
        "section": "自动生成标题",
        "chunk_index": 0,
    }
    assert captured_texts and captured_texts[0][0] == content


def test_chunking_pipeline_llm_failure_returns_empty_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_generate(self, texts: List[str]) -> List[str]:
        raise EmbeddingClientError("network error")

    monkeypatch.setattr(
        "chunkers.pipeline.EmbeddingClient.generate_section_titles", fake_generate
    )

    chunker = Chunker(chunk_size=200, overlap=30)
    content = "另一个无标题段落。"
    result = chunker.chunk(
        document_content=content,
        document_id="DOC-ERR",
        metadata_base={"title": "异常测试"},
    )

    assert result[0]["metadata"]["section"] == "另一个无标题段落。"
