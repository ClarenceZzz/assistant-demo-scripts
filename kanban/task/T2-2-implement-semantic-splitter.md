# T2-2-implement-semantic-splitter: 实现语义分割器

## Goal
创建一个基于文档结构（特别是 Markdown 标题）的分割器。它能将一份清洗后的文本，按照 `#`、`##` 等标记分割成多个有意义的章节或段落，为后续精细化分块做准备。

## Subtasks
- [x] 创建 `SemanticSplitter` 类或函数。
- [x] 实现 `split(text)` 方法，使用正则表达式 `(^## .*)` 或类似逻辑来识别标题行。
- [x] 编写逻辑，将文本按标题分割成多个部分，每个部分包含其标题和后续内容。
- [x] 确保分割后，标题本身被保留在对应块的开头。
- [x] 编写单元测试，验证其能正确处理包含多个标题、无标题、或只有标题的文本。

## Developer
- Owner: codex
- Complexity: L

## Acceptance Criteria
- 输入一份包含多个 `#`、`## `等标题的 Markdown 格式文本，能被准确地分割成与标题数量对应的块数。
- 每个分割出的块都以其对应的 `## ` 标题开头。
- 输入不含标题的文本，返回包含完整文本的单个块。

## Test Cases
- [x] `pytest tests/test_splitters.py::test_semantic_splitter_multiple_headings` -> 验证正确分割。
- [x] `pytest tests/test_splitters.py::test_semantic_splitter_no_headings` -> 验证返回单个块。

## Related Files / Design Docs
- None

## Dependencies
- None

## Notes & Updates
- 2025-10-20: 任务创建，用于实现结构化优先的切分策略。
- 2025-10-20: 实现 `SemanticSplitter` 并完成单元测试覆盖；`PYTHONPATH=. pytest tests/test_splitters.py` 通过。
- 2025-10-20: 基于 `data/clean/` 文档生成 `mock/semantic_splitter/` 测试前后数据；`产品测评_OG-8598Plus_20251020.txt` 分割出 1 段，`产品说明书_OG-5308_20251020.txt` 分割出 20 段。
