# T4-2-build-embedding-and-load-pipeline: 构建向量化与加载主流程

## Goal
创建一个主流程控制器，它负责读取分块后的 `JSONL` 文件，使用 `EmbeddingClient` 为每个块生成向量，然后调用 `PostgresWriter` 将结果写入数据库，并处理整个过程中的失败情况。

## Subtasks
- [ ] 创建一个 `Loader` 类或一个独立的脚本 `run_loader.py`。
- [ ] 在主流程中，实例化 `EmbeddingClient` 和 `PostgresWriter`。
- [ ] 实现逻辑以读取指定的 `.jsonl` 文件。
- [ ] 按合适的批次大小（如 16 或 32）将 chunks 分批。
- [ ] 对每一批 chunks：
    - [ ] 调用 `embedding_client.embed()` 生成向量。
    - [ ] 将返回的向量填充回对应的 chunk 字典中。
    - [ ] 如果 `embed` 失败，将这批失败的 chunks 的 `content` 写入一个“死信文件”（e.g., `data/dead_letters/{document_id}.txt`），并记录错误日志，然后继续处理下一批。
- [ ] 将所有成功生成向量的 chunks 传递给 `postgres_writer.upsert_chunks()`。
- [ ] 在 `upsert` 成功后，调用 `postgres_writer.sanity_check()` 进行最终验证。
- [ ] 记录详细的日志，包括总处理数、成功数、失败数、耗时等。

## Developer
- Owner: `[待分配]`
- Complexity: M

## Acceptance Criteria
- 能够完整地处理一个 `.jsonl` 文件，将其内容向量化并存入数据库。
- 当部分批次的 Embedding 请求失败时，流程不会中断，失败的文本会被记录，成功的批次仍能被处理和写入。
- 流程结束后，会自动执行健全性检查。

## Test Cases
- [ ] `pytest tests/test_loader.py::test_loader_pipeline_happy_path` -> (需Mock依赖) 验证从文件读取到写入数据库的完整流程。
- [ ] `pytest tests/test_loader.py::test_loader_handles_embedding_failures` -> (需Mock依赖) 模拟 Embedding 失败，验证死信文件被创建，且流程继续。

## Related Files / Design Docs
- `loaders/main_loader.py`
- `tests/test_loader.py`

## Dependencies
- T2-5-integrate-chunker-into-ingest-script.md
- T3-1-implement-embedding-client
- T4-1-implement-db-writer

## Notes & Updates
- 2025-10-21: 任务创建。这是串联T4和T5阶段的核心任务。