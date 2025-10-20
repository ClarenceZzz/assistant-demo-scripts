# T2-1-implement-recursive-text-splitter: 实现递归文本分割器

## Goal
创建一个通用的、可复用的文本分割器类/函数，它能够将任意长文本按照指定的 `chunk_size` 和 `overlap` 进行切分。这是处理不含明显结构的长段落或作为备用策略的核心工具。

## Subtasks
- [ ] 创建 `RecursiveTextSplitter` 类。
- [ ] 实现 `split(text, chunk_size, overlap)` 方法。
- [ ] 编写核心逻辑：使用循环或递归，从文本开头截取 `chunk_size` 长度的块，然后将下一次截取的起点回退 `overlap` 长度。
- [ ] 处理边界情况：例如当输入文本长度小于 `chunk_size` 时，应直接返回包含完整文本的单个块。
- [ ] 确保 `overlap` 参数小于 `chunk_size`，并在不满足时抛出异常或警告。
- [ ] 编写完整的单元测试，覆盖所有逻辑和边界情况。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- 输入长文本，能正确切分出多个长度符合 `chunk_size` 的块（最后一个块可能较短）。
- 切分出的相邻块之间，有长度符合 `overlap` 的重叠内容。
- 输入短文本（小于 `chunk_size`），返回包含该文本的单一列表。
- 输入空的或 `None` 的文本，返回空列表。

## Test Cases
- [ ] `pytest tests/test_splitters.py::test_recursive_splitter_long_text` -> 验证块数量、长度和重叠正确。
- [ ] `pytest tests/test_splitters.py::test_recursive_splitter_short_text` -> 验证返回单个块。
- [ ] `pytest tests/test_splitters.py::test_recursive_splitter_edge_cases` -> 验证 `overlap >= chunk_size` 等无效参数。

## Related Files / Design Docs
- `chunkers/recursive_splitter.py`
- `tests/test_splitters.py`

## Dependencies
- None

## Notes & Updates
- 2025-10-19: 任务创建，这是分块功能的基础。