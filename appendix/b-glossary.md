# 附录 B 术语表

| 术语 | 英文 | 解释 | 章 |
|---|---|---|---|
| AI 平台 | AIP, AI Platform | 托管 LLM 应用的平台：模型接入、编排、知识库、工具、发布、运营 | 0 |
| 应用形态 | App Mode | completion / chat / agent-chat / workflow / advanced-chat（Chatflow）…… | 1 |
| Chatflow | advanced-chat | 带会话记忆和 Answer 节点的工作流 | 1 |
| 流式输出 | Streaming | 边生成边推送；首字延迟（TTFT）是关键体验指标 | 6 |
| SSE | Server-Sent Events | 基于 HTTP 的单向事件流，`data: ...\n\n` | 6 |
| Provider | Model Provider | 模型供应商的适配层，屏蔽各家 API 的差异 | 4 |
| ModelInstance | — | “某个租户的某个模型”，凭证已绑定在里面 | 4 |
| Token 预算 | Token Budget | 给历史等可变内容分配的上下文空间 | 5 |
| DSL | Domain Specific Language | 应用导出的 YAML 文件 | 7 |
| 草稿 / 发布 | Draft / Published | 可编辑的版本 vs 线上运行的冻结版本 | 7 |
| 乐观锁 | Optimistic Locking | 提交时带上版本号（hash），冲突时拒绝 | 7, 15 |
| 选择器 | Selector | 变量地址 `[node_id, name, *path]`，模板里写作 `{{#a.b#}}` | 8 |
| 变量池 | Variable Pool | 一次运行的共享存储；节点从中读、引擎往里写 | 8 |
| 系统变量 | System Variables | `sys.query`、`sys.user_id`、`sys.conversation_id`…… | 8 |
| 环境变量 | Environment Variables | 随工作流保存的只读配置，`env.*` | 8 |
| 会话变量 | Conversation Variables | Chatflow 中跨轮次保存的变量，`conversation.*` | 8 |
| 边状态 | Edge State | UNKNOWN / TAKEN / SKIPPED | 9 |
| 就绪 | Ready | 入边全部有了结论，并且至少有一条是 TAKEN | 9 |
| 跳过传播 | Skip Propagation | 没被选中的分支一路向下标记为 SKIPPED，直到遇到汇合节点 | 9 |
| 执行类型 | Execution Type | executable / branch / response / container / root | 9 |
| 命令通道 | Command Channel | 外部向引擎发送 Abort 等命令的消息通道 | 9, 25 |
| Layer | Graph Engine Layer | 观察引擎事件的插件：持久化、执行限制、追踪…… | 9, 13 |
| 回复流 | Response Stream | 按 Answer 模板的顺序流式输出各个来源的内容 | 10 |
| 容器节点 | Container Node | 内含子图的节点：迭代、循环 | 11 |
| 执行帧 | Execution Frame | graphon 为子图的每一轮创建的独立执行上下文 | 11 |
| 错误策略 | Error Strategy | 终止 / 默认值（default-value）/ 异常分支（fail-branch） | 12 |
| 部分成功 | partial-succeeded | 有节点以 exception 状态结束，但整个运行完成了 | 12 |
| 人在回路 | HITL, Human In The Loop | 工作流暂停，等人来输入或审批 | 12 |
| 单步调试 | Single Step Run | 只运行一个节点，输入由用户提供 | 17 |
| Agent | — | 由模型决定控制流的“思考 → 调用工具 → 观察”循环 | 18 |
| Function Calling | Tool Calling | 模型原生返回结构化的工具调用 | 18 |
| ReAct | Reason + Act | 用提示词约定 Thought / Action / Observation 文本格式 | 18 |
| Scratchpad | — | ReAct 中累积的推理记录 | 18 |
| 工具提供方 | Tool Provider | 一组共享凭证的工具 | 19 |
| MCP | Model Context Protocol | 工具接入的开放协议，基于 JSON-RPC 2.0 | 20 |
| Streamable HTTP | — | MCP 的 HTTP 传输：POST 发送，响应可以是 JSON 或 SSE | 20 |
| 层组合 | Layer Composition | agenton 用可组合的层来构建 Agent | 21 |
| RAG | Retrieval-Augmented Generation | 先检索、再把检索结果放进提示词生成回答 | 22 |
| 分段 | Chunking | 把文档切成适合检索的片段 | 22 |
| 重叠 | Chunk Overlap | 相邻分段共享的部分，防止关键信息被切断 | 22 |
| 父子分段 | Parent-Child Chunking | 用小块匹配、返回大块 | 22 |
| Embedding | 向量化 | 把文本映射成向量，语义相近的文本向量也相近 | 22 |
| BM25 | — | 经典的关键词相关性打分算法 | 23 |
| 混合检索 | Hybrid Search | 向量检索 + 全文检索，再融合分数 | 23 |
| Rerank | 重排序 | 用 cross-encoder 对候选结果重新打分 | 23 |
| RRF | Reciprocal Rank Fusion | 基于排名的融合方法 | 23 |
| 召回测试 | Hit Testing | 输入问题，查看检索结果和分数 | 23 |
| 租户 | Tenant / Workspace | 数据隔离的单位 | 24 |
| RBAC | Role-Based Access Control | 基于角色的访问控制 | 24 |
| Service API | — | 面向开发者的 `/v1` 接口，用 App Key 鉴权 | 24 |
| WebApp | — | 分享链接背后的公开页面 | 24 |
| 事件总线 | Event Bus | 执行端 → API 端的事件通道（Queue / Redis Stream） | 25 |
| acks_late | — | Celery 任务执行完才确认，任务需要幂等 | 25 |
| 反向调用 | Backwards Invocation | 插件回调平台的能力（模型、工具……） | 26 |
| SSRF | Server-Side Request Forgery | 诱使服务器访问内网资源 | 27 |
| 沙箱 | Sandbox | 隔离执行不受信任的代码 | 27 |
| 提示词注入 | Prompt Injection | 数据里夹带的指令劫持了模型的行为 | 27 |
| SKIP LOCKED | — | `SELECT ... FOR UPDATE SKIP LOCKED`，多个消费者安全地领取任务 | 28 |
