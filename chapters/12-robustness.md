# 第 12 章 健壮性：错误、重试、超时、停止、人工介入

> 本章目标：让工作流在“节点会失败、外部服务会抖动、用户会中途停止、有时需要人来拍板”的现实里依然可靠；实现重试、三种错误策略、执行限制和停止，并理解暂停/恢复的原理。
> 前置：第 9、10 章。对应代码：mini-dify **v0.2** `backend/app/workflow/engine.py`（`_on_failed`）、`layers.py`、`commands.py`；前端失败处理面板见 v0.3。

## 12.1 问题：节点失败了怎么办

工作流里的每个外部调用都可能失败：LLM 被限流、HTTP 接口超时、用户写的代码抛了异常。不同场景需要不同的处理方式：

| 场景 | 期望的处理方式 |
|---|---|
| 接口偶尔超时 | **重试**几次 |
| 某个“锦上添花”的步骤失败了（比如查天气），主流程照常继续 | **使用默认值继续** |
| 失败了要走另一套逻辑（主模型失败就换备用模型，或者通知人工） | **走异常分支** |
| 关键步骤失败 | **终止整个工作流**（默认） |

Dify 把这四种处理方式都做成了节点上的配置，`BaseNodeData` 里有：

```python
# graphon/entities/base_node_data.py:17
class RetryConfig(BaseModel):
    max_retries: int = 0          # 最多重试几次
    retry_interval: int = 0       # 重试间隔，单位毫秒
    retry_enabled: bool = False

# graphon/enums.py:93
class ErrorStrategy(StrEnum):
    FAIL_BRANCH = "fail-branch"
    DEFAULT_VALUE = "default-value"
# error_strategy 为 None 时，表示“终止”
```

## 12.2 Dify 是怎么做的：ErrorHandler

节点失败时，Worker 产出 `NodeRunFailedEvent`。EventHandler 收到后交给 `ErrorHandler.handle_node_failure`（`graphon/graph_engine/error_handler.py:51`）：

```python
def handle_node_failure(self, *, frame_id, event):
    node = self._graph.nodes[event.node_id]
    retry_count = self._graph_execution.get_or_create_node_execution(...).retry_count

    # ① 先看能不能重试
    if node.retry and retry_count < node.retry_config.max_retries:
        result = self._handle_retry(event, retry_count)              # 114：sleep 间隔，返回 NodeRunRetryEvent
        if result:
            return result

    # ② 重试次数用完了，再按错误策略处理
    match node.error_strategy:
        case None:                         return self._handle_abort(event)          # 97：返回 None = 终止
        case ErrorStrategyEnum.FAIL_BRANCH: return self._handle_fail_branch(event)  # 153
        case ErrorStrategyEnum.DEFAULT_VALUE: return self._handle_default_value(event)  # 192
```

三种结果的去向：

- **重试** → `NodeRunRetryEvent`：EventHandler 把重试计数加一，把节点重新放进就绪队列（`event_handlers.py:296`）；
- **异常分支 / 默认值** → `NodeRunExceptionEvent`：节点的状态变成 `exception`（介于成功和失败之间），输出里带上 `error_message` 和 `error_type`；

```python
# _handle_fail_branch：走 "fail-branch" 这个出口
NodeRunExceptionEvent(..., node_run_result=NodeRunResult(
    status=EXCEPTION,
    outputs={"error_message": ..., "error_type": ...},
    edge_source_handle="fail-branch",
))
# _handle_default_value：输出 = 用户配置的默认值 + 错误信息，然后照常走所有出边
outputs = {**node.default_value_dict, "error_message": ..., "error_type": ...}
```

- **终止** → 返回 None：EventHandler 调用 `graph_execution.fail(...)`，Dispatcher 发现有 error 就退出循环。

EventHandler 处理 `NodeRunExceptionEvent` 的方式（`event_handlers.py:279`）：

```python
if node.error_strategy == ErrorStrategy.DEFAULT_VALUE:
    follow_branch = False          # 按普通节点处理：所有出边 TAKEN
elif node.error_strategy == ErrorStrategy.FAIL_BRANCH:
    follow_branch = True           # 按分支节点处理：只走 fail-branch
self._complete_node(frame=frame, event=event, follow_branch=follow_branch)
```

只要有节点以 exception 状态结束，整个运行的最终状态就是 **partial-succeeded**（部分成功，`GraphRunPartialSucceededEvent`）。它告诉调用方：结果出来了，但中间有步骤是降级处理的。

## 12.3 执行限制

防止失控的工作流（比如一个巨大的迭代，或者某个 HTTP 节点卡住）无限地消耗资源：

```python
# graphon/graph_engine/layers/execution_limits.py:33
class ExecutionLimitsLayer(GraphEngineLayer):
    def __init__(self, max_steps: int, max_time: int): ...
    def on_event(self, event):                       # 77
        if self._reached_step_limitation() or self._reached_time_limitation():
            self._send_abort_command(...)            # 123：通过命令通道发 Abort
```

默认值在 `api/configs/feature/__init__.py`：

```python
WORKFLOW_MAX_EXECUTION_STEPS = 500      # 921
WORKFLOW_MAX_EXECUTION_TIME = 3600      # 931（秒）
WORKFLOW_CALL_MAX_DEPTH = 5             # 工作流作为工具嵌套调用的最大深度
```

注意它的实现方式：**限制是用一个 Layer 实现的，它通过命令通道给引擎发 Abort**，和用户点“停止”走的是同一条路径。限制逻辑不需要侵入引擎内部。

## 12.4 停止

第 3 章（3.9）和第 9 章（9.4.7）讲过，停止要经过两个环节：

1. 外部通过**命令通道**发送 `AbortCommand`（单进程用 InMemoryChannel，多进程用 RedisChannel）；
2. 引擎的 Dispatcher 处理命令，把运行标记为 aborted；节点内部**协作式**地检查停止标志，然后退出。

停止后的运行状态是 `stopped`，已经产生的输出会保留下来。

## 12.5 人工介入：暂停与恢复

有些流程必须由人来做决定：“AI 写好了邮件草稿，经理审批后才能发出”。Dify 的 **Human Input** 节点（`graphon/nodes/human_input/human_input_node.py`）会让整个工作流**暂停**：

```python
# human_input_node.py:63
def _run(self):
    ...
    case PauseRequested(session_id=session_id):
        yield PauseRequestedEvent(reason=HitlRequired(...))    # HITL = Human In The Loop
```

暂停的过程：

1. 引擎收到 `NodeRunPauseRequestedEvent`（`event_handlers.py:237`）：把运行标记为 paused，把这个节点的状态重置为 UNKNOWN，并作为一个“延迟任务”保存起来；
2. Dispatcher 发现运行已暂停，就把就绪队列里还没执行的任务也取出来保存（`defer_ready_tasks`）；
3. 引擎发出 `GraphRunPausedEvent`，前端收到 `workflow_paused` 和 `human_input_required` 事件，显示一个表单；
4. `PauseStatePersistenceLayer`（`api/core/app/layers/pause_state_persist_layer.py:77`）把**整个运行时状态**序列化后存入数据库：变量池、节点和边的状态、就绪队列（`ReadyQueue.dumps()`）、迭代的执行帧……
5. 用户提交表单（可能是几小时以后，由另一台服务器处理），`WorkflowAppGenerator.resume`（`app_generator.py:272`）读出保存的状态，重建引擎；引擎的 `_start_execution(resume=True)` 把保存的任务重新放进队列，从中断的地方继续执行。

要支持暂停和恢复，**运行时状态必须可以序列化**。这就是 graphon 引擎把状态集中放在 `GraphRuntimeState` 里、并让 ReadyQueue 支持 `dumps/loads` 的原因。这也是 mini-dify 选择“每轮迭代一个子引擎”所放弃的能力：子引擎的状态分散在各个线程里，没法序列化。

## 12.6 从零实现

### 12.6.1 引擎里的失败处理

```python
# backend/app/workflow/engine.py
def _on_failed(self, event: NodeRunFailed):
    node = self.graph.nodes[event.node_id]
    retry = node.data.retry_config
    attempts = self._retries.get(node.id, 0)

    # ① 重试：不阻塞 dispatcher，而是把“等待间隔”交给 Worker 线程去 sleep
    if retry.retry_enabled and attempts < retry.max_retries:
        self._retries[node.id] = attempts + 1
        self._running.discard(node.id)
        yield from self._emit(node.event(NodeRunRetry, error=event.error, retry_index=attempts + 1))
        self._enqueue(node.id, delay=retry.retry_interval / 1000, retry=True)
        return

    strategy = node.data.error_strategy
    # ② 终止
    if strategy is None:
        self._error = f"节点「{node.title}」运行失败：{event.error}"
        self._finish(node.id)
        yield from self._emit(event)
        return

    # ③ 异常分支 / 默认值：把失败转换成一个 exception 状态的结果，然后按“完成”来处理
    self._exceptions += 1
    outputs = {"error_message": event.error, "error_type": event.result.error_type or "NodeError"}
    if strategy == ErrorStrategy.DEFAULT_VALUE:
        outputs = {**node.data.default_value, **outputs}
    exc_result = NodeRunResult(status=RunStatus.EXCEPTION, inputs=event.result.inputs,
                               process_data=event.result.process_data, outputs=outputs, error=event.error)
    exc_event = node.event(NodeRunException, result=exc_result, error=event.error, start_at=event.start_at)
    yield from self._complete(exc_event, exc_result)     # _complete 里会根据策略决定走哪些出边
```

和 graphon 的一处重要差别：graphon 的 `_handle_retry` 在 **Dispatcher 线程**里 `time.sleep(retry_interval)`。这意味着重试等待期间，其他并行分支的事件也处理不了。我们把延迟交给 Worker（`_enqueue(..., delay=...)` → `_execute` 里先 sleep），dispatcher 可以继续处理其他事件。

### 12.6.2 运行的终止事件

```python
def _terminal_event(self):
    if self._abort_reason:  return GraphRunAborted(reason=self._abort_reason, outputs=self._outputs)
    if self._error:         return GraphRunFailed(error=self._error, exceptions_count=self._exceptions)
    if self._exceptions:    return GraphRunPartialSucceeded(outputs=self._outputs, exceptions_count=self._exceptions)
    return GraphRunSucceeded(outputs=self._outputs)
```

转换器把它们分别映射为 `workflow_finished` 事件里的 `status`：`stopped / failed / partial-succeeded / succeeded`。

### 12.6.3 前端：失败处理面板（v0.3）

每个可执行节点的配置面板底部都有“失败处理”区域（`frontend/src/workflow/components/NodePanel.tsx` 的 `ErrorHandling`）：重试开关、次数、间隔；“重试后仍失败时”可以选择终止、使用默认值或走异常分支；选择默认值时，可以编辑一段默认输出 JSON。

选择“走异常分支”后，节点右侧会多出一个“异常”出口（`blocks.ts` 的 `sourceHandles` 会加上 `fail-branch`），可以从这里连线到处理失败的节点。下游节点还能引用 `{{#该节点.error_message#}}`（`outputVars` 会为配置了错误策略的节点加上 `error_message` 和 `error_type` 两个输出变量）。

## 12.7 运行与验证

```bash
cd code/mini-dify && git checkout v0.2 && cd backend
uv run pytest -q tests/test_engine.py -k "failure or default_value or fail_branch or retry or abort" -v
```

| 测试 | 场景 | 结果 |
|---|---|---|
| `test_failure_aborts_without_error_strategy` | 代码节点抛异常，没有配置错误策略 | `GraphRunFailed`，错误信息里包含 boom |
| `test_default_value_strategy_gives_partial_success` | 同上，配置了默认值 `{"y": "fallback"}` | `GraphRunPartialSucceeded`，输出为 fallback |
| `test_fail_branch_strategy_routes_to_fail_handle` | 配置了异常分支 | 正常分支的节点没有执行，异常分支收到了 `error_message` |
| `test_retry_then_succeed` | 前两次失败、第三次成功（用文件记录调用次数） | 两次 `NodeRunRetry`，最终输出 2 |
| `test_abort_stops_run` | 运行中途停止 | `GraphRunAborted`，下游节点没有执行 |

在 UI 中验证：给 HTTP 节点填一个不存在的地址 `https://this-domain-does-not-exist.invalid`，配置“重试 2 次、间隔 500ms，之后走异常分支”，从异常分支连到一个模板转换节点，模板写 `接口挂了：{{ e }}`（变量 e 选择 HTTP 节点的 `error_message`）。运行后可以在追踪面板里看到重试记录，HTTP 节点以橙色的“异常”状态结束，最终运行状态是 partial-succeeded。

## 12.8 练习

1. **巩固**：partial-succeeded 状态对 API 调用方有什么意义？如果没有这个状态，调用方会怎么误判？
2. **扩展**：实现**指数退避**重试：在 `retry_config` 里加 `backoff: "fixed" | "exponential"`，指数模式下第 n 次重试的间隔是 `interval * 2^(n-1)`，并加入随机抖动。
3. **读源码**：读 Dify 的 `PauseStatePersistenceLayer`，列出暂停时它保存了哪些数据，以及恢复时这些数据分别是怎么用的。

## 12.9 延伸阅读

- `api/core/workflow/human_input_forms.py`、`human_input_policy.py`：人工输入表单的定义和投递策略（邮件、站内信……）
- `api/tasks/human_input_timeout_tasks.py`：人工输入超时的处理
