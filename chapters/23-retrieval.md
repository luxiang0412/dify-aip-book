# 第 23 章 检索、融合与上下文注入

> 本章目标：理解向量检索、全文检索、混合检索各自擅长什么；实现 BM25 和加权融合；实现知识检索节点，以及 LLM 节点的 `{{#context#}}` 上下文注入，跑通完整的 RAG 工作流。
> 前置：第 22 章。对应代码：mini-dify **v0.5** `backend/app/rag/index.py`（`retrieve`、`bm25_scores`）、`workflow/nodes/knowledge.py`、`nodes/llm.py`（context）。

## 23.1 问题：怎样找到“最相关”的那几段

| 方法 | 原理 | 擅长 | 不擅长 |
|---|---|---|---|
| **向量检索**（语义） | 问题和分段都转换成向量，比较余弦相似度 | 同义表达（“怎么退钱” ≈ “退款流程”） | 精确词：型号、人名、错误码、专有名词 |
| **全文检索**（关键词，BM25） | 统计问题里的词在分段中出现的频率和稀有程度 | 精确匹配（“ERR_1042”） | 换一种说法就找不到了 |
| **混合检索** | 两路都检索，再把分数融合起来 | 兼顾两者 | 多一些计算开销 |

在生产环境中，混合检索几乎总是更好的默认选择。

## 23.2 Dify 是怎么做的

### 23.2.1 四种检索方法

```python
# api/core/rag/retrieval/retrieval_methods.py
class RetrievalMethod(StrEnum):
    SEMANTIC_SEARCH = "semantic_search"
    FULL_TEXT_SEARCH = "full_text_search"
    HYBRID_SEARCH = "hybrid_search"
    KEYWORD_SEARCH = "keyword_search"          # 经济模式：不用 embedding，只用 jieba 关键词表
```

`api/core/rag/datasource/retrieval_service.py:93` 的 `RetrievalService.retrieve` 根据检索方法，并发地执行向量检索和全文检索（各自交给向量库完成），然后把结果交给 rerank。

### 23.2.2 两种融合（rerank）方式

```python
# api/core/rag/rerank/rerank_type.py
class RerankMode(StrEnum):
    RERANKING_MODEL = "reranking_model"     # 用专门的 rerank 模型重新打分（Cohere、Jina、bge-reranker……）
    WEIGHTED_SCORE = "weighted_score"       # 向量分数和关键词分数加权求和
```

加权融合（`api/core/rag/rerank/weight_rerank.py:20` `WeightRerankRunner.run`）：

```python
query_scores = self._calculate_keyword_score(query, documents)                         # 79
query_vector_scores = self._calculate_cosine(self.tenant_id, query, documents, ...)     # 133
for document, query_score, query_vector_score in zip(...):
    score = (self.weights.vector_setting.vector_weight * query_vector_score
             + self.weights.keyword_setting.keyword_weight * query_score)
    if score_threshold and score < score_threshold:
        continue
```

关键词分数的计算方法：先用 jieba 分别提取问题和分段的关键词，再计算 TF-IDF 向量的余弦相似度。

**Rerank 模型**是另一种思路：它是一个交叉编码器（cross-encoder），把“问题 + 分段”一起输入模型，直接输出相关性分数。精度明显高于向量相似度，但要对每个候选分段都调用一次，所以一般只用来**对前几十个候选结果重新排序**。

### 23.2.3 多知识库与路由

工作流里的知识检索节点可以选择多个知识库（`api/core/rag/retrieval/dataset_retrieval.py:126` `DatasetRetrieval`）：

- `multiple_retrieve`（第 793 行）：在所有知识库中检索，合并后统一 rerank；
- `single_retrieve`（第 651 行）：**路由模式**，先让 LLM 根据各个知识库的描述，判断问题应该去哪个库查，再只查那一个库。

另外还支持**元数据过滤**（第 1511 行 `get_metadata_filter_condition`）：比如只检索“部门=财务”的文档，过滤条件可以手动配置，也可以让 LLM 从问题中自动提取（第 1615 行）。

### 23.2.4 上下文注入

知识检索节点的输出 `result` 是一个列表：`[{content, title, score, metadata}, ...]`。LLM 节点的 **context** 配置选中这个变量后，在提示词里写 `{{#context#}}`，就会被替换成格式化之后的检索结果（第 5 章 5.3.1 的 `raw_prompt.replace("{{#context#}}", context or "")`）。Dify 的简单模式还会自动套上一段固定的上下文提示词（`core/prompt/prompt_templates/common_chat.json` 里的 `context_prompt`）：“Use the following context as your learned knowledge, inside `<context></context>` XML tags... If you don't know, just say that you don't know...”

## 23.3 从零实现

### 23.3.1 分词与 BM25

```python
# backend/app/rag/index.py
def tokenize(text: str) -> list[str]:
    """拉丁字符按单词切分，中文按字符二元组切分（作为 jieba 的简易替代）。"""
    text = text.lower()
    tokens = _LATIN.findall(text)
    for run in _CJK.findall(text):
        tokens += [run[i:i + 2] for i in range(len(run) - 1)] or [run]
    return tokens
# tokenize("退款政策 refund") == ["refund", "退款", "款政", "政策"]

def bm25_scores(query, docs, k1=1.5, b=0.75) -> list[float]:
    q, toks = tokenize(query), [tokenize(d) for d in docs]
    n, avgdl = len(docs), sum(len(t) for t in toks) / len(docs)
    df = Counter(term for t in toks for term in set(t))                     # 每个词出现在多少篇分段里
    scores = []
    for t in toks:
        tf, score = Counter(t), 0.0
        for term in q:
            if term in tf:
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))   # 越稀有的词，权重越高
                score += idf * tf[term] * (k1 + 1) / (tf[term] + k1 * (1 - b + b * len(t) / avgdl))
        scores.append(score)
    return scores
```

BM25 的直觉是：**问题里的词在这个分段中出现得越多越好，但收益递减（k1 控制）；越稀有的词越重要（idf）；分段越长越要打折扣（b 控制）**。中文按二元组切分是一个“够用”的近似：“退款”能匹配到“退款政策”。但它也会产生一些无意义的二元组（例如上面的“款政”）。生产环境请用 jieba 之类的分词器。

### 23.3.2 检索与融合

```python
def retrieve(dataset_ids, query, *, method="hybrid_search", top_k=4, score_threshold=0.0,
             vector_weight=0.7, tenant_id=None) -> list[Hit]:
    # 1. 只取本工作空间的知识库（v1.0），以及状态为 completed、enabled 的分段
    # 2. 向量分数：按知识库的 embedding 模型分组，每个模型只为查询生成一次向量，numpy 计算余弦
    if method in ("semantic_search", "hybrid_search"):
        for model_spec, idxs in by_model.items():
            qv = np.array(embed_texts(model_spec, [query], tenant_id=tenant_id)[0])
            mat = np.array([segments[i].vector for i in idxs])
            vec_scores[idxs] = mat @ qv / (np.linalg.norm(mat, axis=1) * np.linalg.norm(qv) + 1e-9)
    # 3. 关键词分数
    if method in ("full_text_search", "hybrid_search"):
        kw_scores = np.array(bm25_scores(query, [seg.content for seg in segments]))
    # 4. 融合：BM25 的分数没有上限，先除以最大值归一化到 [0,1]，才能和余弦相似度相加
    final = vec_scores if method == "semantic_search" else \
            _normalize(kw_scores) if method == "full_text_search" else \
            vector_weight * vec_scores + (1 - vector_weight) * _normalize(kw_scores)
    # 5. 按分数排序，应用阈值，父子模式下按父块去重，取前 top_k 个
    for i in np.argsort(-final):
        seg = segments[i]
        content = seg.parent_content or seg.content          # 父子模式：返回父块
        if seg.parent_content and content in seen_parents:   # 多个子块命中了同一个父块：只返回一次
            continue
        ...
```

**为什么要按 embedding 模型分组？** 不同知识库可能使用不同的 embedding 模型，它们生成的向量**不在同一个空间里**，不能互相比较。用 A 模型生成的查询向量，去和 B 模型生成的分段向量计算相似度，结果毫无意义。所以每个模型都要单独为查询生成一次向量。

**存储的取舍**：向量以 JSON 的形式存在 `segments.vector` 列里，检索时全部加载到内存，用 numpy 计算。这是 O(n) 的暴力检索，几千到几万个分段都没有问题。规模再大，就该换成向量库（pgvector 的 HNSW 索引、Qdrant 等），用近似最近邻（ANN）算法做到 O(log n)。Dify 的 `vector_factory.py` 就是为了能方便地做这种切换。

### 23.3.3 知识检索节点

```python
# backend/app/workflow/nodes/knowledge.py
class KnowledgeRetrievalNodeData(BaseNodeData):
    query_variable_selector: list[str] = []
    dataset_ids: list[str] = []
    retrieval: RetrievalConfig = RetrievalConfig()     # method / top_k / score_threshold / vector_weight

class KnowledgeRetrievalNode(Node):
    def _run(self):
        query = str(self.pool.get(self.data.query_variable_selector) or "")
        hits = retrieve(self.data.dataset_ids, query, tenant_id=self.ctx.tenant_id, ...)
        return NodeRunResult(inputs={"query": query}, outputs={"result": [h.to_dict() for h in hits]})
```

输出的结构和 Dify 一致：`{content, title, score, metadata}`。

### 23.3.4 LLM 节点的上下文注入

```python
# backend/app/workflow/nodes/llm.py
class ContextConfig(BaseModel):
    enabled: bool = False
    variable_selector: list[str] = []

def build_messages(self):
    context = ""
    if self.data.context.enabled and self.data.context.variable_selector:
        value = self.pool.get(self.data.context.variable_selector)
        context = format_context(value) if isinstance(value, list) else str(value or "")
    rendered = [Message(p.role, self.pool.render(p.text.replace("{{#context#}}", context)))
                for p in self.data.prompt_template]
    ...

def format_context(results):                       # backend/app/rag/index.py
    return "\n\n".join(f"[{i + 1}] {r.get('title', '')}\n{r.get('content', '')}" for i, r in enumerate(results))
```

给每段加上编号 `[1] [2]`，模型在回答时就可以引用来源（“根据 [2]……”）。

为什么 `{{#context#}}` 要单独处理，而不是走正常的变量模板？因为它没有 `node.var` 这种两段式结构，不符合变量模板的正则（第 5 章），所以必须在模板渲染之前先替换掉。

### 23.3.5 召回测试

`POST /api/datasets/{id}/retrieve` 对应 Dify 的“召回测试”（hit testing）页面：输入一个问题，查看检索结果，以及每个结果的向量分数、关键词分数和融合后的总分。**调整分段和检索参数时，必须靠它来观察效果。**

## 23.4 运行与验证

```bash
cd code/mini-dify && git checkout v0.5 && cd backend
uv run pytest -q tests/test_rag.py -k "retrieve or parent"
```

- 三种检索方法下，问“怎么退款？”时排第一的都是“第四章 退款政策”那一段；
- 父子模式下，问“超过七天需要什么”，返回的是**完整的父段落**（以“第四章”开头），而不只是命中的子块；
- RAG 工作流 `开始 → 知识检索 → LLM(context) → 结束` 中，LLM 节点 `process_data.prompts[0]` 里包含“七天内可以无理由退款”，证明检索结果确实被注入到了提示词里。

**在 UI 中搭一个 RAG Chatflow**：

1. 新建 Chatflow；在开始和 LLM 之间插入一个“知识检索”节点（先选中开始节点，再点击“知识检索”）；
2. 知识检索：查询变量选 `系统变量.query`，勾选知识库；
3. LLM：“上下文”选择“知识检索.result”；SYSTEM 提示词写：`根据以下资料回答问题，资料里没有就说不知道：\n{{#context#}}`；
4. 预览，提问。在追踪里展开 LLM 节点，查看 prompts，确认资料已经注入。换成真实模型后，就是一个能用的知识库问答机器人了。

写作时用 UI 做召回测试的结果：问“怎么退款”，第一条命中“第三章 退款政策……”，总分 0.42 = 0.7 × 向量 0.17 + 0.3 × 关键词（归一化后为 1.0）。这里可以看到，mock 的哈希向量语义能力很弱，主要靠关键词把正确答案排到了第一，这正好说明了混合检索的价值。

## 23.5 练习

1. **巩固**：BM25 的分数为什么要先归一化，才能和余弦相似度相加？如果不做归一化会怎样？
2. **扩展**：实现 **RRF**（Reciprocal Rank Fusion）融合：`score = Σ 1/(k + rank_i)`，k 取 60。它只用排名、不用分数，所以不需要归一化。和加权融合比较一下，各有什么优缺点？
3. **读源码**：读 Dify 的 `DatasetRetrieval.single_retrieve`，说说路由模式下 LLM 是怎么从多个知识库中选出一个的（提示：把知识库包装成工具，让模型去选）。

## 23.6 延伸阅读

- 论文：*Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*（Cormack et al., 2009）
- `api/core/rag/retrieval/router/`：Dify 的多知识库路由
- pgvector 文档：HNSW 和 IVFFlat 索引
