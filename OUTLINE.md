# 《从 Dify 到 Mini-Dify：从零构建 AI 平台与 Agent Workflow》

> 状态：全部章节已完成，正文见 [README.md](README.md)。本文件是最初的大纲，保留作参考。

> 参照仓库：`langgenius/dify`（main @ f3ecedab56）
> 读者目标：读完后能从零写出一个前后端可运行的 AI 平台 / Agent Workflow 编排系统（mini-dify）。
> 写作方式：每章 = 概念 → Dify 源码导读 → 从零实现 → 运行验证 → 练习。

## 贯穿全书的项目：mini-dify

| 版本 | 能力 | 对应章节 |
|---|---|---|
| v0.1 | 流式聊天（LLM + SSE + 聊天 UI） | Part II |
| v0.2 | DAG 工作流引擎（变量池、条件分支、并行） | Part III |
| v0.3 | 可视化画布编排 + 运行可视化 | Part IV |
| v0.4 | Agent 节点 + 工具 + MCP | Part V |
| v0.5 | 知识库 + 检索节点（RAG） | Part VI |
| v1.0 | 发布为 API、异步队列、Docker Compose 一键启动 | Part VII |

默认技术栈（与 Dify 保持概念一致、复杂度降一档）：
- 后端：Python 3.12 + FastAPI + SQLAlchemy + SQLite/Postgres + Redis(可选)
- 前端：React + Vite + TypeScript + @xyflow/react（React Flow）+ Zustand
- 模型：任意 OpenAI 兼容接口（OpenAI / DeepSeek / 通义 / Ollama 本地）

---

## Part 0 导读

### 第 0 章 本书怎么读
- 什么是 AIP（AI Platform）：模型层 / 编排层 / 应用层 / 运营层
- mini-dify 最终效果演示与代码结构
- 环境准备：uv、pnpm、Docker、一个 OpenAI 兼容的 API Key
- 如何对照阅读 Dify 源码（附录 A 源码地图）

## Part I 全景：读懂 Dify（浅）

### 第 1 章 LLM 应用的五种形态
- Completion / Chat / Agent Chat / Workflow / Chatflow（Advanced Chat）
- 源码：`api/core/app/apps/{completion,chat,agent_chat,workflow,advanced_chat}`
- 为什么最后都收敛到“图”

### 第 2 章 Dify 架构鸟瞰
- api（Flask + Celery）、web（Next.js）、Postgres、Redis、向量库、plugin daemon、sandbox、dify-agent
- 目录地图：`controllers → services → core → models`
- 动手：`docker/` 下用 Docker Compose 跑起 Dify，搭一个 3 节点 workflow

### 第 3 章 一次 Workflow 运行的完整生命周期 ★
- 前端点击“运行” → `controllers/console/app/workflow.py`
- `services/app_generate_service.py` → `core/app/apps/workflow/app_generator.py`
- `app_runner.py` → `core/workflow/workflow_entry.py` → GraphEngine（`graphon` 包）
- 事件 → `app_queue_manager.py` → `generate_task_pipeline.py` → SSE（`libs/helper.py: compact_generate_response`）
- 前端 `web/app/components/workflow/hooks/use-workflow-run-event/` 消费事件
- 产出：一张时序图，后面所有章节都是在拆这张图

## Part II 地基：模型调用层 → mini-dify v0.1

### 第 4 章 模型抽象：Provider / Model / Credential
- 源码：`core/provider_manager.py`、`core/model_manager.py`、`core/plugin/`（模型即插件）
- 设计：统一 `invoke_llm(messages, tools, stream)` 接口；凭证加密存储
- 实现：mini-dify 的 `ModelProvider` 抽象 + OpenAI 兼容实现

### 第 5 章 Prompt、模板与记忆
- 源码：`core/prompt/`（simple/advanced prompt transform）、`core/memory/token_buffer_memory.py`
- Jinja2 / `{{#node.var#}}` 变量模板、Token 窗口截断
- 实现：Prompt 渲染器 + 会话记忆

### 第 6 章 流式输出与事件协议
- SSE 协议细节；为什么不用 WebSocket
- Dify 的事件类型：`workflow_started / node_started / text_chunk / node_finished / workflow_finished / error / ping`
- 实现：FastAPI `StreamingResponse` + 前端 `fetch` 流式读取

### Lab 1：mini-dify v0.1 —— 能流式对话的聊天应用（前后端可运行）

## Part III 核心：Workflow 引擎 → mini-dify v0.2

### 第 7 章 Workflow 的数据模型与 DSL
- graph = `{nodes: [...], edges: [...]}`；节点 `data`、边 `sourceHandle`
- 草稿 vs 发布版本：`models/workflow.py`、`services/workflow_service.py`
- DSL 导入导出：`services/app_dsl_service.py`
- 实现：Pydantic 定义 Graph / Node / Edge，YAML 导入导出

### 第 8 章 变量池（VariablePool）★
- selector：`[node_id, var_name]`；系统变量 `sys.*`、环境变量、会话变量
- 源码：`core/workflow/variable_pool_initializer.py`、`system_variables.py`、`environment_variables.py`
- 实现：类型化变量池 + 模板引用解析

### 第 9 章 图执行引擎（Graph Engine）★★
- 运行时图与入口节点：`graphon/graph/graph.py`、`api/core/workflow/node_factory.py`
- Ready Queue + Worker 池；并行分支；条件边与“未选中分支跳过传播”
- 事件驱动：引擎只产出事件，上层负责持久化与推送（Layer 模式）
- 命令通道：停止/暂停（`core/app/apps/workflow/command_channels.py`）
- 实现：约 300 行的 DAG 引擎（含并行、分支、事件流）

### 第 10 章 节点体系
- Node 基类：输入映射 → `_run()` → 输出 / 事件
- 基础节点：Start、End、Answer、LLM、IF/ELSE、Code、HTTP Request、Template、Variable Aggregator
- 源码：`core/workflow/llm_node.py`、`core/workflow/nodes/`、`graphon` 内置节点
- 实现：mini-dify 的节点注册表 + 6 个节点

### 第 11 章 容器节点：Iteration 与 Loop
- 子图、局部变量作用域、并发迭代
- 实现：Iteration 节点

### 第 12 章 健壮性：错误、重试、超时、人工介入
- 节点级错误策略（fail / default value / fail branch）、重试
- Human Input 暂停与恢复：`core/workflow/human_input_*.py`
- 实现：错误分支 + 重试 + 停止

### 第 13 章 持久化与可观测
- WorkflowRun / NodeExecution 记录：`core/app/workflow/layers/persistence`、`core/repositories/`
- Trace：`core/ops/`（Langfuse / LangSmith 等）
- 实现：运行记录表 + 运行历史 API

### Lab 2：mini-dify v0.2 —— 用 API 提交 JSON 图并流式看到每个节点执行

## Part IV 前端：可视化编排画布 → mini-dify v0.3

### 第 14 章 React Flow 画布
- 自定义节点 / 边 / Handle；Block Selector 拖入节点
- 源码：`web/app/components/workflow/{index.tsx,nodes,custom-edge.tsx,block-selector}`

### 第 15 章 编辑器状态管理
- Zustand store：`workflow/store/`；草稿自动同步 `hooks/use-nodes-sync-draft.ts`
- Undo/Redo：`workflow-history-store.ts`

### 第 16 章 节点配置面板与变量选择器 ★
- 上游可用变量计算：`hooks/use-nodes-available-var-list.ts`
- 每个节点 = 画布组件 + 面板组件 + 默认值 + 校验（`hooks/use-checklist.ts`）

### 第 17 章 运行与调试体验
- SSE 事件 → 节点状态着色、运行面板、Tracing 视图
- 单节点调试、变量检查器：`workflow/variable-inspect/`

### Lab 3：mini-dify v0.3 —— 拖拽编排 + 一键运行 + 节点状态实时高亮

## Part V Agent → mini-dify v0.4

### 第 18 章 Agent 原理：ReAct 与 Function Calling
- 源码：`core/agent/cot_agent_runner.py`、`fc_agent_runner.py`、`output_parser/`
- 循环：思考 → 调工具 → 观察 → 直到 final answer；最大迭代与 token 控制

### 第 19 章 工具体系
- 内置工具 / OpenAPI 自定义工具 / Workflow-as-Tool / 插件工具 / MCP 工具
- 源码：`core/tools/{tool_manager.py,tool_engine.py,custom_tool,workflow_as_tool,mcp_tool}`
- 实现：Tool 抽象 + JSON Schema + 3 个内置工具

### 第 20 章 MCP 协议
- 源码：`core/mcp/{client,server,session}`
- 实现：mini-dify 接入一个 MCP Server；把 workflow 暴露为 MCP Server

### 第 21 章 Agent 在 Workflow 中 & 新一代 Agent 运行时
- Agent 节点与 Agent Strategy：`core/workflow/nodes/agent`、`agent_v2`
- `dify-agent/`：agenton 的 Layer / Compositor 组合式架构、运行时调度
- 实现：Agent 节点

### Lab 4：mini-dify v0.4 —— 工作流里的 Agent 节点自动调用工具和 MCP

## Part VI RAG 知识库 → mini-dify v0.5

### 第 22 章 索引管线
- 源码：`core/rag/{extractor,cleaner,splitter,embedding,index_processor}`
- 父子分段、元数据

### 第 23 章 检索与重排
- 向量 / 全文 / 混合检索、Rerank：`core/rag/{retrieval,rerank}`
- Knowledge Retrieval 节点：`core/workflow/nodes/knowledge_retrieval`

### Lab 5：mini-dify v0.5 —— 上传文档、建索引、在工作流中检索问答

## Part VII 平台化（深）→ mini-dify v1.0

### 第 24 章 多租户、发布与开放 API
- Tenant / Account / App / API Key；console API vs service API vs web API（`controllers/`）

### 第 25 章 异步执行与横向扩展
- Celery 队列、Redis 命令通道、长任务恢复：`tasks/`、`core/app/apps/execution_coordinator.py`

### 第 26 章 插件系统
- plugin daemon、反向调用：`core/plugin/`

### 第 27 章 安全
- 代码沙箱、SSRF 代理（`core/helper/ssrf_proxy.py`）、凭证加密、权限（`core/rbac`）

### 第 28 章 触发器
- Webhook / Schedule / Plugin Trigger：`core/workflow/nodes/trigger_*`、`core/trigger`

### Lab 6：mini-dify v1.0 —— 发布 Workflow 为 API，Docker Compose 一键启动

## 附录
- A. 源码阅读地图：概念 → Dify 文件路径
- B. 术语表
- C. 横向对比：Dify / LangGraph / n8n / Coze
- D. 练习参考答案
