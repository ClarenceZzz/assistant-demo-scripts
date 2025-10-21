# assistant-demo-scripts

## 命令行工具

- 清洗文档: `python main_cleaner.py --input-file <path>`
- 仅执行分块: `python main_chunker.py --input-file <clean-text> --output-dir data/chunks --disable-llm --llm-log-dir <log-dir>`
- 完整导入流程: `python -m tools.ingest --input-file <path> --disable-llm --llm-log-dir <log-dir>`
- 可选参数: `--title`, `--meta-file`, `--clean-output-dir`, `--chunks-output-dir`, `--llm-log-dir`

`--disable-llm` 可在本地测试时跳过远程 LLM 调用，使用兜底摘要逻辑；`--llm-log-dir` 则会将每次请求与响应保存为 JSON 便于排查。
