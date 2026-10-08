# 附录 A 源码阅读地图：概念 → Dify 源码 → mini-dify

> Dify 基于 commit `f3ecedab56`；graphon 基于 `0.7.0`（`pip download graphon==0.7.0`）。mini-dify 基于 tag `v1.0`。

## 应用与请求链路

| 概念 | Dify | mini-dify | 章 |
|---|---|---|---|
| 应用类型枚举 | `api/models/model.py:387` `AppMode` | `App.mode` | 1 |
| 按类型分发 | `api/services/app_generate_service.py:101` | `apps/generator.py` | 1, 3 |
| 运行草稿接口 | `api/controllers/console/app/workflow.py:1149` | `api/apps.py` `run_draft` | 3 |
| Generator：开线程、队列 | `api/core/app/apps/workflow/app_generator.py:319`（`_generate`）、`:614`（`_generate_worker`） | `apps/generator.py` | 3, 25 |
| 队列与 ping | `api/core/app/apps/base_app_queue_manager.py:76` `listen` | `tasks/bus.py` | 3, 25 |
| Runner | `api/core/app/apps/workflow/app_runner.py:81` | `generator.execute` | 3 |
| 引擎事件 → 队列事件 | `api/core/app/apps/workflow_app_runner.py:467` `_handle_event` | `apps/converter.py` | 3 |
| 队列事件 → SSE | `api/core/app/apps/workflow/generate_task_pipeline.py` | `apps/converter.py` | 3, 6 |
| SSE 事件名 | `api/core/app/entities/task_entities.py:62` `StreamEvent` | `converter.py` | 6 |
| SSE 序列化 | `api/core/app/apps/base_app_generator.py:313`；`api/libs/helper.py:416` | `sse.py` | 6 |
| 停止 | `workflow.py:1195`；`base_app_queue_manager.py:189`；`apps/workflow/command_channels.py` | `tasks/channels.py` | 3, 25 |

## 模型、提示词与记忆

| 概念 | Dify | mini-dify | 章 |
|---|---|---|---|
| 消息、工具、流式片段 | `graphon/model_runtime/entities/message_entities.py`、`llm_entities.py` | `llm/entities.py` | 4 |
| ModelInstance | `api/core/model_manager.py:45`、`:181` `invoke_llm`、`:429` 轮询负载均衡 | `llm/manager.py` | 4 |
| 供应商配置 | `api/core/provider_manager.py:559` | `get_model(..., tenant_id)` | 4, 24 |
| 插件模型调用 | `api/core/plugin/impl/model.py:170` | — | 4, 26 |
| 模板语法 | `api/core/prompt/utils/prompt_template_parser.py`；`graphon/nodes/base/variable_template_parser.py:9` | `prompt/template.py`、`workflow/variables.py` | 5, 8 |
| 提示词编排 | `api/core/prompt/advanced_prompt_transform.py:147` | `nodes/llm.py` `build_messages` | 5 |
| 记忆 | `api/core/memory/token_buffer_memory.py:92`、`:202` | `memory.py` | 5 |
| 历史 token 预算 | `api/core/prompt/prompt_transform.py:58` | `history_within_budget` | 5 |

## 工作流引擎（graphon）

| 概念 | graphon / Dify | mini-dify | 章 |
|---|---|---|---|
| 图 JSON 存储 | `api/models/workflow.py:178`（`version`/`graph`/`environment_variables`） | `models.Workflow` | 7 |
| 乐观锁 | `models/workflow.py:553` `unique_hash`；`services/workflow_service.py:402`、`:439` | `services/workflow_service.py` | 7 |
| 发布 | `services/workflow_service.py:680` | `publish` | 7 |
| DSL | `services/app_dsl_service.py:134`、`:799` | `services/dsl.py` | 7 |
| 变量池 | `graphon/runtime/variable_pool.py:28`（add `:143`、get `:192`） | `workflow/variables.py` | 8 |
| 变量类型 | `graphon/variables/types.py:66`；`segments.py` | `infer_type` | 8 |
| 系统变量 | `api/core/workflow/system_variables.py:22` | `generator.execute` | 8 |
| 引擎主体 | `graphon/graph_engine/graph_engine.py:64`（run `:222`、start `:324`） | `workflow/engine.py` | 9 |
| 就绪规则 | `graph_engine/graph_state_manager.py:75` | `_is_ready` | 9 |
| 出边处理 | `graph_engine/graph_traversal/edge_processor.py:43`、`:119` | `_take_all` / `_take_branch` | 9 |
| 跳过传播 | `graph_engine/graph_traversal/skip_propagator.py:36`、`:76` | `_skip_edge` | 9 |
| Dispatcher | `graph_engine/orchestration/dispatcher.py:31`、`:110` | `run()` 主循环 | 9 |
| Worker / 池 | `graph_engine/worker.py:51`；`worker_management/worker_pool.py:27` | `ThreadPoolExecutor` | 9 |
| 事件处理 | `graph_engine/event_management/event_handlers.py:58`（完成 `:318`） | `_handle` / `_complete` | 9 |
| 执行类型 | `graphon/enums.py:80` `NodeExecutionType` | `entities.ExecutionType` | 9 |
| 错误处理 | `graph_engine/error_handler.py:51`（重试 `:114`、异常分支 `:153`、默认值 `:192`） | `_on_failed` | 12 |
| Layer | `graph_engine/layers/base.py`；`execution_limits.py:33` | `workflow/layers.py` | 9, 12 |
| 回复流 | `graph_engine/filters/response_stream.py`；`api/core/workflow/workflow_entry.py:56` | `workflow/response.py` | 10 |
| Node 基类 | `graphon/nodes/base/node.py:399`（run `:634`） | `nodes/base.py` | 10 |
| 节点注册与版本 | `api/core/workflow/node_factory.py:122`、`:140`、`:303` | `nodes/registry.py` | 10 |
| IF/ELSE | `graphon/nodes/if_else/if_else_node.py` | `nodes/if_else.py` | 10 |
| 迭代 | `graphon/nodes/iteration/iteration_node.py:63`；`graph_engine/iteration_container_handler.py:35` | `nodes/iteration.py` | 11 |
| 人工输入 / 暂停 | `graphon/nodes/human_input/human_input_node.py:63`；`api/core/app/layers/pause_state_persist_layer.py:77` | — | 12 |
| 持久化 | `api/core/app/workflow/layers/persistence.py:83`；`api/core/repositories/` | `apps/persistence.py` | 13 |
| 追踪上报 | `api/core/ops/`（`entities/config_entity.py:8`） | — | 13 |
| 单步调试 | `workflow.py:1223`；`workflow_entry.py:202` | `services/single_node.py` | 17 |

## 前端

| 概念 | Dify (`web/app/components/...`) | mini-dify (`frontend/src/...`) | 章 |
|---|---|---|---|
| 画布入口 | `workflow/index.tsx:111`（nodeTypes）、`:736` | `workflow/components/Canvas.tsx` | 14 |
| 节点组件分派 | `workflow/nodes/index.tsx` | `CustomNode.tsx` | 14 |
| 节点默认值与校验 | `workflow/nodes/<type>/default.ts` | `workflow/blocks.ts` | 14, 16 |
| 连线规则 | `workflow/hooks/use-nodes-interactions.ts:499` | `store.ts` `onConnect` | 14 |
| 状态切片 | `workflow/store/workflow/index.ts:71` | `workflow/store.ts` | 15 |
| 防抖保存 | `workflow/store/workflow/workflow-draft-slice.ts:35`（5s）；`workflow-app/hooks/use-nodes-sync-draft.ts` | `hooks/useSyncDraft.ts` | 15 |
| 撤销 | `workflow/workflow-history-store.ts`（zundo） | `store.ts` past/future | 15 |
| 上游节点 | `workflow/hooks/use-workflow.ts:104`、`:155` | `workflow/availableVars.ts` | 16 |
| 变量选择器 | `workflow/nodes/_base/components/variable/var-reference-picker.tsx` | `components/fields.tsx` | 16 |
| 检查清单 | `workflow/hooks/use-checklist.ts:165` | 后端 `/checklist` | 16 |
| SSE 客户端 | `web/service/base.ts:433` | `lib/sse.ts` | 6 |
| 运行事件 | `workflow/hooks/use-workflow-run-event/` | `hooks/useWorkflowRun.ts` | 17 |
| 运行面板 | `workflow/run/` | `components/RunPanel.tsx` | 17 |

## Agent、工具、MCP

| 概念 | Dify | mini-dify | 章 |
|---|---|---|---|
| FC Agent | `api/core/agent/fc_agent_runner.py:103`（最后一轮去掉工具 `:150`） | `agent/runner.py` `FunctionCallingRunner` | 18 |
| ReAct Agent | `api/core/agent/cot_agent_runner.py`；`prompt/template.py`；`output_parser/cot_output_parser.py:12` | `ReActRunner`、`agent/prompts.py` | 18 |
| 思考记录 | `api/core/agent/base_agent_runner.py:226`、`:268` | `AgentStep` | 18 |
| Agent 策略插件 | `api/core/agent/strategy/plugin.py:12` | — | 18, 21 |
| Tool 基类 | `api/core/tools/__base/tool.py:22` | `tools/base.py` | 19 |
| 工具消息类型 | `api/core/tools/entities/tool_entities.py:230` | `ToolResult` | 19 |
| 工具调用兜底 | `api/core/tools/tool_engine.py:49` | `tools/manager.py` `invoke_tool` | 19 |
| OpenAPI 解析 | `api/core/tools/utils/parser.py:32` | `tools/api_tool.py` | 19 |
| 工作流即工具 | `api/core/tools/workflow_as_tool/tool.py:40` | `tools/workflow_tool.py` | 19 |
| MCP 客户端 | `api/core/mcp/mcp_client.py:20` | `mcp/client.py` | 20 |
| MCP Server | `api/controllers/mcp/mcp.py:45`；`api/core/mcp/server/streamable_http.py:61` | `mcp/server.py` | 20 |
| Agent 节点 v1/v2 | `api/core/workflow/nodes/agent/agent_node.py:30`；`agent_v2/agent_node.py:84` | `nodes/agent.py` | 21 |
| agenton | `dify-agent/src/agenton/`、`dify-agent/docs/agenton/` | — | 21 |

## RAG

| 概念 | Dify | mini-dify | 章 |
|---|---|---|---|
| 索引任务 | `api/tasks/document_indexing_task.py:35`；`api/services/knowledge/indexing/execution.py:73` | `rag/indexing.py` | 22 |
| 索引状态 | `api/models/enums.py:121` | `Document.status` | 22 |
| 租户公平队列 | `api/core/rag/pipeline/queue.py:25` | — | 22 |
| 提取 / 清洗 | `api/core/rag/extractor/`；`cleaner/clean_processor.py` | `rag/processing.py` | 22 |
| 分段 | `api/core/rag/splitter/fixed_text_splitter.py:34` | `recursive_split` | 22 |
| 父子分段 | `api/core/rag/index_processor/processor/parent_child_index_processor.py:44` | `split_document(mode="parent_child")` | 22 |
| 向量缓存 | `api/core/rag/embedding/cached_embedding.py:24` | `embed_texts` | 22 |
| 检索方法 | `api/core/rag/retrieval/retrieval_methods.py` | `retrieve` | 23 |
| 加权融合 | `api/core/rag/rerank/weight_rerank.py:20` | `retrieve` 混合 | 23 |
| 多库与路由 | `api/core/rag/retrieval/dataset_retrieval.py:651`、`:793` | — | 23 |
| 向量库工厂 | `api/core/rag/datasource/vdb/vector_factory.py` | JSON + numpy | 23 |

## 平台

| 概念 | Dify | mini-dify | 章 |
|---|---|---|---|
| 账号、租户、成员 | `api/models/account.py:29`、`:175`、`:212`；`api/enums/account.py:7` | `models.py` | 24 |
| RBAC | `api/core/rbac/entities.py:25` | `auth.py` `ROLE_RANK` | 24 |
| 密码 / JWT | `api/libs/password.py:19`；`api/libs/passport.py` | `security/crypto.py` | 24 |
| Service API 鉴权 | `api/controllers/service_api/wraps.py:396`；`services/api_token_service.py` | `auth.app_from_api_key` | 24 |
| 规范 | `api/AGENTS.md` | — | 2, 24, 28 |
| Celery 队列 | `api/docker/entrypoint.sh:34` | `tasks/celery_app.py` | 25 |
| Redis 命令通道 | `graphon/graph_engine/command_channels/redis_channel.py:61` | `tasks/channels.py` | 25 |
| 异步工作流 | `api/services/async_workflow_service.py:39` | `run_async` | 25 |
| 插件守护进程 | `docker/docker-compose.yaml:573`；`api/core/plugin/impl/base.py`；`backwards_invocation/` | `plugins.py` | 26 |
| SSRF | `api/core/helper/ssrf_proxy.py`；`docker/ssrf_proxy/squid.conf.template` | `security/ssrf.py` | 27 |
| 代码沙箱 | `api/core/helper/code_executor/code_executor.py:69`；`dify-sandbox` | `security/sandbox.py` | 27 |
| 凭证加密 | `api/libs/rsa.py:30`、`:47`；`api/core/helper/encrypter.py` | `security/crypto.py` | 27 |
| 执行限制 | `api/configs/feature/__init__.py:921`、`:931`、`:936` | `ExecutionLimitsLayer`、`MAX_CALL_DEPTH` | 12, 19 |
| Webhook | `api/controllers/trigger/webhook.py:60` | `api/service.py` `webhook` | 28 |
| 定时 | `api/schedule/workflow_schedule_task.py:18`、`:55`（SKIP LOCKED `:82`） | `scheduler.py` | 28 |
| 部署 | `docker/docker-compose.yaml`、`docker/README.md` | `docker/` | 2, 28 |
