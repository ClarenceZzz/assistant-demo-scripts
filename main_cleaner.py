"""Entry point for the document cleaning pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Type

from cleaners import BaseCleaner, HTMLCleaner, MarkdownCleaner, PdfCleaner

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure application wide logging."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def build_dispatch_table() -> Dict[str, Type[BaseCleaner]]:
    """Return the mapping between file extensions and cleaner classes."""

    return {
        ".pdf": PdfCleaner,
        ".html": HTMLCleaner,
        ".htm": HTMLCleaner,
        ".md": MarkdownCleaner,
        ".markdown": MarkdownCleaner,
    }


def resolve_cleaner(file_path: Path) -> BaseCleaner:
    """Instantiate the cleaner that should process the provided path."""

    dispatch_table = build_dispatch_table()
    extension = file_path.suffix.lower()
    cleaner_cls = dispatch_table.get(extension)
    if cleaner_cls is None:
        msg = f"Unsupported file extension: {extension or '<none>'}"
        raise ValueError(msg)
    return cleaner_cls()


def write_output(document_id: str, content: str) -> Path:
    """Persist the cleaned content inside the data/clean directory."""

    output_dir = Path("data/clean")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{document_id}.txt"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def clean_file(file_path: Path) -> Path:
    """Execute the cleaning workflow for the provided file path."""

    LOGGER.info("Processing file %s", file_path)
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)
    cleaner = resolve_cleaner(file_path)
    cleaned_content = cleaner.clean(str(file_path))
    output_path = write_output(file_path.stem, cleaned_content)
    LOGGER.info("Successfully cleaned file %s", file_path)
    return output_path


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description="Clean documents into plain text.")
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to the input document that should be cleaned.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point."""

    configure_logging()
    args = parse_args()
    input_path = Path(args.input_file)
    try:
        output_path = clean_file(input_path)
        LOGGER.info("Output written to %s", output_path)
    except FileNotFoundError:
        LOGGER.exception("Input file does not exist: %s", input_path)
        raise SystemExit(1) from None
    except ValueError:
        LOGGER.exception("No cleaner configured for file: %s", input_path)
        raise SystemExit(2) from None
    except Exception:  # noqa: BLE001
        LOGGER.exception("Unexpected error while cleaning file: %s", input_path)
        raise SystemExit(3) from None


if __name__ == "__main__":
    main()
