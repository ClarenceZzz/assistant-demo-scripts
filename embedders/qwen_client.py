"""Embedding client for Qwen embedding service."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from requests import RequestException
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
    log_dir: Optional[Path] = None
    _request_counter: int = field(default=0, init=False)
    section_base_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    section_model: str = "Qwen/Qwen3-14B"
    section_batch_size: int = 4
    _section_request_counter: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise EmbeddingClientError("API key must not be empty.")
        if self.max_batch_size <= 0:
            raise ValueError("max_batch_size must be positive.")

    def embed(self, texts: Iterable[str]) -> List[List[float]]:
        """Return embeddings for the provided texts."""

        batches = self._chunk_texts(list(texts), self.max_batch_size)
        self._request_counter = 0
        embeddings: List[List[float]] = []
        for batch in batches:
            embeddings.extend(self._embed_batch(batch))
        return embeddings

    def generate_section_titles(self, texts: Iterable[str]) -> List[str]:
        """Generate short section titles for ``texts`` using chat completions."""

        text_list = list(texts)
        if not text_list:
            return []

        results: List[str] = []
        self._section_request_counter = 0
        for batch in self._chunk_texts(text_list, self.section_batch_size):
            batch_results: List[str] = []
            for text in batch:
                try:
                    batch_results.append(self._call_section_api(text))
                except RetryError as exc:
                    raise EmbeddingClientError("Section title generation failed after retries") from exc
            results.extend(batch_results)
        return results

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

        sequence_id = self._request_counter
        prefix = None
        if self.log_dir is not None:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            prefix = f"{sequence_id:04d}"
            request_path = self.log_dir / f"{prefix}_request.json"
            request_path.write_text(
                json.dumps({"payload": payload}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.request_timeout,
            )
        except RequestException as exc:
            if prefix and self.log_dir is not None:
                error_path = self.log_dir / f"{prefix}_network_error.json"
                error_path.write_text(
                    json.dumps(
                        {
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            self._request_counter += 1
            raise

        self._request_counter += 1

        if response.status_code != 200:
            LOGGER.warning(
                "Embedding API responded with %s: %s",
                response.status_code,
                response.text,
            )
            if prefix and self.log_dir is not None:
                error_path = self.log_dir / f"{prefix}_status_error.json"
                error_path.write_text(
                    json.dumps(
                        {
                            "status_code": response.status_code,
                            "text": response.text,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            raise EmbeddingClientError(
                f"Embedding API error: {response.status_code} {response.text}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            LOGGER.error("Unable to decode embedding response: %s", response.text)
            if prefix and self.log_dir is not None:
                error_path = self.log_dir / f"{prefix}_response_error.json"
                error_path.write_text(
                    json.dumps(
                        {
                            "text": response.text,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            raise EmbeddingClientError("Invalid JSON response from embedding API") from exc

        embeddings = self._parse_embeddings(data)
        if len(embeddings) != len(batch):
            raise EmbeddingClientError(
                f"Embedding count mismatch: expected {len(batch)}, got {len(embeddings)}"
            )

        if prefix and self.log_dir is not None:
            response_path = self.log_dir / f"{prefix}_response.json"
            response_path.write_text(
                json.dumps(
                    {
                        "response": data,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _call_section_api(self, text: str) -> str:
        """Call chat completion API to generate a section title."""

        payload = {
            "model": self.section_model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "为以下文本块生成一个不超过10个字的简短总结作为高质量、概括性的section元数据，只能返回标题，不能包含其他内容："
                        f"{text}"
                    ),
                }
            ],
            "stream": False,
            "max_tokens": 128,
            "enable_thinking": True,
            "thinking_budget": 512,
            "min_p": 0.05,
            "stop": None,
            "temperature": 0.3,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "response_format": {"type": "text"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        sequence_id = self._section_request_counter
        prefix = None
        if self.log_dir is not None:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            prefix = f"section_{sequence_id:04d}"
            request_path = self.log_dir / f"{prefix}_request.json"
            request_path.write_text(
                json.dumps({"payload": payload}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        try:
            response = requests.post(
                self.section_base_url,
                headers=headers,
                json=payload,
                timeout=self.request_timeout,
            )
        except RequestException as exc:
            if prefix and self.log_dir is not None:
                error_path = self.log_dir / f"{prefix}_network_error.json"
                error_path.write_text(
                    json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            self._section_request_counter += 1
            raise

        self._section_request_counter += 1

        if response.status_code != 200:
            if prefix and self.log_dir is not None:
                error_path = self.log_dir / f"{prefix}_status_error.json"
                error_path.write_text(
                    json.dumps(
                        {
                            "status_code": response.status_code,
                            "text": response.text,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            raise EmbeddingClientError(
                f"Section API error: {response.status_code} {response.text}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            if prefix and self.log_dir is not None:
                error_path = self.log_dir / f"{prefix}_response_error.json"
                error_path.write_text(
                    json.dumps(
                        {
                            "text": response.text,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            raise EmbeddingClientError("Invalid section response JSON") from exc

        title = self._parse_section_title(data)

        if prefix and self.log_dir is not None:
            response_path = self.log_dir / f"{prefix}_response.json"
            response_path.write_text(
                json.dumps({"response": data}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return title

    @staticmethod
    def _parse_section_title(payload: dict) -> str:
        try:
            choices = payload["choices"]
            message = choices[0]["message"]
            content = message.get("content", "")
        except (KeyError, IndexError, TypeError) as exc:
            raise EmbeddingClientError("Unexpected section response structure.") from exc

        title = content.strip()
        return title

    def set_log_dir(self, directory: Optional[Path]) -> None:
        """Configure directory where request/response logs will be stored."""

        self.log_dir = directory
        self._request_counter = 0
