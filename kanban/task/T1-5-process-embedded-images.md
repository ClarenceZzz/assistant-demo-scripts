# T1-5-process-embedded-images: 处理文档中的嵌入式图片

## Goal
扩展现有的 PDF 和 HTML 清洗器，使其能够提取文档中的图片，利用多模态模型生成文本描述，并将描述整合到最终的干净文本中，以丰富知识库的信息含量。

## Subtasks
- [ ] 调研并选择一个合适的图片转文本方案（例如，本地部署的 LLaVA/CogVLM，或使用 GPT-4V API）。
- [ ] 在 `BaseCleaner` 中增加一个可选的图片处理流程或钩子函数。
- [ ] 修改 `PdfCleaner` (T1-2)，使用 `page.images` 提取图片数据，并调用图片处理模块。
- [ ] 修改 `HtmlCleaner` (T1-3)，解析 `<img>` 标签，下载或解码图片，并调用图片处理模块。
- [ ] 实现图片处理模块，该模块接收图片数据，返回文本描述（可先用 OCR 作为基础实现）。
- [ ] 定义描述文本的插入格式，例如在文本中插入 `[图片描述：...]`。
- [ ] 建立图片缓存机制，避免重复处理同一张图片（基于图片内容的哈希值）。

## Developer
- Owner: codex
- Complexity: L

## Acceptance Criteria
- 当处理包含图片的 PDF 或 HTML 时，输出的 `.txt` 文件中包含由图片内容生成的文本描述。
- 生成的描述被明确的标记（如 `[图片描述：...]`）包围。
- 如果文档不含图片，清洗流程不受影响。
- 图片处理的失败（如 API 调用失败）被优雅地捕获并记录在日志中，不中断整个清洗过程。

## Test Cases
- [ ] `python main_cleaner.py --input-file ./samples/chart_report.pdf` -> 验证输出文本中包含对图表的描述。
- [ ] `python main_cleaner.py --input-file ./samples/product_page.html` -> 验证输出文本中包含对产品图片的描述。
- [ ] `python main_cleaner.py --input-file ./samples/screenshot_tutorial.pdf` -> 验证截图中的文字被 OCR 提取并插入文本。

## Related Files / Design Docs
- `./kanban/task/T1-2-implement-pdf-cleaner.md`
- `./kanban/task/T1-3-implement-html-cleaner.md`

## Dependencies
- T1-2-implement-pdf-cleaner
- T1-3-implement-html-cleaner

## Notes & Updates
- 2025-10-19: 任务创建，已放入 Backlog。这是一个增强型任务，可以在核心文本清洗功能完成后进行。
