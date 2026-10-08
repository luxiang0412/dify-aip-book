# 从 Dify 到 Mini-Dify：从零构建 AI 平台与 Agent Workflow

> 参照仓库：`langgenius/dify` @ `f3ecedab56`（图引擎 `graphon==0.7.0`）
> 目标：读完后，你能从零写出一个前后端都能运行的 AI 平台 / Agent Workflow 编排系统。
> 配套代码：[github.com/luxiang0412/mini-dify](https://github.com/luxiang0412/mini-dify)（tag `v0.1` → `v1.0`，每个版本都能运行，并有测试）。书中的 `code/mini-dify/` 指的就是这个仓库：`git clone https://github.com/luxiang0412/mini-dify code/mini-dify`

## 怎么读

先看 [第 0 章](chapters/00-how-to-read.md)。核心主线是 **3 → 7 → 8 → 9 → 10** 这几章（★ 越多越重要）；其余章节可以按兴趣挑着读。每个 Part 结尾的 Lab 带你把 mini-dify 升级到下一个版本。

```bash
cd code/mini-dify && git checkout v0.2     # 切到某一版
git diff v0.1 v0.2 --stat                  # 看这一版改了什么
```

## 目录

**Part 0 导读**
- [第 0 章 本书怎么读](chapters/00-how-to-read.md)

**Part I 全景（浅）**
- [第 1 章 LLM 应用的五种形态](chapters/01-five-app-forms.md)
- [第 2 章 Dify 架构鸟瞰](chapters/02-dify-architecture.md)
- [第 3 章 一次 Workflow 运行的完整生命周期 ★](chapters/03-one-workflow-run.md)

**Part II 模型层 → v0.1**
- [第 4 章 模型抽象：Provider / Model / Credential](chapters/04-model-abstraction.md)
- [第 5 章 Prompt、模板与记忆](chapters/05-prompt-and-memory.md)
- [第 6 章 流式输出与事件协议](chapters/06-streaming-sse.md)
- [Lab 1：流式聊天应用](chapters/lab-1-streaming-chat.md)

**Part III 工作流引擎 → v0.2**
- [第 7 章 Workflow 的数据模型与 DSL](chapters/07-workflow-dsl.md)
- [第 8 章 变量池 ★](chapters/08-variable-pool.md)
- [第 9 章 图执行引擎 ★★](chapters/09-graph-engine.md)
- [第 10 章 节点体系](chapters/10-nodes.md)
- [第 11 章 容器节点：Iteration 与 Loop](chapters/11-iteration.md)
- [第 12 章 健壮性：错误、重试、超时、停止、人工介入](chapters/12-robustness.md)
- [第 13 章 持久化与可观测](chapters/13-persistence-observability.md)
- [Lab 2：DAG 工作流引擎 + 控制台 API](chapters/lab-2-workflow-engine.md)

**Part IV 前端画布 → v0.3**
- [第 14 章 React Flow 画布](chapters/14-react-flow-canvas.md)
- [第 15 章 编辑器状态管理](chapters/15-editor-state.md)
- [第 16 章 节点配置面板与变量选择器 ★](chapters/16-panels-and-variables.md)
- [第 17 章 运行与调试体验](chapters/17-run-and-debug.md)
- [Lab 3：可视化编排 + 实时追踪](chapters/lab-3-visual-editor.md)

**Part V Agent → v0.4**
- [第 18 章 Agent 原理：ReAct 与 Function Calling](chapters/18-agent-principles.md)
- [第 19 章 工具体系](chapters/19-tools.md)
- [第 20 章 MCP 协议](chapters/20-mcp.md)
- [第 21 章 Agent 在 Workflow 中 & 新一代 Agent 运行时](chapters/21-agent-in-workflow.md)
- [Lab 4：工具、Agent、MCP](chapters/lab-4-agent-tools-mcp.md)

**Part VI RAG → v0.5**
- [第 22 章 索引管线](chapters/22-indexing-pipeline.md)
- [第 23 章 检索、融合与上下文注入](chapters/23-retrieval.md)
- [Lab 5：知识库 RAG](chapters/lab-5-rag.md)

**Part VII 平台化（深）→ v1.0**
- [第 24 章 多租户、权限、发布与开放 API](chapters/24-tenancy-and-api.md)
- [第 25 章 异步执行与横向扩展](chapters/25-async-and-scale.md)
- [第 26 章 插件系统](chapters/26-plugins.md)
- [第 27 章 安全](chapters/27-security.md)
- [第 28 章 触发器与部署](chapters/28-triggers-and-deploy.md)
- [Lab 6：平台化与一键部署](chapters/lab-6-platform.md)

**附录**
- [A 源码阅读地图（概念 → Dify → mini-dify）](appendix/a-source-map.md)
- [B 术语表](appendix/b-glossary.md)
- [C 横向对比：Dify / LangGraph / n8n / Coze](appendix/c-comparison.md)
- [D 练习参考答案](appendix/d-answers.md)

## 一分钟跑起来

```bash
cd code/mini-dify
# 方式一：Docker（v1.0）
cd docker && docker compose up -d --build        # → http://localhost:8080，注册账号即可使用
# 方式二：本地开发
cd backend && cp .env.example .env && uv sync && uv run uvicorn app.main:app --reload --port 5001
cd frontend && npm install && npm run dev        # → http://localhost:3000
```

默认使用内置的 `mock/echo` 模型，**不需要任何 API Key**。想换成真实模型：在“设置”里填写 OpenAI 兼容接口的地址和 Key，然后把节点里的模型 provider 改成 `openai`。

## 本书是怎么验证的

- 后端测试：v1.0 共 53 个（加上 Redis 相关测试），每个版本的 tag 都在测试全部通过后才提交；
- 每个版本都用无头 Chrome 实际操作过界面，书中的截图就来自这些操作；
- v1.0 在 Docker Compose 环境（Postgres + Redis + Celery）里做过端到端验证：登录、运行、发布、Service API、分享页、知识库、Webhook、MCP；
- 真实模型（Ollama qwen2.5:0.5b）验证过流式对话和 Function Calling；
- 书中各章的“踩坑记录”只写实际遇到的问题；写代码时自查发现、在运行前就修掉的隐患，会单独注明。

## 本地预览与发布

```bash
npm install
npm run dev               # 本地预览 http://localhost:5173/dify-aip-book/
./scripts/deploy.sh       # 构建并发布到 gh-pages 分支（GitHub Pages）
```
