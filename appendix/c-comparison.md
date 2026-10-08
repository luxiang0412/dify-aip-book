# 附录 C 横向对比：Dify / LangGraph / n8n / Coze

> 目的：帮你把本书学到的概念放到更大的版图里。各项目都在快速迭代，以下是**架构层面**的比较，具体功能以各自的官方文档为准。

## 定位

| | Dify | LangGraph | n8n | Coze（扣子） |
|---|---|---|---|---|
| 形态 | 开源 LLM 应用平台（可视化 + API） | 开源**代码库**（Python/JS） | 开源工作流自动化平台 | 字节跳动的 Agent 平台（也有开源的 Coze Studio） |
| 主要用户 | 产品、业务、开发者 | 开发者 | 运营、自动化工程师 | 业务人员、开发者 |
| 编排方式 | 画布 DAG + 容器节点 | 用代码定义状态图（**允许有环**） | 画布 DAG | 画布工作流 + Bot 配置 |
| LLM 原生程度 | 高（模型、提示词、RAG、Agent 都是一等公民） | 高 | 中（AI 节点是众多节点中的一类） | 高 |

## 引擎模型对比

| 维度 | Dify（graphon） | LangGraph | n8n |
|---|---|---|---|
| 图 | DAG（循环用容器节点实现） | 有向图，可以有环；节点之间通过共享的 **State** 通信 | DAG，数据沿着边以 items 数组的形式传递 |
| 数据传递 | **共享变量池** + selector | **共享 State** + reducer（定义各节点的更新如何合并） | **沿边传递**（上游节点的输出就是下游节点的输入） |
| 分支 | 分支节点 + 边状态 + 跳过传播 | 条件边函数返回下一个节点 | IF / Switch 节点 |
| 并行 | 自动（就绪即执行） | 同一个 superstep 内的节点并行（Pregel / BSP 模型） | 分支并行执行（取决于执行模式） |
| 暂停 / 恢复 | 人工输入节点 + 运行时状态序列化 | **Checkpointer** 在每一步保存 State，`interrupt()` 支持人在回路，可以“时间旅行”回到任意一步 | Wait 节点 |
| 流式 | 节点事件 + 回复流排序 | 多种 stream mode（values / updates / messages / events） | 较弱 |

**值得注意的几点**：

- LangGraph 允许有环，所以“Agent 循环”可以直接画成图里的一个环（模型节点 ⇄ 工具节点）。Dify 则把 Agent 封装成一个节点，外层保持 DAG。这是**可控性和表达力之间的不同取舍**。
- LangGraph 的 checkpointer 在每个 superstep 都持久化 State，所以暂停、恢复、回放天然就支持。Dify 只在需要暂停时才做序列化（第 12 章）。对应到 mini-dify：如果想让引擎支持这些能力，第 9 章的练习 2 就是第一步。
- n8n 的“数据沿边传递”是传统工作流自动化的经典模型（每个节点处理一个 items 数组）。它适合 ETL 一类的场景，但“引用三步之前的结果”就比较麻烦，这也是第 8 章选择变量池的原因。

## 和本书概念的对应

| 本书概念 | Dify | LangGraph | n8n |
|---|---|---|---|
| 变量池 | VariablePool | State | items + `$node["X"].json` 表达式 |
| 节点就绪规则 | 边状态 | superstep：上一步写过的 channel 会触发订阅它的节点 | 上游执行完成 |
| Layer | GraphEngineLayer | callbacks / checkpointer | — |
| 工具 | Tool + Provider | `@tool` + ToolNode | 各种集成节点 |
| MCP | 客户端 + 服务端 | 通过适配器（langchain-mcp-adapters） | MCP 节点 |
| 发布为 API | Service API | LangGraph Platform / Server | Webhook 触发器 |

## 选型建议

- 想要**开箱即用的平台**，给业务人员搭建 AI 应用：Dify / Coze；
- 想在**自己的代码里**构建复杂的 Agent，需要最大的灵活性：LangGraph；
- 主要做**跨 SaaS 的自动化**，AI 只是其中一环：n8n；
- 想**理解所有这些系统**：自己写一个，也就是这本书做的事。
