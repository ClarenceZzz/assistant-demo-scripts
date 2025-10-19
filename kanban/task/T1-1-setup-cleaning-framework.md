# T1-1-setup-cleaning-framework: 搭建文本清洗基础框架

## Goal
搭建一个可扩展的文本清洗处理框架，该框架负责调度不同文件类型的清洗器、处理文件 I/O、统一日志记录，并标准化输出格式。

## Subtasks
- [ ] 创建主处理脚本 `main_cleaner.py`，实现命令行参数解析（如 `--input-file`）。
- [ ] 定义一个抽象基类 `BaseCleaner`，包含 `clean(self, file_path)` 接口，所有具体清洗器都将继承它。
- [ ] 在主脚本中实现一个分发器（dispatcher），能根据文件扩展名（`.pdf`, `.html`, `.md`）选择并实例化对应的清洗器。
- [ ] 实现文件输出逻辑，将处理结果统一保存到 `data/clean/{document_id}.txt`。
- [ ] 配置全局日志系统（使用 Python `logging` 模块），记录处理流程、成功、失败及异常信息。

## Developer
- Owner: codex
- Complexity: M

## Acceptance Criteria
- 运行 `python main_cleaner.py --input-file <path_to_file>` 命令可以成功执行，即使具体清洗器尚未实现。
- 脚本执行后，会在 `data/clean/` 目录下生成一个对应的 `.txt` 文件（内容可为空或为占位符）。
- 控制台或日志文件中会输出标准化的日志信息，如 "INFO: Processing file <file_name>..." 和 "INFO: Successfully cleaned file <file_name>..."。
- 代码结构清晰，`BaseCleaner` 和分发器逻辑已就位，易于后续扩展。

## Test Cases
- [ ] `python main_cleaner.py --input-file ./samples/dummy.pdf` -> 检查 `data/clean/dummy.txt` 和日志是否生成。
- [ ] `python main_cleaner.py --input-file ./samples/dummy.html` -> 检查 `data/clean/dummy.txt` 和日志是否生成。
- [ ] `python main_cleaner.py --input-file ./samples/non_existent_file.txt` -> 检查是否优雅地抛出文件未找到的错误并记录日志。

## Related Files / Design Docs
- `./kanban/board.md`

## Dependencies
- 无

## Notes & Updates
- 2024-05-21: 任务创建，已放入 Backlog。