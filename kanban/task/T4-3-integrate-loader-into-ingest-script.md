# T4-3-integrate-loader-into-ingest-script: 集成加载流程

## Goal
将 `Loader` 主流程正式集成到项目的主数据导入脚本（如 `tools/ingest.py`）中，使其成为分块（Transform-2）之后的最终处理阶段。

## Subtasks
- [ ] 修改主导入脚本 `tools/ingest.py`。
- [ ] 在脚本中，添加调用 `Loader` 流程的逻辑。
- [ ] 在分块步骤成功生成 `.jsonl` 文件后，将该文件的路径传递给 `Loader`。
- [ ] 确保主脚本能够捕获 `Loader` 流程中可能抛出的最终异常，并以合适的退出码结束。
- [ ] 更新 `README.md`，说明完整的端到端数据导入流程。

## Developer
- Owner: codex
- Complexity: L

## Acceptance Criteria
- 运行 `python tools/ingest.py --input-file ./samples/some_doc.pdf` 后，该文档的所有分块最终被向量化并存入数据库。
- 主脚本的日志能清晰地反映出清洗、分块、向量化和加载各个阶段的执行情况。

## Test Cases
- [ ] **端到端测试**：手动运行主脚本处理一个新文档，并使用 `psql` 或其他数据库客户端验证数据是否已成功写入数据库，且向量维度正确。

## Related Files / Design Docs
- `tools/ingest.py`
- `README.md`

## Dependencies
- T5-2-build-embedding-and-load-pipeline

## Notes & Updates
- 2025-10-21: 任务创建。此任务完成后，整个数据注入管道（ETL）即告完整。