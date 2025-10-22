"""统一的命令行入口，提供清洗、分块与整合管线命令。"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, Optional

from assistant_demo.chunkers.pipeline import Chunker
from assistant_demo.tools.ingest import (
    DEFAULT_CHUNKS_DIR,
    DEFAULT_CLEAN_DIR,
    DEFAULT_DEAD_LETTER_DIR,
    clean_document,
    ingest_document,
    write_chunks,
)

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    """配置统一的日志格式。"""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _add_clean_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "clean",
        help="对输入文件执行清洗并输出 Markdown 文本。",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="需要清洗的原始文件路径。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_CLEAN_DIR),
        help="清洗后的文本输出目录，默认 data/clean。",
    )
    parser.set_defaults(handler=_handle_clean_command)


def _add_chunk_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "chunk",
        help="将清洗后的 Markdown 文本切分为 JSONL 块。",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="需要切分的已清洗文本。",
    )
    parser.add_argument(
        "--document-id",
        help="文档 ID，默认取输入文件名（不含扩展名）。",
    )
    parser.add_argument(
        "--title",
        help="文档标题，默认与文档 ID 一致。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_CHUNKS_DIR),
        help="JSONL 输出目录，默认 data/chunks。",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="禁用 LLM 标题生成，全部使用回退逻辑。",
    )
    parser.add_argument(
        "--llm-log-dir",
        help="若指定，则保存 LLM 请求/响应日志。",
    )
    parser.set_defaults(handler=_handle_chunk_command)


def _add_ingest_subcommand(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "ingest",
        help="执行清洗、分块、嵌入与入库的整合流程。",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="需要处理的原始文件路径。",
    )
    parser.add_argument(
        "--document-id",
        help="文档 ID，默认取文件名（不含扩展名）。",
    )
    parser.add_argument(
        "--title",
        help="文档标题，默认与文档 ID 一致。",
    )
    parser.add_argument(
        "--meta-file",
        help="包含额外元数据（例如标题）的 JSON 文件。",
    )
    parser.add_argument(
        "--clean-output-dir",
        default=str(DEFAULT_CLEAN_DIR),
        help="清洗结果输出目录。",
    )
    parser.add_argument(
        "--chunks-output-dir",
        default=str(DEFAULT_CHUNKS_DIR),
        help="分块结果输出目录。",
    )
    parser.add_argument(
        "--disable-llm",
        action="store_true",
        help="禁用分块阶段的 LLM 标题生成。",
    )
    parser.add_argument(
        "--llm-log-dir",
        help="LLM 调用日志输出目录。",
    )
    parser.add_argument(
        "--loader-dead-letter-dir",
        default=str(DEFAULT_DEAD_LETTER_DIR),
        help="嵌入/入库失败批次的死信目录。",
    )
    parser.add_argument(
        "--loader-batch-size",
        type=int,
        default=16,
        help="嵌入时的批大小。",
    )
    parser.set_defaults(handler=_handle_ingest_command)


def _handle_clean_command(args: argparse.Namespace) -> int:
    input_path = Path(args.input_file)
    output_dir = Path(args.output_dir)

    try:
        clean_path, _ = clean_document(input_path, output_dir)
    except FileNotFoundError:
        LOGGER.exception("输入文件不存在: %s", input_path)
        return 1
    except ValueError:
        LOGGER.exception("未找到匹配的 Cleaner 处理文件: %s", input_path)
        return 2
    except Exception:  # noqa: BLE001
        LOGGER.exception("清洗过程中出现未知错误: %s", input_path)
        return 3

    LOGGER.info("清洗结果写入 %s", clean_path)
    return 0


def _handle_chunk_command(args: argparse.Namespace) -> int:
    input_path = Path(args.input_file)
    output_dir = Path(args.output_dir)
    document_id = args.document_id or input_path.stem
    title = args.title or document_id
    llm_log_dir = Path(args.llm_log_dir) if args.llm_log_dir else None

    if not input_path.exists():
        LOGGER.error("输入文件不存在: %s", input_path)
        return 1

    try:
        text = input_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        LOGGER.exception("读取输入文件失败: %s", input_path)
        return 2

    chunker = Chunker()
    if args.disable_llm:
        chunker.disable_llm()
    if llm_log_dir is not None:
        chunker.set_llm_log_dir(llm_log_dir)

    try:
        chunks = chunker.chunk(
            text,
            document_id=document_id,
            metadata_base={"title": title},
        )
    except Exception:  # noqa: BLE001
        LOGGER.exception("分块过程中发生错误: %s", input_path)
        return 3

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{document_id}.jsonl"
    write_chunks(chunks, output_path)
    LOGGER.info("生成 %s 个 chunk -> %s", len(chunks), output_path)
    return 0


def _handle_ingest_command(args: argparse.Namespace) -> int:
    input_file = Path(args.input_file)
    llm_log_dir = Path(args.llm_log_dir) if args.llm_log_dir else None
    clean_output_dir = Path(args.clean_output_dir)
    chunks_output_dir = Path(args.chunks_output_dir)
    meta_file = Path(args.meta_file) if args.meta_file else None
    dead_letter_dir = Path(args.loader_dead_letter_dir)

    try:
        ingest_document(
            input_file,
            document_id=args.document_id,
            title=args.title,
            meta_file=meta_file,
            clean_output_dir=clean_output_dir,
            chunks_output_dir=chunks_output_dir,
            use_llm=not args.disable_llm,
            llm_log_dir=llm_log_dir,
            loader_dead_letter_dir=dead_letter_dir,
            loader_batch_size=args.loader_batch_size,
        )
    except FileNotFoundError:
        LOGGER.exception("输入文件或元数据文件不存在。")
        return 1
    except ValueError:
        LOGGER.exception("输入文件的清洗或元数据解析失败。")
        return 2
    except Exception:  # noqa: BLE001
        LOGGER.exception("整合管线执行失败。")
        return 3

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="assistant-demo 项目的统一命令行工具。",
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_clean_subcommand(subparsers)
    _add_chunk_subcommand(subparsers)
    _add_ingest_subcommand(subparsers)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(None if argv is None else list(argv))

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
