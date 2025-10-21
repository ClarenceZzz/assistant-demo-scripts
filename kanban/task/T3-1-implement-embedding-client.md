# E-1-implement-embedding-client: 实现 Embedding 客户端

## Goal
创建一个健壮、可复用的客户端，用于调用外部 Qwen/Qwen3-Embedding-8B 模型服务（测试时使用 apikey:sk-fvkljvsojrgknsnqftkpnjoxfqvjijitspsvalywcfblvhim，创建配置文件保存，调用时读取）。该客户端必须包含优雅的重试机制以应对网络或API的瞬时故障，最好能支持批量处理以提高效率。

## Subtasks
- [ ] 在项目中添加 `tenacity` (用于重试) 作为依赖。
- [ ] 创建 `EmbeddingClient` 类。
- [ ] 在构造函数中，从环境变量或配置文件中读取 `api_key` 和模型名称（如 `Qwen/Qwen3-Embedding-8B`）。
- [ ] 实现一个核心方法 `embed(texts: list[str]) -> list[list[float]]`。
- [ ] 在 `embed` 方法内部，使用 `tenacity` 的 `@retry` 装饰器来包裹 `TextEmbedding.call` API 调用，设置合理的重试策略（如：尝试3次，指数退避等待）。
- [ ] 如果你能够实现**批量调用，且确保请求响应一一对应**，则可以在`embed` 方法内批量调用 `TextEmbedding.call`，而不是在循环中单次调用。在这种情况下要注意接口是否有限流策略。
- [ ] 添加逻辑，处理API返回的错误或非200状态码，并记录详细接口日志。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- 客户端能够成功地为一批文本生成维度为1536的向量。
- 当API调用瞬时失败时，重试机制能被触发，且不会导致整个程序崩溃。
- 连续失败后，客户端会抛出异常并记录详细的错误日志。
- 实现了批量能力时，验证批量逻辑的正确性。

## Test Cases
- [ ] `pytest tests/test_embedding_client.py::test_embed_success` -> (需Mock API) 验证成功调用时返回正确结构的向量列表。
- [ ] `pytest tests/test_embedding_client.py::test_embed_with_retry` -> (需Mock API) 模拟API前两次失败、第三次成功，验证重试逻辑被正确执行。
- [ ] `pytest tests/test_embedding_client.py::test_embed_permanent_failure` -> (需Mock API) 模拟API持续失败，验证最终会抛出异常。
- [ ] `pytest tests/test_embedding_client.py::test_embed_with_retry` -> (真实调用 API) 验证成功调用时返回正确结构的向量列表。
- [ ] `pytest tests/test_embedding_client.py::test_embed_batch_with_retry` -> (真实批量调用 API) 验证成功调用时返回正确结构的向量列表。

## Related Files / Design Docs
- `embedders/qwen_client.py`
- `tests/test_embedding_client.py`
- `data/embedding-api.md`

## Dependencies
- None

## Notes & Updates
- 2025-10-21: 任务创建。这是连接本地数据和云端AI能力的关键桥梁。