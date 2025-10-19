# T1-2-implement-pdf-cleaner: 实现 PDF 文件清洗器

## Goal
基于基础框架，实现对 PDF 格式文档的文本清洗功能，包括去除页眉页脚、保留结构信息，并确保编码正确。

## Subtasks
- [ ] 在项目中添加 `pdfplumber` 作为依赖。
- [ ] 创建 `PdfCleaner` 类，继承自 `BaseCleaner`。
- [ ] 实现 `clean` 方法，使用 `pdfplumber` 提取文本和页面元素信息。
- [ ] 编写逻辑，根据页面坐标（`page.height`, `char.y0`）过滤掉页面顶部和底部 10% 的内容。
- [ ] 添加逻辑，通过字体大小或加粗等属性识别标题，并在其行首添加 `## `。
- [ ] 确保所有提取的文本最终都以 UTF-8 编码输出。
- [ ] 在 `main_cleaner.py` 的分发器中注册 `PdfCleaner` 以处理 `.pdf` 文件。

## Developer
- Owner: [待定]
- Complexity: L

## Acceptance Criteria
- 输入一个带页眉页脚的 PDF 文件，输出的 TXT 文件中不包含页眉页脚内容。
- 输入一个包含多级标题的 PDF 文件，输出的 TXT 文件中，标题能被正确识别并以 Markdown 格式 (`## `) 标记。
- 处理包含中文或其他非-ASCII 字符的 PDF 时，输出的文本无乱码。
- 清洗器成功集成到主框架中，可通过主脚本调用。

## Test Cases
- [ ] `python main_cleaner.py --input-file ./samples/report_with_header_footer.pdf` -> 验证输出文本中无页眉页脚。
- [ ] `python main_cleaner.py --input-file ./samples/manual_with_headings.pdf` -> 验证输出文本中标题前有 `## `。
- [ ] `python main_cleaner.py --input-file ./samples/chinese_article.pdf` -> 验证输出文本编码正确。

## Related Files / Design Docs
- `./kanban/task/T1-1-setup-cleaning-framework.md`

## Dependencies
- T1-1-setup-cleaning-framework

## Notes & Updates
- 2024-05-21: 任务创建，已放入 Backlog。