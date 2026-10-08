# Lab 5：mini-dify v0.5 —— 知识库 RAG

> 目标：创建知识库，上传文档（txt / md / pdf / html，或直接粘贴文本），在后台完成提取、清洗、分段、向量化、存储；支持向量、BM25、混合三种检索和父子分段；在工作流中用知识检索节点 + LLM 上下文实现 RAG。
> 起点 `v0.4`，终点 `v0.5`。

## 依赖

```bash
cd backend && uv add "pypdf>=4" "python-multipart>=0.0.9" "numpy>=1.26"
```

`python-multipart` 是 FastAPI 处理文件上传（`UploadFile`、`Form`）所必需的。

## 构建顺序

| 步骤 | 文件 | 章节 |
|---|---|---|
| 1 | `app/rag/processing.py`：`extract_text`、`clean_text`、`recursive_split`、`_merge`、`split_document` | 22 |
| 2 | `app/models.py`：`Dataset`、`Document`（`raw_content`、`status`）、`Segment`（`vector`、`parent_content`）、`EmbeddingCache` | 22 |
| 3 | `app/rag/index.py`：`embed_texts`（带缓存）、`tokenize`、`bm25_scores`、`retrieve`、`format_context` | 22、23 |
| 4 | `app/rag/indexing.py`：`index_document`（状态流转）、`index_in_background` | 22 |
| 5 | `app/api/datasets.py`：知识库、文档上传（multipart）、分段查看、召回测试 | 23 |
| 6 | `app/workflow/nodes/knowledge.py`；LLM 节点增加 `context` 配置 | 23 |
| 7 | 前端：`pages/DatasetsPage.tsx`（列表 / 创建 / 详情 / 召回测试，索引期间轮询状态）、知识检索节点面板、LLM 面板的“上下文”字段 | 23 |

## 演示

1. 知识库 → 创建“产品手册”（通用分段，分段最大长度 120）；
2. 粘贴下面这段文本：

```
第一章 安装。后端使用 FastAPI，运行 uv sync 安装依赖，然后用 uvicorn 启动服务。

第二章 工作流。工作流由节点和边组成，引擎按照拓扑顺序执行节点，支持条件分支与并行。

第三章 退款政策。购买后七天内可以无理由退款，超过七天需要提供质量问题证明。
```

3. 状态变为“可用”后，点击文档名，能看到 3 个分段；
4. 召回测试：问“怎么退款”，选择混合检索，第一条结果是第三章；
5. 再创建一个“父子分段”知识库，用同样的文本，问“超过七天需要什么”，返回的是第三章的完整段落；
6. 新建 Chatflow，按第 23 章 23.4 节的步骤搭建 RAG 流程，然后提问。

## 验收清单

- [ ] `uv run pytest -q`：34 个测试通过（v0.5 的数量）
- [ ] 上传 PDF 能提取出文字（扫描版 PDF 没有文字层，提取不到，这是预期的）
- [ ] 索引状态能在前端实时更新；出错的文档显示“出错”，鼠标悬停可以看到原因
- [ ] 三种检索方法都能命中；混合检索的分数由两部分组成
- [ ] RAG 工作流中，LLM 的 prompts 里包含检索到的内容

## 写作时踩到的坑（真实记录）

1. **CRLF**：浏览器提交表单时会把换行转换成 `\r\n`，导致 `\n\n` 分隔符失效（第 22 章 22.4 节）。

另有两个**设计时就规避掉的坑**（不是实际踩到的）：

- **BM25 分数的量纲**：BM25 的分数可能是 3.7，余弦相似度却在 0 到 1 之间，直接加权相加的话，关键词分数会完全压倒向量分数。所以先除以最大值归一化。
- **`hash()` 的随机盐**：mock embedding 没有使用 Python 内置的 `hash()`。`hash()` 对字符串加了每个进程不同的随机盐，单进程测试能过，但 v1.0 里 API 和 Celery Worker 是两个进程，算出的向量会不一样，检索就会悄悄失效。所以从一开始就用了稳定的 FNV-1a。
