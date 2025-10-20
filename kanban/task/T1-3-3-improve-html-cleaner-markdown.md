# T1-3-2-improve-html-cleaner-markdown: 修复 HTML 清洗 Markdown 结构与分块友好度（阶段 2）

## Goal
上一轮 `T1-3-2` 修复后，经对实际业务 HTML (`/data/raw/产品测评_OG-8598Plus_20251020.html`) 验收发现：
1. 顶部标题与小节未被识别，输出缺少 Markdown `#` 标记，仅为纯文本；
2. 长段内容仍被压缩为单段，缺乏自然段间隔，列表/引用等结构不稳定；
3. 真实文件输出缺少导航、脚本等噪声处理后的 Markdown 结构，不便于后续向量化分块。

本阶段目标：以真实 HTML 文件为基准，彻底修复 Markdown 结构（含标题、段落、列表、表格、引用），并确保输出内容可直接用于分块和解析。

## Subtasks
- [x] 以 `/data/raw/产品测评_OG-8598Plus_20251020.html` 为例，抽取主要结构（标题、段落、列表、图片/表格等），归纳现有输出缺陷与预期 Markdown 形态。
- [x] 调整 `HtmlCleaner`：确保 `<h1>-<h6>`、`<p>`、`<section>`、`<article>` 等映射到正确的 Markdown 标记，并在段落之间插入适度空行；确保 `<br>` 生成软换行时保留 Markdown 语义。
- [x] 强化列表/嵌套列表输出：首行采用 `-`/`1.`，续行使用两个空格缩进；引用、代码块、表格等结构需以 Markdown 标准输出。
- [x] 针对真实文件新增单元测试或快照校验，验证标题提取、段落拆分与列表输出；必要时引入 Markdown 渲染库（如 `markdown` 或 `mistune`）做解析验证。
- [x] 运行 `python3 main_cleaner.py --input-file data/raw/产品测评_OG-8598Plus_20251020.html`，检视 `data/clean` 输出内容，确保符合 Markdown 与分块要求，并在任务备注中附样例片段。
- [x] 更新文档/注释，总结 Markdown 输出规则与分块友好策略，便于后续维护。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- `/data/raw/产品测评_OG-8598Plus_20251020.html` 清洗后输出包含正确的 Markdown 标题（`#`/`##` 等）、段落空行、列表缩进与表格格式。
- 使用 Markdown 解析器解析输出无报错；随机段落解析后仍保留语义结构，可作为分块输入（可验证段落数与原文结构对齐）。
- `python3 -m pytest tests/test_html_cleaner.py` 通过新增/更新的测试；若引入解析库，需在测试中验证结构正确性。
- 任务备注附上关键片段示例（例如首屏标题、段落与列表），证明 Markdown 与分块友好度满足 `T1-3` 目标。

## Test Cases
- [x] `python3 -m pytest tests/test_html_cleaner.py::test_html_cleaner_outputs_markdown_shape` -> 验证标题、表格结构未回退。
- [x] `python3 -m pytest tests/test_html_cleaner.py::test_html_cleaner_preserves_line_breaks_and_paragraphs` -> 验证段落、列表换行逻辑。
- [x] `python3 -m pytest tests/test_html_cleaner.py::test_html_cleaner_cleans_real_product_article` -> 针对 `/data/raw/产品测评_OG-8598Plus_20251020.html` 样例验证 Markdown 结构。
- [x] `python3 main_cleaner.py --input-file data/raw/产品测评_OG-8598Plus_20251020.html` -> 检查实际输出，确认 Markdown 和分块需求达成。

## Related Files / Design Docs
- `./kanban/task/T1-3-implement-html-cleaner.md`

## Dependencies
- T1-3-implement-html-cleaner

## Notes & Updates
- 2025-10-20: 任务重新排期。实际业务 HTML 输出仍为纯文本段落，缺少 Markdown 标记与段落边界，对分块造成影响。需围绕真实文件完成修复、测试与回归。
- 2025-10-20: 已重构 `HtmlCleaner`，引入标题提取（支持 `<title>` 拆分）、Markdown 链接格式及换行保留；新增 `tests/test_html_cleaner.py::test_html_cleaner_cleans_real_product_article` 覆盖真实 HTML。运行 `python3 -m pytest tests/test_html_cleaner.py tests/test_pdf_cleaner.py` 与 `python3 main_cleaner.py --input-file data/raw/产品测评_OG-8598Plus_20251020.html` 全部通过，输出首行示例：
  ```
  # 奥佳华 OG-8598Plus 按摩椅怎么样?看完体验测评再选,不踩坑
  
  奥佳华 OG-8598Plus 按摩椅怎么样?看完体验测评再选,不踩坑
  ```
