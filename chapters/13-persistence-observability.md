# 第 13 章 持久化与可观测

> 本章目标：把每次运行、每个节点的输入输出都记录下来，用于回放、排错和统计；理解 Dify 的 Repository 抽象和 LLM 链路追踪；用一个 Layer 实现 mini-dify 的运行记录。
> 前置：第 9 章（Layer）。对应代码：mini-dify **v0.2** `backend/app/apps/persistence.py`、`app/models.py`（`WorkflowRun`、`NodeExecution`）。

## 13.1 问题：跑完以后，还剩下什么

一次运行结束，内存里的引擎、变量池都会被回收。可是用户和开发者接下来还需要：

- **回放**：“昨天下午那次运行为什么失败了？”——需要知道每个节点当时的输入、输出、错误信息；
- **调试**：LLM 节点最终发出去的提示词到底长什么样（`process_data.prompts`）；
- **统计**：调用量、token 消耗、平均耗时、失败率；
- **审计**：谁、在什么时候、通过什么渠道（调试 / API / WebApp / 定时任务）触发了这次运行。

这些都要求**引擎事件在落地之前，先被记录到持久存储里**。

## 13.2 两张核心表

| 表 | 一行代表 | 主要字段 |
|---|---|---|
| `workflow_runs` | 一次运行 | 应用、工作流版本、触发来源、状态、输入、输出、错误、耗时、总 token、总步数、创建人 |
| `workflow_node_executions` | 一个节点的一次执行 | 所属运行、序号、节点 ID 和类型、标题、状态、输入、处理过程（process_data）、输出、错误、耗时、token、所属迭代与轮次 |

Dify 的定义在 `api/models/workflow.py`：`WorkflowRun`（第 759 行）、`WorkflowNodeExecutionModel`（第 920 行）。还有一张 `WorkflowNodeExecutionOffload`（第 1172 行）：当某个节点的输入或输出**特别大**时（比如文档提取节点输出了一整本书），把内容卸载到对象存储，表里只保留引用，避免把数据库撑爆。

## 13.3 Dify 是怎么做的

### 13.3.1 用 Layer 来持久化

```python
# api/core/app/workflow/layers/persistence.py:83
class WorkflowPersistenceLayer(GraphEngineLayer):
    def on_graph_start(self): ...                                  # 111
    def on_event(self, event):                                     # 118：按事件类型分派
        ...
    def _handle_graph_run_started(self, event): ...                # 152：创建 WorkflowExecution
    def _handle_graph_run_succeeded / partial_succeeded / failed / aborted / paused: ...
    def _handle_node_started(self, event): ...                     # 226：创建 NodeExecution（状态 running）
    def _handle_node_retry(self, event): ...                       # 266
    def _handle_node_succeeded / failed / exception: ...           # 279 / 293 / 308：更新状态、输出、耗时
    def _handle_node_pause_requested(self, event): ...             # 323
```

Runner 在启动前把它挂到引擎上（`app_runner.py:212`）。**引擎不知道数据库的存在**，持久化只是一个旁观的“事件订阅者”。

### 13.3.2 Repository：存储方式可以替换

Layer 并不直接写 SQL，而是调用 **Repository**：

```
api/core/repositories/
├── factory.py                                         根据配置决定用哪个实现
├── sqlalchemy_workflow_execution_repository.py        同步写入数据库
├── sqlalchemy_workflow_node_execution_repository.py
├── celery_workflow_execution_repository.py            交给 Celery 异步写入
└── celery_workflow_node_execution_repository.py
```

`factory.py` 用“类路径字符串 + `import_string`”的方式（类似 Django 的 settings）创建实例，具体用哪个实现由配置决定：

```python
# api/configs/feature/__init__.py
WORKFLOW_NODE_EXECUTION_STORAGE: str = ...       # 984
CORE_WORKFLOW_EXECUTION_REPOSITORY: str = ...    # 995  可以填一个自定义的类路径
```

为什么需要可替换？

- 高并发时，每个节点都同步写一次数据库会拖慢运行，换成 Celery 实现就变成了异步批量写入；
- 运行记录量很大时，可以写到日志型存储里（Dify 支持 Logstore，见 `extensions/ext_logstore.py`）；
- 企业私有化部署时，可能要求写到自己的存储系统。

运行记录还会被定期归档（`WorkflowArchiveLog`、`WorkflowRunArchiveBundle` 两张表，以及 `tasks/workflow_run_archive_download_tasks.py`），超过保留期的会被清理。

### 13.3.3 LLM 链路追踪（Ops Trace）

数据库里的运行记录主要供平台自己的界面使用。专业的 LLM 可观测平台（Langfuse、LangSmith……）能提供更好的分析能力，比如提示词版本对比、评测、成本分析。Dify 可以把每次运行**上报**到这些平台：

```python
# api/core/ops/entities/config_entity.py:8
class TracingProviderEnum(StrEnum):
    ARIZE = "arize"; PHOENIX = "phoenix"; LANGFUSE = "langfuse"; LANGSMITH = "langsmith"
    OPIK = "opik"; WEAVE = "weave"; ALIYUN = "aliyun"; MLFLOW = "mlflow"; DATABRICKS = "databricks"; TENCENT = "tencent"
```

在应用的“监测”页面里配置好以后，每次运行结束时，`core/ops/ops_trace_manager.py` 会把运行信息组装成对应平台的 trace 格式，交给 Celery 任务异步上报（`tasks/ops_trace_task.py`）。上报一定要异步：可观测平台慢了或者挂了，都不应该影响用户的请求。

此外还有基础设施层面的 **OpenTelemetry**：`core/app/workflow/layers/observability.py`，以及 `extensions/otel/`。每个节点的执行都会生成一个 span，可以接入 Jaeger、Grafana Tempo 等系统。

## 13.4 从零实现：PersistenceLayer

```python
# backend/app/apps/persistence.py
class PersistenceLayer(Layer):
    def __init__(self, run_id: str):
        self.run_id = run_id
        self._index = 0
        self._started = datetime.now()

    def on_event(self, event):
        match event:
            case NodeRunStarted():
                self._index += 1
                with session_scope() as s:
                    s.add(NodeExecution(
                        id=event.execution_id,              # 用事件里的执行 ID 作主键
                        workflow_run_id=self.run_id, index=self._index,
                        node_id=event.node_id, node_type=event.node_type, title=event.title,
                        status="running",
                        iteration_id=event.in_iteration_id, iteration_index=event.iteration_index,
                        created_at=event.start_at,
                    ))
            case NodeRunSucceeded() | NodeRunFailed() | NodeRunException():
                status = {NodeRunSucceeded: "succeeded", NodeRunFailed: "failed", NodeRunException: "exception"}[type(event)]
                with session_scope() as s:
                    row = s.get(NodeExecution, event.execution_id)
                    r = event.result
                    row.status = status
                    row.inputs, row.process_data, row.outputs = _jsonable(r.inputs), _jsonable(r.process_data), _jsonable(r.outputs)
                    row.error, row.total_tokens = r.error, r.total_tokens
                    row.finished_at = event.finished_at
                    row.elapsed_time = (event.finished_at - event.start_at).total_seconds()

    def on_graph_end(self, terminal):
        status, outputs, error = "succeeded", {}, None
        match terminal:
            case GraphRunSucceeded():         outputs = terminal.outputs
            case GraphRunPartialSucceeded():  status, outputs = "partial-succeeded", terminal.outputs
            case GraphRunFailed():            status, error = "failed", terminal.error
            case GraphRunAborted():           status, error, outputs = "stopped", terminal.reason, terminal.outputs
        with session_scope() as s:
            run = s.get(WorkflowRun, self.run_id)
            run.status, run.outputs, run.error = status, _jsonable(outputs), error
            run.total_steps, run.total_tokens = self.engine.steps, self.engine.total_tokens
            run.finished_at = datetime.now()
            run.elapsed_time = (run.finished_at - self._started).total_seconds()
```

几个细节：

1. **`workflow_runs` 的记录在 Generator 的准备阶段就创建了**（状态为 running），而不是等引擎启动后才创建。这样即使构建图的时候就出错了（配置有误），也会留下一条 failed 的记录，前端立刻就能查到这次运行。
2. **节点开始时插入、结束时更新**：运行过程中查询，也能看到“正在运行”的节点。
3. **`_jsonable`**：节点输出里可能有 datetime 之类不能直接序列化成 JSON 的对象，先 `json.dumps(default=str)` 再 `json.loads`，把它们规整成纯 JSON。
4. **迭代内部的节点也会被记录**：子引擎的事件经由迭代节点透传到外层引擎，外层引擎的 Layer 能看到它们，`iteration_id` 和 `iteration_index` 字段就派上了用场。

### 线程安全

Layer 的 `on_event` 在 dispatcher 线程里被调用，每次写入都会开一个新的 session。`app/db.py` 给 SQLite 打开了 **WAL 模式**和 `busy_timeout`：

```python
@event.listens_for(engine, "connect")
def _sqlite_pragmas(conn, _record):
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")      # 读操作不会阻塞写操作
    cur.execute("PRAGMA busy_timeout=5000")     # 遇到写锁时最多等待 5 秒，而不是立即报错
    cur.execute("PRAGMA foreign_keys=ON")
```

即便如此，SQLite 同一时刻**只允许一个写入者**。第 28 章会遇到这个限制引发的真实 bug。

### 查询运行记录的 API

```
GET /api/apps/{id}/workflow-runs                          最近的运行列表
GET /api/apps/{id}/workflow-runs/{run_id}                 某次运行的详情
GET /api/apps/{id}/workflow-runs/{run_id}/node-executions 这次运行中每个节点的执行记录
```

前端运行面板的“历史”标签页就是用这三个接口实现的（第 17 章）。

## 13.5 运行与验证

```bash
cd code/mini-dify && git checkout v0.2 && cd backend
uv run pytest -q tests/test_api.py::test_workflow_app_lifecycle
```

这个测试先运行一次默认工作流，然后检查：运行列表里第一条记录的状态是 succeeded；节点执行记录依次是 start、llm、end；LLM 节点的 outputs.text 以 "hello" 结尾。

直接查看数据库：

```bash
sqlite3 storage/mini_dify.db "select node_type, status, elapsed_time, total_tokens from workflow_node_executions order by created_at desc limit 5"
```

## 13.6 练习

1. **巩固**：为什么持久化要用 Layer 来做，而不是写在引擎里？举出至少两个好处。
2. **扩展**：实现一个 `LangfuseLayer`：`on_graph_start` 时创建一个 trace，每个 LLM 节点完成时创建一个 generation（带上 prompts、输出和 usage），`on_graph_end` 时结束 trace。上报放到后台线程里做，不能阻塞 dispatcher。
3. **读源码**：读 Dify 的 `celery_workflow_node_execution_repository.py`，它是怎样保证“先写入的开始记录”和“后写入的完成记录”不会乱序的？

## 13.7 延伸阅读

- `api/core/ops/ops_trace_manager.py`：多平台 trace 的统一组装
- `api/services/workflow_run_service.py`：运行记录的查询、筛选、统计
