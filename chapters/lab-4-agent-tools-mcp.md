# Lab 4：mini-dify v0.4 —— 工具、Agent、MCP

> 目标：内置工具 + OpenAPI 自定义工具 + 工作流即工具 + MCP 工具；Function Calling 和 ReAct 两种 Agent；聊天 Playground 支持 Agent 模式；工作流中的 Agent 节点和工具节点；MCP 客户端和 MCP Server。
> 起点 `v0.3`，终点 `v0.4`。

## 构建顺序

| 步骤 | 文件 | 章节 |
|---|---|---|
| 1 | `app/llm/mock.py`：学会“调用工具”和 ReAct；顺带加入哈希向量（v0.5 要用） | 18 |
| 2 | `app/tools/base.py`、`builtin.py`（时间、计算器、网页抓取） | 19 |
| 3 | `app/tools/api_tool.py`（OpenAPI 解析） | 19 |
| 4 | `app/mcp/client.py`（stdio + HTTP）→ `app/tools/mcp_tool.py` | 20 |
| 5 | `app/tools/workflow_tool.py`、`manager.py` | 19 |
| 6 | `app/agent/prompts.py`、`runner.py`（两种 Runner） | 18 |
| 7 | `app/workflow/nodes/agent.py`（Agent 节点、工具节点）+ `NodeRunAgentLog` 事件 + 转换器支持 `agent_log` | 21 |
| 8 | `app/api/chat.py` 的 Agent 模式（`agent_thought` / `agent_message` 事件） | 18 |
| 9 | `app/api/tools.py`、`app/mcp/server.py`、`models.py` 新增 `ToolProviderRecord` | 19、20 |
| 10 | `examples/mcp_demo_server.py` | 20 |
| 11 | 前端：`lib/useTools.ts`、`components/ToolPicker.tsx`、`pages/ToolsPage.tsx`、ChatPage 的 Agent 模式、Agent/工具两种节点的面板 | 19、21 |

## 演示脚本

```bash
cd code/mini-dify && git checkout v0.4
# 启动后端和前端
```

1. **工具页** → “＋ MCP Server” → stdio：`python3` + `../examples/mcp_demo_server.py` → 保存。点击 `get_weather`，输入“北京”，返回 `北京：晴 26°C`；
2. **聊天 Playground** → 勾选“计算器”和“get_weather” → 问“帮我算 (12+8)*3”，再问“查一下 get_weather 上海”。每条回答上方会显示 🔧 工具调用和 👀 观察结果；
3. 把策略切换成 ReAct，再问一次，回答相同，但思考过程是文字形式的；
4. **工作流**：开始 → Agent（勾选计算器，问题写“请计算 99*99”）→ 结束 → 运行。在追踪里展开 Agent 节点，查看 steps；
5. **工作流即工具**：发布一个 Workflow 应用，它会出现在工具页的 workflow 分组里，可以被另一个应用的 Agent 调用；
6. **MCP Server**：`curl -X POST localhost:5001/mcp/<app_id> -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'`（v0.4 没有鉴权；v1.0 需要加上 `Authorization: Bearer <API Key>`）。

## 换成真实模型

v0.4 还没有工作空间凭证设置（v1.0 才加），所以通过环境变量配置：

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 OPENAI_API_KEY=ollama uv run uvicorn app.main:app --port 5001
```

然后在聊天 Playground 的模型框中填 `openai/qwen2.5:7b`（Ollama 上的小模型基本都支持工具调用，0.5B 的版本也能用，第 18 章有实测记录）。

## 验收清单

- [ ] `uv run pytest -q`：28 个测试通过（v0.4 的数量）
- [ ] 两种 Agent 策略都能正确完成计算器任务
- [ ] OpenAPI 工具在接口不可达时返回错误结果，而不是 500
- [ ] stdio 方式的 MCP Server 能添加，也能调用
- [ ] 工作流中 Agent 节点的追踪包含 steps；Answer 节点能流式输出 Agent 的回答
- [ ] 已发布的工作流可以作为工具被调用，也可以通过 MCP 协议被调用

## 写作时踩到的坑（真实记录）

1. **计算器精度**：`:g` 格式把 7006652 变成了 `7.00665e+06`，模型又把它“还原”成了错误的 7,006,650。改为整数原样输出（第 18 章）。
2. **ReAct 示例里的嵌套代码块**：写书时，Markdown 代码块里又包含了 ```，导致渲染错乱。外层改用 `~~~~` 就好了。这和 ReAct 本身无关，但如果你要在文档里展示 ReAct 提示词，迟早会遇到。
3. **v1.0 才补上的两个安全问题**（写第 19、20 章时对照 Dify 发现的）：工作流即工具没有调用深度限制，可能无限递归；stdio MCP 在多租户场景下等于允许用户在服务器上执行任意命令。这两个问题都在 v1.0 里修复了，并加了回归测试。**如果你基于 v0.4 做实验，要清楚这两个风险。**
