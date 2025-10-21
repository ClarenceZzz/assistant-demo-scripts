# assistant-demo-scripts

## 命令行工具

- 清洗文档: `python main_cleaner.py --input-file <path>`
- 仅执行分块: `python main_chunker.py --input-file <clean-text> --output-dir data/chunks --disable-llm --llm-log-dir <log-dir>`
- 完整导入流程: `python -m tools.ingest --input-file <path> --disable-llm --llm-log-dir <log-dir> --dead-letter-dir data/dead_letters`
- 可选参数: `--title`, `--meta-file`, `--clean-output-dir`, `--chunks-output-dir`, `--llm-log-dir`, `--dead-letter-dir`, `--loader-batch-size`

完整导入脚本顺序执行：清洗 → 分块 → 嵌入 → 数据库写入。`--disable-llm` 可在本地测试时跳过远程 LLM 调用，使用兜底摘要逻辑；`--llm-log-dir` 将请求与响应保存为 JSON；`--dead-letter-dir` 记录嵌入失败批次，`--loader-batch-size` 控制批量大小。
