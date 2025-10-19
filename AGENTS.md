# 项目规范

## 看板工作流

本项目使用看板工作流进行任务管理，请严格遵守以下规范。

阅读 ./docs/PRD.md 了解项目背景和需求。

统一 Kanban 看板列（项目级）：

* **Backlog**（需求池）
* **To Do**（当前周期待办）
* **In Progress**（开发中）
* **In Review**（代码审查）
* **Testing / QA**（QA 测试中）
* **Blocked**（阻塞）
* **Done**（验收通过）

> 每个任务卡必须包含：目标、子任务、开发者、估算复杂度（S/M/L）、验收标准、测试用例、相关文件/设计稿、依赖任务。

## 任务状态定义（严格）

* **In Progress**：除了完成任务外，还需包含单元测试（若适用）。
* **In Review**：PR 描述需写清修改点、运行方式、影响面、回归风险；至少 1 名审查者通过（由你切换身份扮演）。
* **Testing / QA**：QA 按测试用例执行，记录 BUG，BUG 分级（P0/P1/P2）。所有 P0 必须解决，P1 需评估。QA 完成后 QA 在卡片上写“QA Passed”（由你切换身份扮演）。
* **Done**：产品经理或维护者对接收准则（Acceptance Criteria）进行最终验收，若通过，移动卡片到 Done。（由你切换身份扮演）

Kanban 数据记录在 `./kanban/` 目录（Markdown 格式）.
- `./kanban/board.md` 维护看板状态。
- `./kanban/task/` 目录存放每个任务的详细描述（Markdown）, 每个任务一个文件，文件名为任务 ID，例如 `A-1-initialize-repo.md`。此文件内不但要记录任务描述，还要记录开发过程中遇到的问题与解决方案、BUG 记录、Review 意见等。

---

请检查 ./kanban/ 目录：
- 如果不存在，请根据 PRD 创建初始看板和任务文件。
- 如果存在，请根据看板上的任务状态，继续推进任务，或遵照用户本次的指示进行工作。


## 代码规范

1.  [Git 工作流](#1-git-工作流)
2.  [编码规范](#2-编码规范)
3.  [测试规范](#3-测试规范)
4.  [依赖管理](#4-依赖管理)
5.  [代码审查流程](#5-代码审查流程)
6.  [文档规范](#6-文档规范)

---

### 1. Git 工作流

我们采用基于功能分支（Feature Branch）的工作流，分支不一定预先创建好，缺少时由你创建

-   **主分支**:
    -   `main`: 生产分支，始终保持稳定和可部署状态。只接受来自 `develop` 分支的合并。
    -   `develop`: 开发主分支，集成了所有已完成的功能。是新功能分支的起点。
-   **分支命名**:
    -   功能开发: `feat/<feature-name>` (e.g., `feat/html-parser`)
    -   Bug修复: `fix/<issue-name-or-id>` (e.g., `fix/pdf-page-number-error`)
    -   重构: `refactor/<module-name>` (e.g., `refactor/chunking-logic`)
    -   文档: `docs/<topic>` (e.g., `docs/update-readme`)
-   **提交信息 (Commit Message)**:
    -   我们遵循 **Conventional Commits** 规范。
    -   格式: `<type>(<scope>): <subject>`
    -   **Type**: `feat`, `fix`, `refactor`, `test`, `docs`, `style`, `chore`
    -   **Scope** (可选): 影响的模块，如 `ingest`, `chunking`, `embedding`, `db`
    -   **示例**:
        -   `feat(ingest): add support for parsing markdown files`
        -   `fix(db): resolve race condition in upsert logic`
        -   `test(chunking): add unit tests for recursive text splitter`

### 2. 编码规范

代码的清晰性和一致性至关重要。

-   **语言与风格**:
    -   遵循 **PEP 8** 风格指南。使用 `black` 进行代码格式化，`isort` 进行 import 排序。
    -   项目应配置 `.pre-commit-config.yaml`，在提交前自动执行检查。
-   **类型提示 (Type Hinting)**:
    -   **强制要求**：所有函数签名（参数和返回值）都必须包含类型提示。
    -   使用 `from typing import ...` 引入 `List`, `Dict`, `Optional`, `Tuple` 等。
    -   这有助于静态分析（`mypy`）和代码可读性。
-   **模块化与职责单一 (Separation of Concerns)**:
    -   代码结构应遵循清晰的关注点分离原则。每个模块应只负责一项核心任务。
    -   **建议的模块结构**：
        -   `parsers/`: 存放所有与解析不同文件格式（PDF, HTML, Markdown等）相关的代码。
        -   `chunkers/` 或 `splitters/`: 存放所有文本分块、重叠和元数据提取的逻辑。
        -   `embedders/`: 封装与外部Embedding模型（如DashScope）API交互的代码。
        -   `storages/` 或 `db/`: 负责所有与向量数据库（PgVector）的读写操作。
    -   将不同职责的代码严格隔离，可以极大地提高代码的可测试性和可维护性。
-   **配置与密钥管理**:
    -   **严禁**将任何 API Key、密码等敏感信息硬编码在代码中。
    -   使用环境变量 (`os.environ.get()`) 读取敏感信息。
    -   非敏感配置（如分块大小、模型名称）应存放在独立的配置文件中（如 `configs/ingest.yaml`），并通过配置加载器读取。
-   **日志 (Logging)**:
    -   使用 Python 内置的 `logging` 模块，而不是 `print()`。
    -   在关键步骤记录信息，如：开始处理哪个文档、生成了多少个 Chunks、成功写入多少条记录。
    -   错误日志应包含足够的回溯信息（Traceback）以供排查。
    -   日志级别：`INFO` 用于关键流程节点，`DEBUG` 用于开发调试，`WARNING` 用于可恢复的异常，`ERROR` 用于导致当前任务失败的严重问题。

### 3. 测试规范

"Code without tests is broken by design."

-   **测试框架**:
    -   使用 `pytest` 作为主要的测试框架。
-   **测试目录与命名**:
    -   所有测试代码必须放在 `tests/` 目录下，并保持与主代码相似的目录结构。
    -   测试文件名必须以 `test_` 开头 (e.g., `test_chunking.py`)。
    -   测试函数名必须以 `test_` 开头 (e.g., `test_chunk_overlap_logic`)。
-   **测试类型**:
    1.  **单元测试 (Unit Tests)**:
        -   **目标**: 针对单一函数或类进行测试，不依赖外部服务（数据库、API）。
        -   **要求**: 每个核心函数（如文本清洗、分块算法）都必须有对应的单元测试。
        -   **实践**: 使用 `pytest.mark.parametrize` 覆盖多种边界情况。
    2.  **集成测试 (Integration Tests)**:
        -   **目标**: 测试多个模块协同工作的正确性。
        -   **要求**: 至少覆盖从“文件读取”到“向量入库”的完整流程。
        -   **实践**:
            -   使用 `unittest.mock` 或 `pytest-mock` 来模拟（Mock）外部 API 调用（如 DashScope Embedding），避免产生真实费用和网络依赖。
            -   可以连接到一个本地或CI环境专用的测试数据库，验证数据写入的正确性。
-   **测试覆盖率**:
    -   使用 `pytest-cov` 插件来衡量测试覆盖率。
    -   目标覆盖率 **不低于 85%**。每次提交 PR 时，覆盖率不得下降。

### 4. 依赖管理

-   使用 `requirements.txt` 文件来管理项目依赖。
-   应包含两个文件：
    -   `requirements.txt`: 生产环境所需的核心依赖。
    -   `requirements-dev.txt`: 开发和测试所需的额外依赖（如 `pytest`, `black`, `mypy`）。
-   务必使用 `pip freeze` 等工具锁定依赖版本，以保证环境的一致性。

### 5. 代码审查流程 (Pull Request)

1.  从 `develop` 分支创建你的功能分支。
2.  完成开发和测试后，确保所有本地测试通过 (`pytest`)。
3.  向 `develop` 分支发起一个 **Pull Request (PR)**。
4.  **PR 描述模板**:
    ```markdown
    ### 1. 本次变更解决了什么问题？
    (简要描述背景和目标，关联 Issue ID)

    ### 2. 本次变更做了什么？
    (分点说明主要改动)
    - 新增了 HTML 解析器
    - 重构了分块逻辑以支持语义切分
    - ...

    ### 3. 如何进行测试？
    (提供简单的测试步骤，帮助审查者验证)
    - 运行 `pytest tests/test_html_parser.py`
    - 执行 `python tools/ingest.py --input data/raw/sample.html` 并检查数据库

    ### 4. Checklist
    - [x] 我已阅读并遵循了 `CONTRIBUTING.md`。
    - [x] 我的代码遵循了项目的编码规范。
    - [x] 我为新增或修改的代码编写了必要的测试。
    - [x] 所有测试均已通过。
    ```
5.  PR 必须获得 **至少一位** 其他团队成员的批准（Approve）。
6.  所有 CI 检查（如 Linting, Testing, Coverage）必须通过。
7.  审查通过后，使用 **Squash and Merge** 将 PR 合并到 `develop` 分支，保持主干历史的整洁。

### 6. 文档规范

-   为所有公共模块、类和函数编写清晰的 **Docstrings**（推荐 Google 或 NumPy 风格）。
-   如果你的变更影响了项目的使用方式或架构，请同步更新 `README.md` 或其他相关文档。
-   复杂的算法或业务逻辑应在代码中附上必要的注释。