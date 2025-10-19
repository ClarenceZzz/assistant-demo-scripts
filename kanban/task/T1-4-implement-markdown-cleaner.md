# T1-4-implement-markdown-cleaner: 实现 Markdown 文件清洗器

## Goal
为 Markdown 文件提供一个“直通”式的清洗器，主要确保文件编码统一为 UTF-8，因为其内容本身已具备良好结构。

## Subtasks
- [ ] 创建 `MarkdownCleaner` 类，继承自 `BaseCleaner`。
- [ ] 实现 `clean` 方法，该方法读取文件内容。
- [ ] 核心逻辑是检测并处理文件编码，确保最终输出为 UTF-8 编码的文本。
- [ ] （可选）添加移除 HTML 注释 `<!-- ... -->` 的逻辑。
- [ ] 在 `main_cleaner.py` 的分发器中注册 `MarkdownCleaner` 以处理 `.md` 文件。

## Developer
- Owner: [待定]
- Complexity: S

## Acceptance Criteria
- 输入一个 GBK 或其他非 UTF-8 编码的 Markdown 文件，输出的 TXT 文件为 UTF-8 编码且内容无损。
- 输入一个标准的 UTF-8 Markdown 文件，输出的 TXT 文件内容与其基本一致。
- 清洗器成功集成到主框架中，可通过主脚本调用。

## Test Cases
- [ ] 准备一个 GBK 编码的中文 Markdown 文件 `test_gbk.md`。
- [ ] `python main_cleaner.py --input-file ./samples/test_gbk.md` -> 验证 `data/clean/test_gbk.txt` 文件是 UTF-8 编码且内容正确。
- [ ] `python main_cleaner.py --input-file ./README.md` -> 验证输出内容与源文件一致。

## Related Files / Design Docs
- `./kanban/task/T1-1-setup-cleaning-framework.md`

## Dependencies
- T1-1-setup-cleaning-framework

## Notes & Updates
- 2024-05-21: 任务创建，已放入 Backlog。