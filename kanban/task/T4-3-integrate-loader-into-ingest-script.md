# T4-3-integrate-loader-into-ingest-script: 集成加载流程

## Goal
将 `Loader` 主流程正式集成到项目的主数据导入脚本（如 `tools/ingest.py`）中，使其成为分块（Transform-2）之后的最终处理阶段。涉及到的表已经建好，建表语句：
  ```sql
  CREATE TABLE rag_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT,
    content TEXT,
    embedding VECTOR(1536),
    metadata JSONB,
    last_modified TIMESTAMP DEFAULT now()
  );
  CREATE INDEX idx_rag_chunks_metadata ON rag_chunks USING GIN (metadata jsonb_path_ops);
  CREATE INDEX idx_rag_chunks_document ON rag_chunks(document_id);
  CREATE INDEX idx_rag_chunks_embedding_hnsw ON rag_chunks USING hnsw (embedding vector_cosine_ops);
  ```

## Subtasks
- [x] 修改主导入脚本 `tools/ingest.py`。
- [x] 在脚本中，添加调用 `Loader` 流程的逻辑。
- [x] 在分块步骤成功生成 `.jsonl` 文件后，将该文件的路径传递给 `Loader`。
- [x] 确保主脚本能够捕获 `Loader` 流程中可能抛出的最终异常，并以合适的退出码结束。
- [x] 更新 `README.md`，说明完整的端到端数据导入流程。

## Developer
- Owner: codex
- Complexity: L

## Acceptance Criteria
- 运行主脚本后，该文档的所有分块最终被向量化并存入数据库。
- 主脚本的日志能清晰地反映出清洗、分块、向量化和加载各个阶段的执行情况。

## Test Cases
- [x] 运行主脚本处理 `data/raw` 下的文档，并验证数据是否已成功写入数据库，且向量维度正确。

## Related Files / Design Docs
- `tools/ingest.py`
- `README.md`

## Dependencies
- T5-2-build-embedding-and-load-pipeline

## Notes & Updates
- 2025-10-21: 任务创建。此任务完成后，整个数据注入管道（ETL）即告完整。
- 2025-10-21: `tools/ingest.py` 集成 `EmbeddingLoader`，新增 `--dead-letter-dir`、`--loader-batch-size` 参数；`README.md` 更新完整流程；`python3 -m tools.ingest --input-file data/raw/产品测评_OG-8598Plus_20251020.html` 成功执行，`rag_chunks` 表写入 10 条向量。
