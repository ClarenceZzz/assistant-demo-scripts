# T2-5-integrate-chunker-into-ingest-script: 集成 Chunking 流程

## Goal
将已完成的 `Chunker` 管道正式集成到项目的主数据导入脚本（如 `tools/ingest.py`）中，使其成为清洗（Transform-1）之后的下一个处理阶段。

## Subtasks
- [ ] 修改主导入脚本 `tools/ingest.py`。
- [ ] 在脚本中，实例化 `Chunker` 类。
- [ ] 在文本清洗步骤完成后，读取清洗后的文本文件内容。
- [ ] 从文档的元数据源（例如，一个单独的 `meta.json` 文件，或从文件名解析）中提取 `title` 等文档级信息，构建 `metadata_base` 字典。
- [ ] 调用 `chunker.chunk()` 方法，传入文本内容、`document_id` 和相关元数据。
- [ ] 将返回的 chunk 列表（JSON 对象列表）逐行写入到 `data/chunks/{document_id}.jsonl` 文件中。
- [ ] 添加相应的日志记录，输出成功生成的 chunk 数量。
- [ ] 更新主脚本的命令行帮助文档和 `README.md`，说明新的输出产物。

## Developer
- Owner: `[待分配]`
- Complexity: L

## Acceptance Criteria
- 运行 `python tools/ingest.py --input-file ./samples/some_doc.pdf` 后，能够在 `data/chunks/` 目录下找到对应的 `some_doc.jsonl` 文件。
- 生成的 `.jsonl` 文件内容格式正确，且与预期一致。
- 整个流程从头到尾（原始文件 -> 清洗 -> 分块）能够顺利跑通。
- **[新增]** 运行主脚本时，能够正确地将文档的 `title` 传递给 `Chunker`，并最终体现在输出的 `.jsonl` 文件中。

## Test Cases
- [ ] **端到端测试**：手动运行主脚本，并检查最终生成的 `.jsonl` 文件是否符合预期。
- [ ] `pytest tests/test_integration.py::test_e2e_ingestion_produces_chunks` -> 编写一个集成测试，模拟运行主脚本并验证产出文件。

## Related Files / Design Docs
- `tools/ingest.py`
- `README.md`

## Dependencies
- T3-3-build-chunking-pipeline

## Notes & Updates
- 2025-10-20: 任务创建，这是分块阶段的最后一步，标志着该阶段功能交付。