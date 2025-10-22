from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest

from assistant_demo.tools.ingest import ingest_document


def read_jsonl(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_chunker_cli_generates_output(tmp_path: Path) -> None:
    cleaned_text = tmp_path / "sample.txt"
    cleaned_text.write_text(
        "## 标题\n这是第一段。\n\n这是第二段。",
        encoding="utf-8",
    )

    output_dir = tmp_path / "chunks"
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    project_src = Path.cwd() / "src"
    existing_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{project_src}{os.pathsep}{existing_path}" if existing_path else str(project_src)
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "assistant_demo.cli",
            "chunk",
            "--input-file",
            str(cleaned_text),
            "--document-id",
            "DOC001",
            "--title",
            "示例文档",
            "--output-dir",
            str(output_dir),
            "--disable-llm",
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=Path.cwd(),
        check=True,
    )

    assert result.returncode == 0
    chunks_path = output_dir / "DOC001.jsonl"
    assert chunks_path.exists()

    chunks = read_jsonl(chunks_path)
    assert chunks, "Chunker CLI should produce at least one chunk"
    assert all(chunk["document_id"] == "DOC001" for chunk in chunks)
    assert all(chunk["metadata"]["title"] == "示例文档" for chunk in chunks)


def test_e2e_ingestion_produces_chunks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_file = tmp_path / "sample.html"
    raw_file.write_text(
        "<html><body><h2>简介</h2><p>第一段内容。</p><p>第二段内容。</p></body></html>",
        encoding="utf-8",
    )

    # Avoid hitting external LLM service during tests.
    def _fake_generate(self, text: str) -> str:
        return "自动摘要"

    monkeypatch.setattr(
        "assistant_demo.chunkers.pipeline.Chunker._generate_section_title",
        _fake_generate,
    )

    clean_dir = tmp_path / "clean"
    chunks_dir = tmp_path / "chunks"

    chunks_path = ingest_document(
        raw_file,
        document_id="DOC-INTEGRATION",
        title="示例文档",
        clean_output_dir=clean_dir,
        chunks_output_dir=chunks_dir,
        use_llm=False,
    )

    assert chunks_path.exists()
    chunks = read_jsonl(chunks_path)
    assert chunks, "Ingestion pipeline should produce chunks"

    first_chunk = chunks[0]
    assert first_chunk["document_id"] == "DOC-INTEGRATION"
    assert first_chunk["metadata"]["title"] == "示例文档"
    assert first_chunk["metadata"]["chunk_index"] == 0
    assert "content" in first_chunk and first_chunk["content"]
