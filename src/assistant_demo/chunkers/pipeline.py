"""Chunking pipeline that combines semantic and recursive splitting."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests import RequestException, Response

from assistant_demo.embedders import EmbeddingClient, EmbeddingClientError

from .recursive_splitter import RecursiveTextSplitter
from .semantic_splitter import SemanticSplitter

logger = logging.getLogger(__name__)

_HEADING_REGEX = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+)$", re.MULTILINE)


def _extract_section_heading(block: str) -> Optional[str]:
    """Return the first Markdown heading text found in ``block``."""

    for line in block.splitlines():
        match = _HEADING_REGEX.match(line.strip())
        if match:
            return match.group("title").strip()
    return None


def _strip_heading_from_block(block: str) -> str:
    """Remove the first heading line from ``block`` while keeping the rest."""

    lines = block.splitlines()
    if not lines:
        return block

    first_line = lines[0].strip()
    if _HEADING_REGEX.match(first_line):
        return "\n".join(lines[1:]).lstrip()
    return block


@dataclass
class Chunker:
    """Main chunking pipeline orchestrating semantic and recursive splitting."""

    chunk_size: int = 300
    overlap: int = 50
    config_path: Optional[Path] = None
    semantic_splitter: SemanticSplitter = field(default_factory=SemanticSplitter)
    recursive_splitter: RecursiveTextSplitter = field(init=False)
    _api_config_cache: Optional[Dict[str, Any]] = field(default=None, init=False)
    _llm_available: bool = field(default=True, init=False)
    llm_log_dir: Optional[Path] = field(default=None, init=False)
    _request_counter: int = field(default=0, init=False)
    section_client: Optional[EmbeddingClient] = field(default_factory=EmbeddingClient)

    def __post_init__(self) -> None:
        self.recursive_splitter = RecursiveTextSplitter(
            chunk_size=self.chunk_size,
            overlap=self.overlap,
        )

    def chunk(
        self,
        document_content: str,
        document_id: str,
        metadata_base: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Split ``document_content`` into chunk dictionaries."""

        if not document_content:
            return []

        semantic_blocks = self.semantic_splitter.split(document_content)
        if not semantic_blocks:
            return []

        chunks: List[Dict[str, Any]] = []
        chunk_index = 0
        title = str(metadata_base.get("title", "") or "")

        for semantic_block in semantic_blocks:
            heading = _extract_section_heading(semantic_block)
            base_section = heading or ""
            block_content = (
                _strip_heading_from_block(semantic_block)
                if heading
                else semantic_block
            )
            block_segments = self._split_if_oversized(
                original=semantic_block,
                content=block_content,
                heading=heading,
            )

            for segment_index, segment in enumerate(block_segments):
                section = ""
                if segment_index == 0 and base_section:
                    section = base_section
                else:
                    section = self._generate_section_title(segment)
                    if not section:
                        section = self._fallback_section_title(
                            segment,
                            base_section=base_section,
                            segment_index=segment_index,
                        )
                metadata = {
                    "title": title,
                    "section": section,
                    "chunk_index": chunk_index,
                }

                chunk_data = {
                    "document_id": document_id,
                    "chunk_id": f"{document_id}-{chunk_index}",
                    "content": segment.strip(),
                    "metadata": metadata,
                }
                chunks.append(chunk_data)
                chunk_index += 1

        return chunks

    def _split_if_oversized(
        self,
        original: str,
        content: str,
        heading: Optional[str],
    ) -> List[str]:
        """Split ``content`` if it exceeds ``chunk_size``."""

        if len(original) <= self.chunk_size:
            return [original.strip()]

        # For large sections keep heading in first segment.
        segments = self.recursive_splitter.split(content)
        if not segments:
            return [original.strip()]

        formatted_segments: List[str] = []
        for index, segment in enumerate(segments):
            segment_text = segment.strip()
            if not segment_text:
                continue
            if heading and index == 0:
                segment_text = f"## {heading}\n{segment_text}"
            formatted_segments.append(segment_text)
        return formatted_segments or [original.strip()]

    def _generate_section_title(self, chunk_content: str) -> str:
        """Generate a short section title using the configured LLM."""

        if self.section_client is None:
            return ""

        if self.llm_log_dir is not None:
            self.section_client.log_dir = self.llm_log_dir

        try:
            titles = self.section_client.generate_section_titles([chunk_content])
        except EmbeddingClientError as exc:
            logger.warning("LLM section title generation failed: %s", exc)
            return ""

        if not titles:
            return ""
        return titles[0].strip()

    def _fallback_section_title(
        self,
        chunk_content: str,
        *,
        base_section: str,
        segment_index: int,
    ) -> str:
        """Generate a deterministic fallback title when LLM is unavailable."""

        if segment_index == 0 and base_section:
            return base_section

        cleaned = chunk_content.strip()
        if not cleaned and base_section:
            return base_section

        first_line = cleaned.splitlines()[0] if cleaned else ""
        fallback = first_line.lstrip("# ").strip()
        if not fallback:
            fallback = base_section

        if fallback:
            return fallback[:10]
        return ""

    def _extract_content_from_response(
        self,
        response: Response,
        log_prefix: Optional[str],
        chunk_preview: str,
    ) -> str:
        """Parse title text from LLM response."""

        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Invalid LLM response format: %s", exc)
            if log_prefix and self.llm_log_dir is not None:
                error_log = self.llm_log_dir / f"{log_prefix}_response_error.json"
                error_log.write_text(
                    json.dumps(
                        {
                            "chunk_preview": chunk_preview,
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            self._llm_available = False
            return ""

        try:
            choices = data["choices"]
            if not choices:
                if log_prefix and self.llm_log_dir is not None:
                    empty_log = self.llm_log_dir / f"{log_prefix}_response_empty.json"
                    empty_log.write_text(
                        json.dumps(
                            {
                                "chunk_preview": chunk_preview,
                                "response": data,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                return ""
            message = choices[0]["message"]
            content = message.get("content", "")
            if not isinstance(content, str):
                return ""
            extracted = content.strip()
            if log_prefix and self.llm_log_dir is not None:
                response_log = self.llm_log_dir / f"{log_prefix}_response.json"
                response_log.write_text(
                    json.dumps(
                        {
                            "chunk_preview": chunk_preview,
                            "response": data,
                            "extracted_title": extracted,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            return extracted
        except (KeyError, TypeError):
            logger.warning("Missing expected fields in LLM response.")
            if log_prefix and self.llm_log_dir is not None:
                error_log = self.llm_log_dir / f"{log_prefix}_response_error.json"
                error_log.write_text(
                    json.dumps(
                        {
                            "chunk_preview": chunk_preview,
                            "error": "Missing expected fields in response.",
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            self._llm_available = False
            return ""

    def _load_api_config(self) -> Optional[Dict[str, Any]]:
        """Load the API configuration from ``config_path``."""

        if self._api_config_cache is not None:
            return self._api_config_cache

        config_raw: Optional[str] = None

        if self.config_path is not None:
            try:
                config_raw = self.config_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                logger.warning("LLM config file not found: %s", self.config_path)
                self._api_config_cache = None
                return None
        else:
            try:
                resource = resources.files("assistant_demo.configs").joinpath("llm_config.json")
                if resource.is_file():
                    config_raw = resource.read_text(encoding="utf-8")
            except (ModuleNotFoundError, FileNotFoundError):
                logger.debug("LLM config resource not available.")

        if not config_raw:
            self._api_config_cache = None
            return None

        try:
            config = json.loads(config_raw)
        except json.JSONDecodeError as exc:
            logger.warning("Fail to parse LLM config: %s", exc)
            self._api_config_cache = None
            return None

        self._api_config_cache = config
        return config

    def disable_llm(self) -> None:
        """Disable remote LLM calls forcing the splitter to use fallbacks."""

        self._llm_available = False

    def set_llm_log_dir(self, log_dir: Optional[Path]) -> None:
        """Configure directory where LLM request/response logs should be written."""

        self.llm_log_dir = log_dir
        self._request_counter = 0
        if log_dir is not None:
            log_dir.mkdir(parents=True, exist_ok=True)
