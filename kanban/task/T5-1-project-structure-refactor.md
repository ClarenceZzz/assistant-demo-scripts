## Goal
- 规范化项目目录结构，迁移业务代码至 `src/assistant_demo/` 包，并确保导入路径统一。
- 引入标准化构建配置（`pyproject.toml`），为依赖与工具链管理打基础。
- 整理临时产物与测试样例，避免运行文件污染仓库。

## Subtasks
- 评估现有模块分布与依赖关系。
- 创建 `src/assistant_demo/` 包并迁移核心模块、脚本入口。
- 更新相关导入路径与执行脚本。
- 新增 `pyproject.toml` 与必要的工具配置。
- 调整 `.gitignore`，整理 `data/`、`mock/` 等目录。
- 运行 `pytest` 确认功能正常。

## Developer
- Owner: Codex
- Complexity: L

## Acceptance Criteria
- 所有业务模块均位于 `src/assistant_demo/` 包下并提供 `__init__.py`。
- CLI 入口位于包内（如 `assistant_demo.cli`），旧根目录脚本不再直接执行。
- `pyproject.toml` 定义项目元数据、依赖、`console_scripts` 入口以及常用工具配置。
- `.gitignore` 排除 `__pycache__`、`.pytest_cache/`、`data/` 运行产物等临时文件。
- 测试数据迁移至 `tests/fixtures/`，仓库根目录保持整洁。
- `pytest` 全量通过。

## Test Cases
- `pytest`

## QA
- Pending

## Related Files / Design Docs
- docs/PRD.md
- README.md

## Dependencies
- 无

## Notes & Updates
- 2025-10-22：任务创建，准备启动项目结构重构。
- 2025-10-22：已迁移代码至 `src/assistant_demo/` 包，新增统一 CLI `assistant_demo.cli`，并通过 `python -m assistant_demo.cli` 支持 `clean/chunk/ingest` 子命令。补充 `pyproject.toml`、`.gitignore`，将运行产物迁移至 `tests/fixtures/`。
- 2025-10-22：执行 `pytest`（30 项）全部通过，验证新结构与入口脚本正常。
