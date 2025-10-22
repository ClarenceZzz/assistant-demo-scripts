"""PostgreSQL writer for chunk persistence."""

from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json

LOGGER = logging.getLogger(__name__)


class PostgresWriterError(RuntimeError):
    """Raised when the writer fails to complete an operation."""


def _load_dsn(config_path: Optional[Path]) -> Dict[str, object]:
    """Load database configuration."""

    dsn = os.environ.get("POSTGRES_DSN")
    table = os.environ.get("POSTGRES_TABLE")
    vector_dim = os.environ.get("POSTGRES_VECTOR_DIMENSION")

    payload: Dict[str, object] = {}
    raw_config: Optional[str] = None

    if config_path and config_path.exists():
        raw_config = config_path.read_text(encoding="utf-8")
    else:
        try:
            resource = resources.files("assistant_demo.configs").joinpath("postgres.json")
            if resource.is_file():
                raw_config = resource.read_text(encoding="utf-8")
        except (ModuleNotFoundError, FileNotFoundError):
            LOGGER.debug("Postgres config resource not found.")

    if raw_config:
        payload = json.loads(raw_config)
        dsn = dsn or payload.get("dsn")
        table = table or payload.get("table")
        vector_dim = vector_dim or payload.get("vector_dimension")

    if not dsn:
        raise PostgresWriterError("Postgres DSN not configured.")
    if not table:
        raise PostgresWriterError("Target table not configured.")

    try:
        vector_dim_int = int(vector_dim) if vector_dim is not None else 1536
    except (TypeError, ValueError) as exc:
        raise PostgresWriterError("Vector dimension must be an integer.") from exc

    return {
        "dsn": dsn,
        "table": table,
        "vector_dim": vector_dim_int,
    }


@dataclass
class PostgresWriter:
    """Writer handling transactional upsert into a pgvector table."""

    config_path: Optional[Path] = None
    dsn: str = field(init=False)
    table: str = field(init=False)
    vector_dimension: int = field(init=False)

    def __post_init__(self) -> None:
        config = _load_dsn(self.config_path)
        self.dsn = config["dsn"]
        self.table = config["table"]
        self.vector_dimension = config["vector_dim"]

    @contextmanager
    def get_conn(self) -> Iterator[PgConnection]:
        """Context manager yielding a PostgreSQL connection with transaction."""

        conn = psycopg2.connect(self.dsn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            LOGGER.exception("Transaction rolled back due to error.")
            raise
        finally:
            conn.close()

    def upsert_chunks(self, chunks: Iterable[Dict[str, object]]) -> None:
        """Delete previous chunks and insert provided ones atomically."""

        chunk_list = list(chunks)
        if not chunk_list:
            raise PostgresWriterError("No chunks provided for upsert.")

        document_id = chunk_list[0].get("document_id")
        if not document_id:
            raise PostgresWriterError("Chunks must include document_id.")

        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DELETE FROM {table} WHERE document_id = %s").format(
                        table=sql.Identifier(self.table)
                    ),
                    (document_id,),
                )

                insert_stmt = sql.SQL(
                    """
                    INSERT INTO {table}
                        (chunk_id, document_id, content, embedding, metadata)
                    VALUES
                        (%s, %s, %s, %s::vector, %s::jsonb)
                    """
                ).format(table=sql.Identifier(self.table))

                for chunk in chunk_list:
                    if chunk.get("document_id") != document_id:
                        raise PostgresWriterError("All chunks must share the same document_id.")
                    embedding = chunk.get("embedding")
                    if not isinstance(embedding, list):
                        raise PostgresWriterError("Chunk embedding must be a list of floats.")
                    if len(embedding) != self.vector_dimension:
                        raise PostgresWriterError(
                            f"Embedding dimension mismatch: expected {self.vector_dimension}, got {len(embedding)}"
                        )

                    embedding_str = self._format_vector(embedding)
                    metadata = chunk.get("metadata", {})
                    cur.execute(
                        insert_stmt,
                        (
                            chunk.get("chunk_id"),
                            chunk.get("document_id"),
                            chunk.get("content"),
                            embedding_str,
                            Json(metadata),
                        ),
                    )

    def sanity_check(self, document_id: str, expected_chunk_count: int) -> None:
        """Validate stored chunks for a given document."""

        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT COUNT(*) FROM {table} WHERE document_id = %s").format(
                        table=sql.Identifier(self.table)
                    ),
                    (document_id,),
                )
                (count,) = cur.fetchone()
                if count != expected_chunk_count:
                    raise PostgresWriterError(
                        f"Chunk count mismatch: expected {expected_chunk_count}, got {count}"
                    )

                cur.execute(
                    sql.SQL(
                        """
                        SELECT chunk_id, embedding::text, content, metadata::text
                        FROM {table}
                        WHERE document_id = %s
                        ORDER BY random()
                        LIMIT 3
                        """
                    ).format(table=sql.Identifier(self.table)),
                    (document_id,),
                )
                rows = cur.fetchall()
                for chunk_id, embedding_text, content, metadata_text in rows:
                    vector = self._parse_vector(embedding_text)
                    if len(vector) != self.vector_dimension:
                        raise PostgresWriterError(
                            f"Embedding dimension mismatch for chunk {chunk_id}: {len(vector)}"
                        )
                    if not content:
                        raise PostgresWriterError(f"Chunk {chunk_id} has empty content.")
                    try:
                        json.loads(metadata_text or "{}")
                    except json.JSONDecodeError as exc:
                        raise PostgresWriterError(
                            f"Invalid metadata JSON for chunk {chunk_id}."
                        ) from exc

    def _format_vector(self, embedding: List[float]) -> str:
        """Convert embedding list to pgvector textual representation."""

        return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"

    def _parse_vector(self, embedding_text: str) -> List[float]:
        """Parse pgvector textual representation back to floats."""

        embedding_text = embedding_text.strip()[1:-1]
        if not embedding_text:
            return []
        return [float(value) for value in embedding_text.split(",")]
