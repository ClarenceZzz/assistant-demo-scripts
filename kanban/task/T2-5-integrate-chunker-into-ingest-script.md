# T2-5-integrate-chunker-into-ingest-script: 集成 Chunking 流程

## Goal
将已完成的 `Chunker` 管道正式集成到项目的主数据导入脚本中，使其成为清洗（Transform-1）之后的下一个处理阶段。

## Subtasks
- [x] 创建一个类似 `main_cleaner.py` 的脚本，能够使用命令行参数分块（如 `--input-file`）。
- [x] 创建主导入脚本，能够使用命令行参数（如 `--input-file`）。
- [x] 在主导入脚本，集成已经实现的清洗（`Cleaner`）功能
- [x] 在主导入脚本，集成分块（`Chunker`）功能。
    - [x] 在文本清洗步骤完成后，读取清洗后的文本文件内容。
    - [x] 从文档的元数据源（例如，一个单独的 `meta.json` 文件，或从文件名解析）中提取 `title` 等文档级信息，构建 `metadata_base` 字典。
    - [x] 调用 `chunker.chunk()` 方法，传入文本内容、`document_id` 和相关元数据。
    - [x] 将返回的 chunk 列表（JSON 对象列表）逐行写入到 `data/chunks/{document_id}.jsonl` 文件中。
    - [x] 添加相应的日志记录，输出成功生成的 chunk 数量。
- [x] 更新主脚本的命令行帮助文档和 `README.md`，说明新的输出产物。

## Developer
- Owner: codex
- Complexity: L

## Acceptance Criteria
- 运行主导入脚本命令行参数（如 `--input-file data/raw/some_doc.pdf`）后，能够在 `data/chunks/` 目录下找到对应的 `some_doc.jsonl` 文件。
- 生成的 `.jsonl` 文件内容格式正确，且与预期一致。
- 整个流程从头到尾（原始文件 -> 清洗 -> 分块）能够顺利跑通。
- 运行主脚本时，能够正确地将文档的 `title` 传递给 `Chunker`，并最终体现在输出的 `.jsonl` 文件中。

## Test Cases
- [x] 运行主脚本，并检查最终生成的 `.jsonl` 文件是否符合预期。
- [x] `pytest tests/test_integration.py::test_e2e_ingestion_produces_chunks` -> 编写一个集成测试，模拟运行主脚本并验证产出文件。

## Related Files / Design Docs
- `tools/ingest.py`
- `README.md`

## Dependencies
- T2-3-build-chunking-pipeline

## Notes & Updates
- 2025-10-20: 任务创建，这是分块阶段的最后一步，标志着该阶段功能交付。
- 2025-10-20: 新增 `main_chunker.py` 与 `tools/ingest.py`，支持 `--disable-llm` 与可配置输出目录；`python -m tools.ingest --input-file ...` 生成 `data/chunks/*.jsonl`。`PYTHONPATH=. pytest tests/test_integration.py` 通过。
- 2025-10-21: 增强日志输出，在清洗、分块、写入阶段都有 Info 级提示；在 `mock/ingest_run/` 目录重新验证 `data/raw/产品测评_OG-8598Plus_20251020.html` 流程，生成 10 个分块 JSON。
- 2025-10-21: 同目录验证 `data/raw/产品说明书_OG-5308_20251020.pdf`，最终产出 61 个分块；打印 `chunking document ...` 日志帮助排查执行耗时。
