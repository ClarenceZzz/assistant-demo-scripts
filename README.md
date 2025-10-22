# assistant-demo-scripts

## 命令行工具

安装依赖后，可通过 `assistant-demo` 命令（或 `python -m assistant_demo.cli`）调用各流程：

- 清洗文档: `assistant-demo clean --input-file <path> [--output-dir data/clean]`
- 仅执行分块: `assistant-demo chunk --input-file <clean-text> --output-dir data/chunks [--disable-llm --llm-log-dir <log-dir>]`
- 完整导入流程: `assistant-demo ingest --input-file <path> [--disable-llm --llm-log-dir <log-dir> --dead-letter-dir data/dead_letters --loader-batch-size 16]`

若暂时不想安装，也可以在 src/ 目录下直接用模块方式运行：`python -m assistant_demo.cli ingest --input-file <path> [--disable-llm --llm-log-dir <log-dir> --dead-letter-dir data/dead_letters --loader-batch-size 16]`

可选参数包括 `--title`, `--meta-file`, `--clean-output-dir`, `--chunks-output-dir`, `--llm-log-dir`, `--dead-letter-dir`, `--loader-batch-size` 等。完整导入脚本顺序执行：清洗 → 分块 → 嵌入 → 数据库写入。`--disable-llm` 可在本地测试时跳过远程 LLM 调用；`--llm-log-dir` 将请求与响应保存为 JSON；`--dead-letter-dir` 记录嵌入失败批次。样例测试数据存放在 `tests/fixtures/` 目录下。
