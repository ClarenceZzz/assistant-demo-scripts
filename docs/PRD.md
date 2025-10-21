# 文档向量化项目（供数据 / 知识工程师使用）

## 目标与心智模型
- **目标**：将原始文档拆分为可检索的文本分块，并为每个分块生成嵌入向量，最终加载到向量库（Postgres + pgvector）供 RAG 检索使用。
- **心智模型**：把这件事当作一次定制化的 *ETL Pipeline*——Extract（提取原文）→ Transform（清洗、分块、生成向量）→ Load（写入数据库）。理解这一点，有助于沿用你熟悉的工程套路：日志、配置、重试、回滚、监控都适用。

---

## 1. 拉取原始文档（Extract）
- **为什么**：确保所有语料来源有统一的入口，便于审计和自动化调度。
- **操作**：
    - 支持格式：Markdown、HTML、PDF、工单导出的 CSV/JSON 等。
    - 将原始文件放入 `data/raw/`，文件名包含 `document_id`（示例：`manual_ac_2024.pdf`）。
    - 建议建立 `docs/sources.md` 记录数据来源、更新频率、联系人。

---

## 2. 文本清洗（Transform-1）
- **为什么**：输入越干净、结构越明确，后续分块和检索效果就越好；同时提前做脱敏，规避合规风险。
- **工具建议**：
    - PDF：`pdfplumber` 或 `pdfminer.six`（支持解析文本坐标、字体信息）。
    - HTML：`BeautifulSoup` 去除 `<script>`、`<style>`、广告等无关节点。
    - Markdown：直接读取或用 `markdown` 库渲染后再处理。
- **操作要点**：
    1. 统一转为 UTF-8。
    2. 去除噪声：例如使用 `pdfplumber` 获取页面元素坐标（`y0`, `y1`），过滤顶部/底部 10% 的内容可高效移除页眉页脚。
    3. 保留/提取结构信息：标题前加 `##`，列表项保留 `- `，表格可转为 Markdown 表头；必要时将标题或加粗字体记录在 `metadata.section` 中。
    4. 输出到 `data/clean/{document_id}.txt`，并记录处理日志（行数、异常）。

---

## 3. 分块（Chunking，Transform-2）
- **为什么**：大模型的上下文窗口有限，把文本拆成“既能覆盖完整语义，又不过长”的块，才能在检索阶段精确回溯原文；适度重叠能降低语义被切断的概率。
- **原则**：
    - 块长度控制在 300–500 字左右。
    - 邻接块重叠 80–100 字，保留上下文连续性。
    - 优先按文档结构（标题、段落）切分，再按长度细分。
- **算法伪代码**：
  ```pseudo
  function chunk_document(text):
      sections = split_by_headings(text)          // 按 H1/H2 或字体大小分段
      all_chunks = []
      for section in sections:
          paragraphs = split_by_paragraphs(section)
          for p in paragraphs:
              if len(p) > CHUNK_SIZE:
                  all_chunks.extend(recursive_split(p, CHUNK_SIZE, OVERLAP))
              else:
                  all_chunks.append(p)
      merged = merge_small_chunks(all_chunks, CHUNK_SIZE) // 可选，合并过短块
      return merged
  ```
- **输出格式**：`data/chunks/{document_id}.jsonl`，示例：
  ```json
  {
    "document_id": "manual_ac_2024",
    "chunk_id": "manual_ac_2024-0001",
    "content": "……文本……",
    "metadata": {
      "title": "XX 型号空调快速指南",
      "section": "重置步骤",
      "page_number": 12,
      "last_modified_at": "2024-09-01",
      "source_type": "manual"
    }
  }
  ```

---

## 4. 调用 DashScope Embedding（Transform-3）
- **为什么**：嵌入向量是文本的“数学表示”，用于度量语义相似度；批量调用能显著降低延迟与成本。
- **批量示例（Python）**：
  ```python
  import os
  from dashscope import TextEmbedding
  from tenacity import retry, stop_after_attempt, wait_exponential

  api_key = os.environ["DASHSCOPE_API_KEY"]

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
  def embed_batch(texts: list[str]) -> list[list[float]]:
      # DashScope 支持批量输入，按顺序返回结果
      resp = TextEmbedding.call(
          model="text-embedding-v2",
          input=texts,
          api_key=api_key,
      )
      # resp.output.embeddings 为列表，与输入顺序一致
      return [item["embedding"] for item in resp.output["embeddings"]]

  def process_jsonl(path):
      chunks, contents = [], []
      with open(path, "r", encoding="utf-8") as f:
          for line in f:
              chunk = json.loads(line)
              chunks.append(chunk)
              contents.append(chunk["content"])
              if len(contents) == 8:  # 根据限速调节批量大小
                  embeddings = embed_batch(contents)
                  for c, emb in zip(chunks[-len(embeddings):], embeddings):
                      c["embedding"] = emb
                  contents.clear()
      if contents:
          embeddings = embed_batch(contents)
          for c, emb in zip(chunks[-len(embeddings):], embeddings):
              c["embedding"] = emb
      return chunks
  ```
- **注意事项**：
    - 关注 DashScope QPS/并发限制（可在配置中设置批量大小、时间间隔）。
    - 对失败请求要重试、记录日志，必要时写入“死信”文件以便复查。

---

## 5. 写入 PgVector（Load）
- **为什么**：`DELETE` + `INSERT` 结合数据库事务是一种简单可靠的 Upsert 策略，保证文档被更新一次，向量表也同步更新一次。
- **建表参考**：
  ```sql
  CREATE TABLE rag_chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT,
    content TEXT,
    embedding VECTOR(1536),
    metadata JSONB,
    last_modified TIMESTAMP DEFAULT now()
  );
  CREATE INDEX idx_rag_chunks_metadata ON rag_chunks USING GIN (metadata jsonb_path_ops);
  CREATE INDEX idx_rag_chunks_document ON rag_chunks(document_id);
  CREATE INDEX idx_rag_chunks_embedding_hnsw ON rag_chunks USING hnsw (embedding vector_cosine_ops);
  ```
- **写入示例（保证事务）**：
  ```python
  import json
  import psycopg2
  from contextlib import contextmanager

  @contextmanager
  def get_conn():
      conn = psycopg2.connect(dsn)
      try:
          yield conn
          conn.commit()
      except Exception:
          conn.rollback()
          raise
      finally:
          conn.close()

  def upsert_chunks(chunks):
      doc_id = chunks[0]["document_id"]
      with get_conn() as conn:
          with conn.cursor() as cur:
              cur.execute("DELETE FROM rag_chunks WHERE document_id = %s", (doc_id,))
              for c in chunks:
                  cur.execute(
                      """
                      INSERT INTO rag_chunks (chunk_id, document_id, content, embedding, metadata)
                      VALUES (%s, %s, %s, %s, %s)
                      """,
                      (
                          c["chunk_id"],
                          c["document_id"],
                          c["content"],
                          c["embedding"],
                          json.dumps(c["metadata"]),
                      ),
                  )
  ```
- **健全性检查**：写入完成后随机抽查几条记录，验证：
    - `embedding` 维度是否正确（1536）。
    - `content` 是否非空、无乱码。
    - `metadata` 是否可 JSON 解析，关键字段是否齐全。

---

## 6. 封装 CLI / 脚本
- **为什么**：标准化入口便于自动化调度、复现和回溯。
- **示例命令**：
  ```bash
  python tools/ingest.py --input data/raw/manual_ac_2024.pdf --doc-id manual_ac_2024
  ```
- **建议流程**：
    1. 解析参数，加载配置（`configs/ingest.yaml`）决定分块长度、模型名称等。
    2. 执行清洗 → 分块 → 嵌入 → 写库。
    3. 输出处理统计：文档数量、chunk 数、耗时、失败列表。
    4. 执行健全性检查并打印结果。
    5. 将日志写入文件（便于调试）。

---

## 7. 抽检与监控
- **抽检**：提供脚本随机选取若干 `chunk_id` 输出 `content`、`metadata`、`embedding` 维度，必要时导出给业务或 QA 复核。
- **自动化评估**：与 QA、AI 工程师协同，使用黄金问答集验证检索效果；统计向量库容量、每日增量数。
- **监控**：记录每次导入的更新时间、文档数、Token 成本，为运维/SRE 做成本与容量规划提供依据。

---

## 8. 后续扩展建议
- **配置化**：将分块长度、重叠、模型参数等放在配置文件/配置中心，便于热更新。
- **调度化**：在 CI/CD 或调度平台（Dagster/Airflow）上定期运行增量任务，结合 git tag / 文档更新时间触发。
- **多环境管理**：区分测试/预发/正式数据库，避免向量数据混淆；同时做好备份与回滚脚本。

---

> 遵循以上步骤，可以在 **清晰可复现** 的前提下，完成 Stage 1 所需的知识向量化工作。每个环节都建议在代码中加入日志、异常处理与告警，确保流程在生产环境运行时具备足够鲁棒性。
