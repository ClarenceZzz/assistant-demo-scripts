# T2-4-implement-small-chunk-merger (Optional): 实现小块合并器

## Goal
为 `Chunker` 管道添加一个可选的优化步骤，用于将过短的、相邻的文本块合并起来，以避免产生太多碎片化、低信息量的块，提升检索质量。

## Subtasks
- [ ] 创建一个 `merge_small_chunks(chunks, min_chunk_size, max_chunk_size)` 函数，输入参数 `chunks` 是一个包含完整 chunk 字典的列表。
- [ ] 编写逻辑：遍历 `chunks` 列表，如果一个块的长度小于 `min_chunk_size`，则尝试将其与后一个块合并。
- [ ] 合并时：
    - [ ] 拼接 `content`。
    - [ ] 智能地处理 `metadata`：保留第一个块的 `metadata`（包括其 `chunk_index` 和 `section`），并丢弃第二个块的 `metadata`。
- [ ] 确保合并后的新块长度不超过 `max_chunk_size`。
- [ ] 合并完成后，需要重新遍历整个 `chunks` 列表，并**重新生成 `chunk_id` 和 `chunk_index`**，以确保它们在合并后仍然是连续和正确的。
- [ ] 将此函数集成到 `Chunker` 类的 `chunk` 方法的末尾。

## Developer
- Owner: `[待分配]`
- Complexity: M

## Acceptance Criteria
- 输入一个包含多个过短块（如只有标题）的列表，输出的列表块数减少，且块长度更均衡。
- 合并后的块内容和元数据是合理的。
- 不会产生超过 `max_chunk_size` 的块。
- 经过合并处理后，返回的 `chunks` 列表中的 `chunk_index` 仍然是从0开始连续递增的。

## Test Cases
- [ ] `pytest tests/test_chunker.py::test_merger_combines_short_chunks` -> 验证合并功能。
- [ ] `pytest tests/test_chunker.py::test_merger_respects_max_size` -> 验证合并时不会超出长度限制。
- [ ] `pytest tests/test_chunker.py::test_merger_maintains_consecutive_index` -> 验证合并后 `chunk_index` 的连续性。

## Related Files / Design Docs
- `chunkers/pipeline.py` (在其中添加合并逻辑)

## Dependencies
- T3-3-build-chunking-pipeline

## Notes & Updates
- 2025-10-20: 任务创建。此为优化任务，可在核心功能完成后进行。