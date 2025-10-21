# T4-1-implement-db-writer: 实现数据库写入器

## Goal
创建一个专门负责与 PgVector 数据库交互的模块（测试时使用用户名：postgres，密码：zAzHHplnxXb7QvT02QMl0oPV，创建配置文件保存，调用时读取）。它必须提供一个事务性的 `upsert_chunks` 方法，以确保对单个文档的知识更新是原子操作（要么全部成功，要么全部回滚）。

## Subtasks
- [ ] 在项目中添加 `psycopg2-binary` 作为依赖。
- [ ] 创建 `PostgresWriter` 类。
- [ ] 在构造函数中，从环境变量或配置文件中读取数据库连接字符串 (DSN)。
- [ ] 实现 `get_conn` 上下文管理器，用于处理数据库连接和事务。
- [ ] 实现 `upsert_chunks(chunks: list[dict])` 方法。
- [ ] 在 `upsert_chunks` 方法中，严格按照“先 `DELETE` 同一 `document_id` 的所有旧数据，再 `INSERT` 所有新数据”的逻辑执行。
- [ ] 确保所有数据库操作都在 `get_conn` 的事务块中进行。
- [ ] 实现一个 `sanity_check(document_id: str, expected_chunk_count: int)` 方法。该方法会连接数据库，随机抽查几条记录，验证 `embedding` 维度、`content` 和 `metadata` 的正确性，并比对总数是否与预期一致。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- `upsert_chunks` 方法能够成功将一批带有向量的 chunk 数据写入数据库。
- 如果在 `INSERT` 过程中发生错误，`DELETE` 操作会被回滚，数据库中的旧数据不会丢失。
- 对同一个 `document_id` 多次调用 `upsert_chunks`，数据库中只保留最后一次写入的数据。
- `sanity_check` 方法能够发现数据写入中的常见问题（如维度错误、JSON格式错误）。

## Test Cases
- [ ] `pytest tests/test_db_writer.py::test_upsert_chunks_success` -> (需连接测试数据库) 验证数据被正确写入。
- [ ] `pytest tests/test_db_writer.py::test_upsert_transaction_rollback` -> (需连接测试数据库) 模拟 `INSERT` 中途失败，验证 `DELETE` 被回滚。
- [ ] `pytest tests/test_db_writer.py::test_sanity_check` -> (需连接测试数据库) 验证健全性检查能正常工作。

## Related Files / Design Docs
- `storages/postgres_writer.py`
- `tests/test_db_writer.py`

## Dependencies
- None

## Notes & Updates
- 2025-10-21: 任务创建。这是数据持久化的最后一步，事务性保证至关重要。