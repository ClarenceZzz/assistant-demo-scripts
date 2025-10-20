# T1-3-2-improve-html-cleaner-markdown: 修复 HTML 清洗 Markdown 结构与分块友好度

## Goal
针对 `T1-3-implement-html-cleaner` 交付后发现的两个问题：其一，输出文本虽带 `#`/`-` 符号但整体未满足 Markdown 规范（标题、列表、表格缺少必要空行、缩进或对齐导致渲染失败）；其二，文本段落与结构被压缩到单行，导致后续向量化分块难以保持语义完整。此任务旨在修复 Markdown 结构并提升分块友好度。

## Subtasks
- [x] 对比处理前、处理后的样例 HTML（含列表、表格、段落）确认格式缺陷，总结 Markdown 渲染失败与分块不佳的具体场景。
- [x] 调整 `HtmlCleaner` 的段落/标题/列表/表格输出规则：补充必要空行、缩进、管道对齐以及行内换行，确保常见 Markdown 渲染器可正确解析。
- [x] 优化段落与列表的拼接逻辑，避免将多句内容压缩为单行，恢复分块友好的段落边界。
- [x] 扩充单元测试：校验 Markdown 结构（例如通过 `markdown` 或 `mistune` 解析无报错），并验证长段文本在清洗后仍保持语义段落划分。
- [x] 在 `data/clean` 中使用样例 HTML 回归，确保输出既符合 Markdown 规范，也便于后续分块（示例：`tests/test_html_cleaner.py::test_html_cleaner_preserves_line_breaks_and_paragraphs` 验证段落与列表继续行）。
- [x] 更新文档/注释，说明 Markdown 格式约定与分块友好策略。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- 经过 `HtmlCleaner` 处理的 HTML 样例可被 Markdown 解析器无错渲染：标题层级正确、列表项缩进对齐、表格分隔行规范。
- 输出文本保留自然段落和列表结构，供分块逻辑按段落/列表切分，不再出现整页单行或语句断裂的情况。
- 新增/更新的单元测试全部通过，覆盖 Markdown 渲染验证与分块友好性检测。
- 运行 `python3 main_cleaner.py --input-file samples/...` 生成的清洗结果符合以上标准，并在任务记录中附示例说明。

## Test Cases
- [x] `python3 -m pytest tests/test_html_cleaner.py::test_html_cleaner_outputs_markdown_shape` -> 验证 Markdown 结构可被解析。
- [x] `python3 -m pytest tests/test_html_cleaner.py::test_html_cleaner_preserves_line_breaks_and_paragraphs` -> 验证段落/列表输出保留分块边界。
- [ ] `python3 main_cleaner.py --input-file ./samples/news_article.html` -> 检查正文输出无导航噪声，Markdown 渲染正常。
- [ ] `python3 main_cleaner.py --input-file ./samples/tutorial_with_lists_tables.html` -> 检查列表、表格格式符合 Markdown 规范，且段落可直接进入分块。

## Related Files / Design Docs
- `./kanban/task/T1-3-implement-html-cleaner.md`

## Dependencies
- T1-3-implement-html-cleaner

## Notes & Updates
- 2025-10-20: 任务创建，确认 T1-3 输出 Markdown 结构不合规、分块语义缺失，需进一步迭代。
- 2025-10-20: 完成 Markdown 行为修复与测试扩展，新增 `tests/test_html_cleaner.py` 覆盖行内换行、段落边界与表格格式；待真实样例 HTML 收集后补充 CLI 回归记录。
