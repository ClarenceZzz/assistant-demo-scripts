"""Embedding client for Qwen embedding service."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

import requests
try:
    from tenacity import (
        RetryError,
        retry,
        stop_after_attempt,
        wait_exponential,
    )
except ImportError:  # pragma: no cover - fallback when tenacity unavailable
    class RetryError(Exception):
        """Fallback retry error raised when retries are exhausted."""

        def __init__(self, last_exception: Exception | None = None) -> None:
            super().__init__("Retry attempts exhausted")
            self.last_exception = last_exception

    class _StopAfterAttempt:
        def __init__(self, attempts: int) -> None:
            self.attempts = max(1, attempts)

    class _WaitExponential:
        def __init__(self, **kwargs: int | float) -> None:
            self.kwargs = kwargs

    def stop_after_attempt(attempts: int) -> _StopAfterAttempt:
        return _StopAfterAttempt(attempts)

    def wait_exponential(**kwargs: int | float) -> _WaitExponential:
        return _WaitExponential(**kwargs)

    def retry(*retry_args, **retry_kwargs):
        stop = retry_kwargs.get("stop", _StopAfterAttempt(3))
        attempts = getattr(stop, "attempts", 3)

        def decorator(func):
            def wrapper(*args, **kwargs):
                last_exc: Exception | None = None
                for attempt in range(attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as exc:  # noqa: BLE001 - mirror tenacity behaviour
                        last_exc = exc
                        if attempt == attempts - 1:
                            raise RetryError(last_exc) from exc
                raise RetryError(last_exc)

            return wrapper

        return decorator

LOGGER = logging.getLogger(__name__)


class EmbeddingClientError(RuntimeError):
    """Raised when the embedding client cannot fulfil a request."""


def _load_api_key(config_path: Optional[Path]) -> str:
    """Load API key from environment variables or configuration file."""

    api_key = os.environ.get("EMBEDDING_API_KEY")
    if api_key:
        return api_key

    if config_path is not None and config_path.exists():
        raw = config_path.read_text(encoding="utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise EmbeddingClientError(f"Invalid JSON in {config_path}") from exc
        key = payload.get("api_key")
        if isinstance(key, str) and key:
            return key

    raise EmbeddingClientError(
        "Embedding API key not found. Set EMBEDDING_API_KEY or provide config file."
    )


@dataclass
class EmbeddingClient:
    """Client responsible for calling the Qwen embedding API."""

    base_url: str = "https://api.siliconflow.cn/v1/embeddings"
    model: str = "Qwen/Qwen3-Embedding-8B"
    api_key: str = field(default_factory=lambda: _load_api_key(Path("configs/embedding.json")))
    request_timeout: float = 60.0
    max_batch_size: int = 8
    log_payloads: bool = False

    def __post_init__(self) -> None:
        if not self.api_key:
            raise EmbeddingClientError("API key must not be empty.")
        if self.max_batch_size <= 0:
            raise ValueError("max_batch_size must be positive.")

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        """Return embeddings for the provided texts."""

        batches = self._chunk_texts(list(texts), self.max_batch_size)
        embeddings: List[List[float]] = []
        for batch in batches:
            embeddings.extend(self._embed_batch(batch))
        return embeddings

    def _chunk_texts(self, texts: List[str], size: int) -> List[List[str]]:
        """Split ``texts`` into batches of ``size``."""

        return [texts[i : i + size] for i in range(0, len(texts), size)]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=False,
    )
    def _call_api(self, batch: List[str]) -> List[List[float]]:
        """Call the embedding API and return the embeddings."""

        payload = {
            "model": self.model,
            "input": batch,
            "encoding_format": "float",
            "dimensions": 1536,
        }
        if self.log_payloads:
            LOGGER.debug("Embedding request payload: %s", payload)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=self.request_timeout,
        )
        if response.status_code != 200:
            LOGGER.warning(
                "Embedding API responded with %s: %s",
                response.status_code,
                response.text,
            )
            raise EmbeddingClientError(
                f"Embedding API error: {response.status_code} {response.text}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            LOGGER.error("Unable to decode embedding response: %s", response.text)
            raise EmbeddingClientError("Invalid JSON response from embedding API") from exc

        embeddings = self._parse_embeddings(data)
        if len(embeddings) != len(batch):
            raise EmbeddingClientError(
                f"Embedding count mismatch: expected {len(batch)}, got {len(embeddings)}"
            )

        return embeddings

    def _embed_batch(self, batch: List[str]) -> List[List[float]]:
        """Wrapper handling retry exceptions."""

        try:
            return self._call_api(batch)
        except RetryError as exc:
            raise EmbeddingClientError("Embedding API call failed after retries") from exc

    @staticmethod
    def _parse_embeddings(payload: dict) -> List[List[float]]:
        """Extract embeddings from API response payload."""

        data = payload.get("data", [])
        if not isinstance(data, list):
            raise EmbeddingClientError("Unexpected embedding payload structure.")

        embeddings: List[List[float]] = []
        for item in data:
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise EmbeddingClientError("Embedding vector missing in response item.")
            embeddings.append([float(value) for value in embedding])
        return embeddings
