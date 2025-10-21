from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

import psycopg2
import pytest

from storages.postgres_writer import PostgresWriter, PostgresWriterError

TEST_TABLE = "rag_chunks_test"
VECTOR_DIM = 4
DSN = "postgresql://postgres:zAzHHplnxXb7QvT02QMl0oPV@localhost:5432/postgres"


def _ensure_schema() -> None:
    with psycopg2.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(f"DROP TABLE IF EXISTS {TEST_TABLE}")
            cur.execute(
                f"""
                CREATE TABLE {TEST_TABLE} (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({VECTOR_DIM}) NOT NULL,
                    metadata JSONB NOT NULL
                )
                """
            )
        conn.commit()


def _fetch_all(document_id: str) -> List[tuple]:
    with psycopg2.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT chunk_id, document_id, content, embedding::text, metadata::text FROM {TEST_TABLE} WHERE document_id = %s ORDER BY chunk_id",
                (document_id,),
            )
            return cur.fetchall()


def _make_chunks(doc_id: str, count: int) -> Iterable[dict]:
    base_embedding = [0.1, 0.2, 0.3, 0.4]
    for idx in range(count):
        yield {
            "chunk_id": f"{doc_id}-{idx}",
            "document_id": doc_id,
            "content": f"content-{idx}",
            "embedding": [value + idx * 0.01 for value in base_embedding],
            "metadata": {"index": idx},
        }


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> None:
    _ensure_schema()


@pytest.fixture
def writer(monkeypatch: pytest.MonkeyPatch) -> PostgresWriter:
    monkeypatch.setenv("POSTGRES_DSN", DSN)
    monkeypatch.setenv("POSTGRES_TABLE", TEST_TABLE)
    monkeypatch.setenv("POSTGRES_VECTOR_DIMENSION", str(VECTOR_DIM))
    return PostgresWriter()


def test_upsert_chunks_success(writer: PostgresWriter) -> None:
    chunks = list(_make_chunks("doc-success", 3))
    writer.upsert_chunks(chunks)

    rows = _fetch_all("doc-success")
    assert len(rows) == 3
    for (chunk_id, document_id, content, embedding_text, metadata_text), original in zip(rows, chunks):
        assert document_id == "doc-success"
        assert content == original["content"]
        metadata = json.loads(metadata_text)
        assert metadata["index"] == original["metadata"]["index"]
        assert embedding_text.startswith("[") and embedding_text.endswith("]")


def test_upsert_transaction_rollback(writer: PostgresWriter) -> None:
    doc_id = "doc-rollback"
    writer.upsert_chunks(list(_make_chunks(doc_id, 2)))

    bad_chunks = list(_make_chunks(doc_id, 2))
    bad_chunks[1]["embedding"] = [0.1, 0.2]  # wrong dimension

    with pytest.raises(PostgresWriterError):
        writer.upsert_chunks(bad_chunks)

    rows = _fetch_all(doc_id)
    assert len(rows) == 2


def test_sanity_check(writer: PostgresWriter) -> None:
    doc_id = "doc-sanity"
    writer.upsert_chunks(list(_make_chunks(doc_id, 2)))
    writer.sanity_check(doc_id, expected_chunk_count=2)
