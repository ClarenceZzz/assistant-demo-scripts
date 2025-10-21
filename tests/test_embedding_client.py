from __future__ import annotations

from typing import Any, Dict, List

import pytest

from embedders.qwen_client import EmbeddingClient, EmbeddingClientError


class DummyResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_embed_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_payloads: List[Dict[str, Any]] = []

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: float) -> DummyResponse:
        captured_payloads.append(json)
        return DummyResponse(
            200,
            {
                "data": [
                    {"embedding": [0.1, 0.2, 0.3]},
                    {"embedding": [0.4, 0.5, 0.6]},
                ]
            },
        )

    monkeypatch.setattr("requests.post", fake_post)

    client = EmbeddingClient(api_key="test-key", max_batch_size=5)
    embeddings = client.embed(["foo", "bar"])

    assert len(embeddings) == 2
    assert embeddings[0] == [0.1, 0.2, 0.3]
    assert embeddings[1] == [0.4, 0.5, 0.6]
    assert captured_payloads[0]["input"] == ["foo", "bar"]


def test_embed_with_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    def flaky_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: float) -> DummyResponse:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return DummyResponse(500, text="temporary failure")
        return DummyResponse(200, {"data": [{"embedding": [0.1, 0.1]}]})

    monkeypatch.setattr("requests.post", flaky_post)

    client = EmbeddingClient(api_key="test-key", max_batch_size=1)
    embeddings = client.embed(["hello"])

    assert attempts["count"] == 3
    assert embeddings == [[0.1, 0.1]]


def test_embed_permanent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: float) -> DummyResponse:
        raise RuntimeError("network down")

    monkeypatch.setattr("requests.post", failing_post)

    client = EmbeddingClient(api_key="test-key", max_batch_size=2)

    with pytest.raises(EmbeddingClientError):
        client.embed(["a", "b"])
