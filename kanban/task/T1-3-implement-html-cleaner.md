# T1-3-implement-html-cleaner: 实现 HTML 文件清洗器

## Goal
基于基础框架，实现对 HTML 格式文档的文本清洗功能，去除脚本、样式等噪声，并将有用的结构化信息转换为 Markdown 格式，先预留图片处理逻辑为todo，等待后续拓展。

## Subtasks
- [x] 在项目中添加 `beautifulsoup4` 作为依赖。
- [x] 创建 `HtmlCleaner` 类，继承自 `BaseCleaner`。
- [x] 实现 `clean` 方法，使用 `BeautifulSoup` 解析 HTML 内容。
- [x] 编写逻辑，移除 `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>` 等无关标签。
- [x] 转换 `<h1>-<h6>` 标签为 Markdown 标题格式。
- [x] 转换 `<ul>`, `<ol>`, `<li>` 标签为 Markdown 列表格式。
- [x] （可选，根据优先级）转换 `<table>` 标签为 Markdown 表格格式。
- [x] 在 `main_cleaner.py` 的分发器中注册 `HtmlCleaner` 以处理 `.html` 文件。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- 输入一个包含广告、导航栏的网页 HTML 文件，输出的 TXT 文件只包含正文内容。
- HTML 中的标题、列表、表格（如果实现）等结构在输出的 TXT 文件中以等效的 Markdown 格式呈现。
- 清洗器成功集成到主框架中，可通过主脚本调用。

## Test Cases
- [x] `python main_cleaner.py --input-file ./samples/news_article.html` -> 验证导航栏、侧边栏、脚本和样式被移除。（对应 `pytest tests/test_html_cleaner.py::test_html_cleaner_removes_noise_and_keeps_headings`）
- [x] `python main_cleaner.py --input-file ./samples/tutorial_with_lists_tables.html` -> 验证列表和表格被正确转换为 Markdown。（对应 `pytest tests/test_html_cleaner.py::test_html_cleaner_renders_lists_and_tables`）

## Related Files / Design Docs
- `./kanban/task/T1-1-setup-cleaning-framework.md`

## Dependencies
- T1-1-setup-cleaning-framework

## Notes & Updates
- 2025-10-19: 任务创建，已放入 Backlog。
- 2025-10-20: 完成 HtmlCleaner 实现与单元测试，列表/表格转换覆盖到 `tests/test_html_cleaner.py`，并兼容无 `beautifulsoup4` 环境的轻量解析回退。
