"""Main ingestion pipeline combining cleaning and chunking steps."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from chunkers.pipeline import Chunker
from cleaners import BaseCleaner, HTMLCleaner, MarkdownCleaner, PdfCleaner

LOGGER = logging.getLogger(__name__)

DEFAULT_CLEAN_DIR = Path("data/clean")
DEFAULT_CHUNKS_DIR = Path("data/chunks")


def configure_logging() -> None:
    """Configure application wide logging."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def build_cleaner_registry() -> Dict[str, type[BaseCleaner]]:
    """Return the mapping between file extensions and cleaner classes."""

    return {
        ".pdf": PdfCleaner,
        ".html": HTMLCleaner,
        ".htm": HTMLCleaner,
        ".md": MarkdownCleaner,
        ".markdown": MarkdownCleaner,
    }


def resolve_cleaner(path: Path) -> BaseCleaner:
    """Instantiate a cleaner able to process ``path``."""

    registry = build_cleaner_registry()
    cleaner_cls = registry.get(path.suffix.lower())
    if cleaner_cls is None:
        msg = f"Unsupported file extension: {path.suffix or '<none>'}"
        raise ValueError(msg)
    return cleaner_cls()


def clean_document(input_path: Path, output_dir: Path) -> Tuple[Path, str]:
    """Clean ``input_path`` and persist the cleaned text within ``output_dir``."""

    if not input_path.exists():
        msg = f"File not found: {input_path}"
        raise FileNotFoundError(msg)

    cleaner = resolve_cleaner(input_path)
    cleaned_text = cleaner.clean(str(input_path))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}.txt"
    output_path.write_text(cleaned_text, encoding="utf-8")
    LOGGER.info("Cleaned document %s -> %s", input_path, output_path)
    return output_path, cleaned_text


def load_metadata(
    document_id: str,
    *,
    title: Optional[str] = None,
    meta_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Load metadata for ``document_id`` prioritising explicit overrides."""

    meta_title = title
    if meta_title is None and meta_path is not None:
        if not meta_path.exists():
            msg = f"Metadata file not found: {meta_path}"
            raise FileNotFoundError(msg)
        meta_raw = meta_path.read_text(encoding="utf-8")
        try:
            payload = json.loads(meta_raw)
        except json.JSONDecodeError as exc:
            msg = f"Unable to parse metadata JSON: {meta_path}"
            raise ValueError(msg) from exc
        meta_title = payload.get("title")

    final_title = meta_title or document_id
    return {"title": str(final_title)}


def write_chunks(chunks: list[dict[str, Any]], output_path: Path) -> None:
    """Persist chunk dictionaries to ``output_path`` in JSONL format."""

    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False))
            handle.write("\n")


def ingest_document(
    input_file: Path,
    *,
    document_id: Optional[str] = None,
    title: Optional[str] = None,
    meta_file: Optional[Path] = None,
    clean_output_dir: Path = DEFAULT_CLEAN_DIR,
    chunks_output_dir: Path = DEFAULT_CHUNKS_DIR,
    use_llm: bool = True,
) -> Path:
    """Execute the ingestion pipeline returning the chunks JSONL path."""

    doc_id = document_id or input_file.stem
    LOGGER.info("Starting ingestion for %s (document_id=%s)", input_file, doc_id)

    clean_path, cleaned_text = clean_document(input_file, clean_output_dir)
    metadata = load_metadata(doc_id, title=title, meta_path=meta_file)

    chunker = Chunker()
    if not use_llm:
        chunker.disable_llm()

    LOGGER.info(
        "Chunking document %s using LLM=%s (clean text length=%s)",
        doc_id,
        "enabled" if use_llm else "disabled",
        len(cleaned_text),
    )
    chunks = chunker.chunk(cleaned_text, document_id=doc_id, metadata_base=metadata)

    chunks_output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = chunks_output_dir / f"{doc_id}.jsonl"
    write_chunks(chunks, chunks_path)

    LOGGER.info(
        "Ingestion finished for %s -> %s (clean: %s, chunk_count=%s)",
        input_file,
        chunks_path,
        clean_path,
        len(chunks),
    )
    return chunks_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the ingestion script."""

    parser = argparse.ArgumentParser(
        description="Run the ingestion pipeline (clean + chunk)."
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to the input document to ingest.",
    )
    parser.add_argument(
        "--document-id",
        help="Optional document identifier. Defaults to the input file stem.",
    )
    parser.add_argument(
        "--title",
        help="Optional document title override.",
    )
    parser.add_argument(
        "--meta-file",
        help="Optional JSON file providing metadata (expects a 'title' field).",
    )
    parser.add_argument(
        "--clean-output-dir",
        default=str(DEFAULT_CLEAN_DIR),
        help="Directory where cleaned text files should be written.",
    )
    parser.add_argument(
        "--chunks-output-dir",
        default=str(DEFAULT_CHUNKS_DIR),
        help="Directory where chunked JSONL files should be written.",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="Disable remote LLM calls when generating section titles.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    configure_logging()
    args = parse_args()

    input_path = Path(args.input_file)
    document_id = args.document_id or None
    title = args.title or None
    meta_file = Path(args.meta_file) if args.meta_file else None
    clean_dir = Path(args.clean_output_dir)
    chunks_dir = Path(args.chunks_output_dir)

    try:
        ingest_document(
            input_path,
            document_id=document_id,
            title=title,
            meta_file=meta_file,
            clean_output_dir=clean_dir,
            chunks_output_dir=chunks_dir,
            use_llm=not args.disable_llm,
        )
    except FileNotFoundError:
        LOGGER.exception("Input or metadata file not found.")
        raise SystemExit(1) from None
    except ValueError:
        LOGGER.exception("Invalid input or metadata content.")
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001
        LOGGER.exception("Unexpected error during ingestion.")
        raise SystemExit(3) from None


if __name__ == "__main__":
    main()
