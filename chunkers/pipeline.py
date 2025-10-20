"""Chunking pipeline that combines semantic and recursive splitting."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from requests import RequestException, Response

from chunkers.recursive_splitter import RecursiveTextSplitter
from chunkers.semantic_splitter import SemanticSplitter

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
    config_path: Path = Path("configs/llm_config.json")
    semantic_splitter: SemanticSplitter = field(default_factory=SemanticSplitter)
    recursive_splitter: RecursiveTextSplitter = field(init=False)
    _api_config_cache: Optional[Dict[str, Any]] = field(default=None, init=False)

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

            for segment in block_segments:
                section = base_section or self._generate_section_title(segment)
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

        config = self._load_api_config()
        if not config:
            return ""

        payload = {
            "model": config.get("model", ""),
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "为以下文本块生成一个不超过10个字的简短总结作为高质量、概括性的"
                        "section元数据，只能返回标题，不能包含其他内容：\n\n"
                        f"{chunk_content}"
                    ),
                }
            ],
            "stream": False,
            "max_tokens": 128,
            "temperature": 0.3,
            "top_p": 0.7,
            "n": 1,
            "response_format": {"type": "text"},
        }

        headers = {
            "Authorization": f"Bearer {config.get('api_key', '')}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                config.get("base_url", ""),
                json=payload,
                headers=headers,
                timeout=float(config.get("timeout", 8.0)),
            )
            response.raise_for_status()
        except (RequestException, ValueError) as exc:
            logger.warning("LLM section title generation failed: %s", exc)
            return ""

        return self._extract_content_from_response(response)

    def _extract_content_from_response(self, response: Response) -> str:
        """Parse title text from LLM response."""

        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Invalid LLM response format: %s", exc)
            return ""

        try:
            choices = data["choices"]
            if not choices:
                return ""
            message = choices[0]["message"]
            content = message.get("content", "")
            if not isinstance(content, str):
                return ""
            return content.strip()
        except (KeyError, TypeError):
            logger.warning("Missing expected fields in LLM response.")
            return ""

    def _load_api_config(self) -> Optional[Dict[str, Any]]:
        """Load the API configuration from ``config_path``."""

        if self._api_config_cache is not None:
            return self._api_config_cache

        try:
            raw = self.config_path.read_text(encoding="utf-8")
            config = json.loads(raw)
        except FileNotFoundError:
            logger.warning("LLM config file not found: %s", self.config_path)
            self._api_config_cache = None
            return None
        except json.JSONDecodeError as exc:
            logger.warning("Fail to parse LLM config: %s", exc)
            self._api_config_cache = None
            return None

        self._api_config_cache = config
        return config
