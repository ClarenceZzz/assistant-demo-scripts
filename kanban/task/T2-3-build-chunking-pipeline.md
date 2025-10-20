# T2-3-build-chunking-pipeline: 构建分块主流程

## Goal
构建一个 `Chunker` 主类，它编排并实现文档中描述的完整分块算法伪代码。它将整合语义分割和递归分割，，还要通过调用小型LLM为一个独立的文本块生成一个简短的、概括性的章节标题（`section`）,并负责生成符合最终输出格式的、包含元数据（包含`title`, `section`, `chunk_index`）的 `JSONL` 数据。分割时的chunk_size设置为300字符，overlap设置为50字符。

## Subtasks
- [x] 创建 `Chunker` 类，并在其构造函数中初始化 `SemanticSplitter` 和 `RecursiveTextSplitter`。
- [x] 实现主方法 `chunk(document_content, document_id, metadata_base)`。
- [x] 在 `chunk` 方法中，首先调用 `SemanticSplitter` 进行初步分割。
- [x] 遍历语义块，检查每个块的长度。如果超过 `CHUNK_SIZE`，则调用 `RecursiveTextSplitter` 对其进行二次切分。
- [x] 创建一个私有辅助方法 `_generate_section_title(chunk_content)`：
    - [x] 在该方法内，设计一个高效的Prompt，例如：“`为以下文本块生成一个不超过10个字的简短总结作为高质量、概括性的section元数据，只能返回标题，不能包含其他内容：\n\n{text}`”。
    - [x] 调用外部模型来执行生成任务，参考 `data/api.md` 内的请求和响应，测试时使用 apikey:sk-fvkljvsojrgknsnqftkpnjoxfqvjijitspsvalywcfblvhim，创建配置文件保存，调用时读取
    - [x] 实现对LLM调用的错误处理和超时机制，失败时返回一个默认值（如空字符串）。
- [x] 在主流程中，为每个最终生成的块（按其在原文中的顺序）：
    - [x] 检查其 `metadata` 中是否已有从标题行继承的 `section`。
    - [x] 如果没有，则调用 `_generate_section_title` 方法，并将返回的标题填充到 `metadata['section']` 中。
    - [x] 生成一个唯一的 `chunk_id` (格式如：`{document_id}-{index}`)。
    - [x] 将该块的顺序索引（从0开始）赋值给 `metadata['chunk_index']`。
    - [x] 将从 `metadata_base` 传入的 `title` 赋值给 `metadata['title']`。
- [x] 将每个块的内容、`chunk_id`、`document_id` 以及从 `metadata_base` 继承的元数据，组装成字典。确保其结构**严格符合** {"document_id":"string","chunk_id":"string","content":"string","metadata":{"title":"string","section":"string","chunk_index":"integer"}} 格式
- [x] `chunk` 方法最终返回一个字典列表，每个字典代表一个完整的 chunk JSON 对象。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- 输入一份长篇、结构化的文本，输出的 chunk 列表同时体现了语义分割和长度分割。
- 所有输出的 chunk 都包含正确的 `document_id`, `chunk_id` 和继承的 `metadata`。
- `chunk_id` 能够唯一、有序地标识一个文档内的所有块。
- 输出的 `JSONL` 文件的每一行都严格遵守“最终输出格式”中定义的结构和字段类型。
- `metadata.title` 字段被正确填充，`metadata.chunk_index` 从0开始连续递增。

## Test Cases
- [x] `pytest tests/test_chunker.py::test_chunking_pipeline_complex_doc` -> 验证混合分割逻辑的正确性。
- [x] `pytest tests/test_chunker.py::test_chunking_pipeline_output_format` -> 此测试用例，严格校验新的 `metadata` 结构，包括 `title` 和 `chunk_index` 的存在与正确性。
- [x] `pytest tests/test_chunker.py::test_chunking_pipeline_llm_failure_returns_empty_section` -> 验证 LLM 失败时的兜底逻辑。

## Related Files / Design Docs
- `chunkers/pipeline.py`
- `tests/test_chunker.py`

## Dependencies
- T3-1-implement-recursive-text-splitter
- T3-2-implement-semantic-splitter

## Notes & Updates
- 2025-10-20: 任务创建，这是分块阶段的核心实现。
- 2025-10-20: 任务更新。增加了使用小型LLM动态生成`section`元数据的功能。
- 2025-10-20: 任务更新。明确了最终输出的 `JSONL` 中 `metadata` 必须包含 `title`, `section`, `chunk_index`，并更新了相关子任务。
- 2025-10-20: 完成 `Chunker` 管线与 LLM 标题生成；配置存于 `configs/llm_config.json`，`PYTHONPATH=. pytest tests/test_chunker.py` 全部通过。
- 2025-10-20: 使用 `data/clean/` 文档生成 `mock/chunker/*.jsonl`，分别得到 10 个与 31 个分块，输出含完整元数据结构。
- 2025-10-20: 修复 `section` 重复问题：除首段外强制调用 LLM，若网络超时则降级为本地摘要；`PYTHONPATH=. pytest tests/test_chunker.py` 复测通过，mock 输出已刷新。更新 LLM 模型(`Qwen/Qwen3-8B`)与 15s 超时后，仍遇网络超时并触发本地兜底。
- 2025-10-20: 将 LLM 接口超时调整为 60s 再次跑 `mock/chunker`，首个无标题块仍触发 60s 超时，其后均走本地摘要；整体生成完成但耗时约 215s。
