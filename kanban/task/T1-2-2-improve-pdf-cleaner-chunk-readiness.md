# T1-2-2-improve-pdf-cleaner-chunk-readiness: 提升 PDF 清洗文本的分块友好度

## Goal
针对 `T1-2-1` 交付中暴露的多栏合并、句子断裂与纯数字噪声问题，改进 `PdfCleaner` 生成的文本，使其更适合向量化阶段的分块处理。

## Subtasks
- [x] 分析现有 `PdfCleaner` 行组装策略，定位多栏标题合并与硬换行的根源。
- [x] 调整段落合并逻辑，依据标点与间距恢复完整句子，减少行内断裂。
- [x] 对检测到的多栏标题/并排文本进行拆分，保持独立小节。
- [x] 过滤或压缩仅含孤立数字、坐标等无语义内容的行。
- [x] 更新或新增单元测试，覆盖多栏 PDF、纯数字行与长句重组场景。
- [x] 更新文档或注释，说明新的行处理策略与适用场景。

## Developer
- Owner: codex
- Complexity: L

## Acceptance Criteria
- 使用 `data/raw/产品说明书_OG-5308_20251020.pdf` 清洗后，文本段落句子完整，不再出现“按 拖起”式断句。
- 类似“## 安装说明 产品移动说明”被拆分为两个独立标题或段落。
- 仅包含散列数字或坐标的行被移除或合并，不影响主干语义。
- 新增/更新的单元测试全部通过，且原有测试不回退。

## Test Cases
- [x] `python3 -m pytest tests/test_pdf_cleaner.py::test_pdf_cleaner_handles_multicolumn_layout` -> 验证多栏标题拆分结果。
- [x] `python3 -m pytest tests/test_pdf_cleaner.py::test_pdf_cleaner_merges_sentence_fragments` -> 验证断句修复。
- [x] `python3 -m pytest tests/test_pdf_cleaner.py::test_pdf_cleaner_filters_numeric_noise` -> 验证数字噪声过滤。
- [x] `python3 main_cleaner.py --input-file data/raw/产品说明书_OG-5308_20251020.pdf` -> 实际输出满足上述验收标准。

## Related Files / Design Docs
- `./kanban/task/T1-2-implement-pdf-cleaner.md`

## Dependencies
- T1-2-implement-pdf-cleaner

## Notes & Updates
- 2025-10-20: 任务创建，自检发现 T1-2-1 输出存在多栏合并与断句问题，进入 Backlog 等待调度。
- 2025-10-20: 完成多栏拆分、续行合并与噪声过滤逻辑调整，新增三项单元测试并通过全量 `pytest tests/test_pdf_cleaner.py`，实测 `data/raw/产品说明书_OG-5308_20251020.pdf` 输出满足验收标准。
