"""Embedding and load pipeline controller."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Iterable, List, Sequence

from embedders import EmbeddingClient, EmbeddingClientError
from storages import PostgresWriter, PostgresWriterError

LOGGER = logging.getLogger(__name__)


def chunk_iterable(items: Sequence[dict], batch_size: int) -> Iterable[List[dict]]:
    """Yield batches from ``items`` of size ``batch_size``."""

    for idx in range(0, len(items), batch_size):
        yield list(items[idx : idx + batch_size])


@dataclass
class EmbeddingLoader:
    """Pipeline orchestrating embedding generation and database loading."""

    embedding_client: EmbeddingClient = field(default_factory=EmbeddingClient)
    postgres_writer: PostgresWriter = field(default_factory=PostgresWriter)
    batch_size: int = 16
    dead_letter_dir: Path = Path("data/dead_letters")

    def run(self, jsonl_path: Path) -> None:
        """Execute the embedding and load pipeline for ``jsonl_path``."""

        start_time = perf_counter()
        chunks = self._read_chunks(jsonl_path)
        if not chunks:
            LOGGER.warning("No chunks found in %s", jsonl_path)
            return

        document_id = chunks[0].get("document_id", "unknown")
        success_chunks: List[dict] = []
        failed_count = 0

        for batch in chunk_iterable(chunks, self.batch_size):
            try:
                embeddings = self.embedding_client.embed([chunk["content"] for chunk in batch])
            except EmbeddingClientError as exc:
                failed_count += len(batch)
                LOGGER.error("Embedding failed for document %s batch of size %s: %s", document_id, len(batch), exc)
                self._write_dead_letters(document_id, batch, str(exc))
                continue

            for chunk, embedding in zip(batch, embeddings):
                chunk["embedding"] = embedding
            success_chunks.extend(batch)

        if success_chunks:
            try:
                self.postgres_writer.upsert_chunks(success_chunks)
                self.postgres_writer.sanity_check(document_id, len(success_chunks))
            except PostgresWriterError as exc:
                LOGGER.exception("Database write failed for document %s: %s", document_id, exc)
                raise
        else:
            LOGGER.warning("No embeddings generated successfully for %s", document_id)

        elapsed = perf_counter() - start_time
        LOGGER.info(
            "Loader finished for %s; total=%s, success=%s, failed=%s, elapsed=%.2fs",
            document_id,
            len(chunks),
            len(success_chunks),
            failed_count,
            elapsed,
        )

    def _read_chunks(self, jsonl_path: Path) -> List[dict]:
        """Read JSONL chunks from disk."""

        with jsonl_path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _write_dead_letters(self, document_id: str, batch: List[dict], reason: str) -> None:
        """Append failed batch contents to dead letter file."""

        self.dead_letter_dir.mkdir(parents=True, exist_ok=True)
        dead_letter_path = self.dead_letter_dir / f"{document_id}.txt"
        with dead_letter_path.open("a", encoding="utf-8") as handle:
            handle.write(f"# Failure: {reason}\n")
            for chunk in batch:
                content = chunk.get("content", "")
                chunk_id = chunk.get("chunk_id", "unknown")
                handle.write(f"[{chunk_id}] {content}\n")
            handle.write("\n")
