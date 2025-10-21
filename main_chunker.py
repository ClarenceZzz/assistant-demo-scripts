"""CLI entry point for chunking cleaned documents into JSONL outputs."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List

from chunkers.pipeline import Chunker

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure application wide logging."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Chunk a cleaned text document into JSONL format."
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to the cleaned text file that should be chunked.",
    )
    parser.add_argument(
        "--document-id",
        help="Optional document identifier. Defaults to the input file stem.",
    )
    parser.add_argument(
        "--title",
        help="Optional document title. Defaults to the document identifier.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/chunks",
        help="Directory where the chunked JSONL file should be stored.",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable remote LLM calls when generating section titles.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    """Read UTF-8 text from ``path``."""

    return path.read_text(encoding="utf-8")


def write_chunks(chunks: List[Dict[str, object]], output_path: Path) -> None:
    """Persist chunk dictionaries to a JSONL file."""

    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False))
            handle.write("\n")


def chunk_file(
    input_path: Path,
    document_id: str,
    title: str,
    output_dir: Path,
    disable_llm: bool = False,
) -> Path:
    """Chunk ``input_path`` and persist the JSONL output in ``output_dir``."""

    if not input_path.exists():
        msg = f"Input file not found: {input_path}"
        raise FileNotFoundError(msg)

    text = read_text(input_path)
    chunker = Chunker()
    if disable_llm:
        chunker.disable_llm()

    metadata_base = {"title": title}
    chunks = chunker.chunk(text, document_id=document_id, metadata_base=metadata_base)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{document_id}.jsonl"
    write_chunks(chunks, output_path)
    LOGGER.info(
        "Generated %s chunks for document %s at %s",
        len(chunks),
        document_id,
        output_path,
    )
    return output_path


def main() -> None:
    """CLI entry point."""

    configure_logging()
    args = parse_args()
    input_path = Path(args.input_file)
    document_id = args.document_id or input_path.stem
    title = args.title or document_id
    output_dir = Path(args.output_dir)

    try:
        chunk_file(
            input_path=input_path,
            document_id=document_id,
            title=title,
            output_dir=output_dir,
            disable_llm=args.disable_llm,
        )
    except FileNotFoundError:
        LOGGER.exception("Input file does not exist: %s", input_path)
        raise SystemExit(1) from None
    except Exception:  # noqa: BLE001
        LOGGER.exception("Unexpected error while chunking file: %s", input_path)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
