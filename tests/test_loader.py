from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from embedders.qwen_client import EmbeddingClientError
from loaders.main_loader import EmbeddingLoader


class DummyEmbeddingClient:
    def __init__(self, results: List[List[float]] | None = None, fail_once: bool = False) -> None:
        self.results = results or []
        self.fail_once = fail_once
        self.calls: List[List[str]] = []

    def embed(self, texts: List[str]) -> List[List[float]]:
        self.calls.append(texts)
        if self.fail_once:
            self.fail_once = False
            raise EmbeddingClientError("embedding error")
        return self.results.pop(0)


class DummyPostgresWriter:
    def __init__(self) -> None:
        self.upsert_args = None
        self.sanity_args = None

    def upsert_chunks(self, chunks: List[dict]) -> None:
        self.upsert_args = chunks

    def sanity_check(self, document_id: str, expected_chunk_count: int) -> None:
        self.sanity_args = (document_id, expected_chunk_count)


def _write_jsonl(path: Path, chunks: List[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def test_loader_pipeline_happy_path(tmp_path: Path) -> None:
    chunks = [
        {"chunk_id": "doc-0", "document_id": "doc", "content": "文本1", "metadata": {}},
        {"chunk_id": "doc-1", "document_id": "doc", "content": "文本2", "metadata": {}},
    ]
    jsonl_path = tmp_path / "doc.jsonl"
    _write_jsonl(jsonl_path, chunks)

    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    embedding_client = DummyEmbeddingClient(results=[embeddings])
    writer = DummyPostgresWriter()
    loader = EmbeddingLoader(embedding_client=embedding_client, postgres_writer=writer, batch_size=4, dead_letter_dir=tmp_path / "dead")

    loader.run(jsonl_path)

    assert writer.upsert_args is not None
    assert all("embedding" in chunk for chunk in writer.upsert_args)
    assert writer.sanity_args == ("doc", len(chunks))
    dead_letter_files = list((tmp_path / "dead").glob("*") )
    assert not dead_letter_files


def test_loader_handles_embedding_failures(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "doc2.jsonl"
    chunks = [
        {"chunk_id": "doc2-0", "document_id": "doc2", "content": "fail", "metadata": {}},
        {"chunk_id": "doc2-1", "document_id": "doc2", "content": "success", "metadata": {}},
        {"chunk_id": "doc2-2", "document_id": "doc2", "content": "success2", "metadata": {}},
    ]
    _write_jsonl(jsonl_path, chunks)

    embedding_client = DummyEmbeddingClient(results=[[[0.5, 0.6]], [[0.7, 0.8]]], fail_once=True)
    writer = DummyPostgresWriter()
    loader = EmbeddingLoader(embedding_client=embedding_client, postgres_writer=writer, batch_size=1, dead_letter_dir=tmp_path / "dead")

    loader.run(jsonl_path)

    dead_file = tmp_path / "dead" / "doc2.txt"
    assert dead_file.exists()
    content = dead_file.read_text(encoding="utf-8")
    assert "fail" in content
    assert writer.upsert_args is not None
    assert len(writer.upsert_args) == 2
    assert writer.sanity_args == ("doc2", 2)
