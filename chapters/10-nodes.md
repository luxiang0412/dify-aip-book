# 第 10 章 节点体系

> 本章目标：设计一个可扩展的节点抽象；实现 Start、End、Answer、LLM、IF/ELSE、Code、HTTP、模板转换、变量聚合 9 种节点；理解“回复流协调器”怎样让多个 LLM 的输出按模板顺序流式呈现。
> 前置：第 8、9 章。对应代码：mini-dify **v0.2** `backend/app/workflow/nodes/`、`response.py`。

## 10.1 问题：节点要长什么样，引擎才能不认识它也能跑

引擎只关心三件事：节点的**执行类型**（第 9 章）、`run()` 产生的**事件**、以及结果里的 `outputs` 和 `edge_source_handle`。所以节点的契约可以非常小：

```
输入：配置（data） + 变量池（只读）
输出：一串事件，最后是 NodeRunResult(outputs, edge_source_handle, ...)
```

这样做的好处是：**新增一种节点 = 写一个类 + 注册**，引擎、持久化、事件转换一行都不用改。

## 10.2 Dify 是怎么做的

### 10.2.1 Node 基类

```python
# graphon/nodes/base/node.py:399
class Node[NodeDataT: BaseNodeData](...):
    node_type: ClassVar[NodeType]
    execution_type: ClassVar[NodeExecutionType] = NodeExecutionType.EXECUTABLE

    def __init_subclass__(cls, **kwargs):            # 418
        # 从 class MyNode(Node[MyNodeData]) 的泛型参数里自动取出 MyNodeData，
        # 记下来，__init__ 时用它校验 data
        ...

    @abstractmethod
    def _run(self) -> NodeRunResult | Generator[NodeEventBase | ...]:   # 621
        """子类实现：返回结果，或者 yield 事件"""

    def run(self) -> Generator[GraphNodeEventBase, ...]:                 # 634
        yield NodeRunStartedEvent(id=execution_id, node_id=..., node_type=..., ...)
        try:
            yield from self._run_events()          # 把 _run 的结果/事件规范化成引擎事件
        except Exception as e:
            yield self._build_run_failed_event(e)  # 任何异常 → NodeRunFailedEvent
```

两个值得学的设计：

1. **公共的 `run()` 和子类的 `_run()` 分开**（模板方法模式）：开始事件、异常兜底、事件规范化都在基类里统一完成，子类只写业务逻辑；
2. **`_run()` 可以返回结果，也可以 yield 事件**：简单节点（IF/ELSE、模板）直接 `return NodeRunResult(...)`；需要报告进度的节点（LLM 的流式输出、迭代的每一轮）用 yield。

基类还会把节点内部的事件（`StreamChunkEvent`、`IterationNextEvent`……）转换成对应的引擎事件（`node.py:859` 起的 `_dispatch` 系列方法）。

### 10.2.2 节点注册与版本

```python
# api/core/workflow/node_factory.py
def register_nodes() -> None:                         # 122
    _import_node_package("graphon.nodes")             # graphon 内置的通用节点
    _import_node_package("core.workflow.nodes")       # Dify 平台相关的节点

def resolve_workflow_node_class(node_type, node_version):   # 140
    node_mapping = get_node_type_classes_mapping()[node_type]
    latest_node_class = node_mapping.get(LATEST_VERSION)
    matched_node_class = node_mapping.get(node_version)
    return matched_node_class or latest_node_class
```

**节点是带版本号的**：当某个节点的配置格式需要改动时（比如变量赋值节点就有 v1、v2 两版，见 `graphon/nodes/variable_assigner/v1`、`v2`），新旧版本的类同时注册。旧工作流里写着 `version: "1"`，依然能按旧逻辑运行。平台产品必须考虑这种向后兼容：用户的工作流可能是两年前画的。

节点的归属也很清楚：

- `graphon/nodes/`：**通用节点**（start、end、answer、llm、if_else、code、http_request、template_transform、iteration、loop、question_classifier、parameter_extractor、list_operator、document_extractor、tool……），不依赖 Dify 平台；
- `api/core/workflow/nodes/`：**平台节点**（agent、knowledge_retrieval、datasource、trigger_webhook/schedule/plugin、human_input……），需要访问数据库、插件、知识库。

### 10.2.3 依赖注入：通用节点如何调用平台能力

graphon 的 Code 节点并不知道 Dify 的沙箱服务在哪里，它只依赖一个协议：

```python
# graphon/nodes/code/code_node.py
class CodeExecutorProtocol(Protocol): ...           # 26
class CodeNode(Node[CodeNodeData]):
    def __init__(self, ..., code_executor: CodeExecutorProtocol, ...):   # 92
        self._code_executor = code_executor
    def _run(self):                                  # 143
        result = self._code_executor.execute(...)    # 163
```

由 Dify 的 `DifyNodeFactory`（`api/core/workflow/node_factory.py:303`）在创建节点时注入具体实现 `DefaultWorkflowCodeExecutor`（第 284 行，调用 `dify-sandbox`）。LLM 节点也一样，模型调用、文件保存都是通过注入的协议完成的。**这正是 graphon 能作为独立包存在的原因。**

Dify 还会子类化 graphon 的节点，加上平台相关的行为，例如 `api/core/workflow/llm_node.py` 的 `DifyLLMNode(LLMNode)`。

### 10.2.4 几个典型节点

- **IF/ELSE**（`graphon/nodes/if_else/if_else_node.py`）：执行类型为 `BRANCH`。依次计算每个 case，第一个满足的 case 返回 `edge_source_handle=case_id`，都不满足则返回 `"false"`：

```python
return NodeRunResult(
    status=WorkflowNodeExecutionStatus.SUCCEEDED,
    inputs=..., process_data=...,
    edge_source_handle=evaluation.selected_case_id or "false",
    outputs={"result": evaluation.final_result, "selected_case_id": evaluation.selected_case_id},
)
```

- **Answer / End**：执行类型为 `RESPONSE`（`answer_node.py:25`、`end_node.py:16`）。它们的输出会被合并成运行的最终输出（第 9 章 `merge_response_outputs`）。
- **LLM**（`graphon/nodes/llm/node.py`，2300 多行）：多模态输入、结构化输出、推理内容、记忆、上下文、文件……骨架就是“渲染提示词 → 流式调用 → 逐片 yield → 汇总结果”。

### 10.2.5 回复流：多个 LLM 输出怎么排序

考虑这样一个 Answer 模板：

```
翻译：{{#llm_translate.text#}}
润色：{{#llm_polish.text#}}
```

两个 LLM 节点**并行**运行，各自都在流式输出。用户应该看到的是：先出现“翻译：”，然后翻译 LLM 的字**一个一个地流出来**，翻译完了再出现“润色：”，然后才是润色 LLM 的输出。即使润色 LLM 先开始输出，它的内容也要**等前面的部分输出完**。

还有更难的情况：Answer 节点位于某个 IF 分支上，在分支还没决定之前，**一个字都不能输出**，否则用户会看到不该看到的内容。

这就是 graphon 的 `ResponseStreamFilter`（`graphon/graph_engine/filters/response_stream.py`，800 多行）要解决的问题。Dify 在 `WorkflowEntry.run()` 里把它作为事件过滤器套在引擎外面（第 3 章 3.5）。它的核心概念：

- 把每个回复节点的模板拆成**片段**：文本片段和变量片段；
- 为每个回复节点计算从根节点到它的**路径**，只记录路径上会阻塞它的边（`Path.edges`，“Blocking traversal edges that must be taken before a response can stream”）；路径上的边全部 TAKEN 之后，这个回复节点才开始输出；
- 输出时严格按片段顺序：当前片段是变量时，如果来源节点正在流式输出，就转发它的片段；否则等它完成后一次性输出完整的值。

## 10.3 从零实现

### 10.3.1 基类：RunContext + Node

```python
# backend/app/workflow/nodes/base.py
@dataclass
class RunContext:
    """一次运行（或一轮迭代）里，节点在自身配置之外需要的一切。"""
    pool: VariablePool
    graph_config: GraphConfig
    inputs: dict[str, Any] = field(default_factory=dict)
    app_id: str = ""; workflow_id: str = ""; workflow_run_id: str = ""; user_id: str = ""
    mode: str = "workflow"
    history: list[Any] = field(default_factory=list)        # Chatflow 的记忆
    stop_event: threading.Event = field(default_factory=threading.Event)
    iteration_id: str | None = None
    iteration_index: int | None = None
    parent: "RunContext | None" = None                       # 迭代的轮次指向外层上下文

    def should_stop(self) -> bool:
        return self.stop_event.is_set() or (self.parent is not None and self.parent.should_stop())


class Node:
    node_type: ClassVar[str]
    data_class: ClassVar[type[BaseNodeData]] = BaseNodeData
    execution_type: ClassVar[ExecutionType] = ExecutionType.EXECUTABLE

    def __init__(self, config: NodeConfig, ctx: RunContext):
        self.id = config.id
        self.ctx = ctx
        self.data = self.data_class.model_validate(config.data)    # 用节点自己的数据类做校验
        self.state = NodeState.UNKNOWN

    def run(self) -> Iterator[NodeEvent]:
        self._execution_id = str(uuid.uuid4())
        start_at = datetime.now()
        yield self.event(NodeRunStarted, start_at=start_at)
        result = None
        try:
            produced = self._run()
            if isinstance(produced, NodeRunResult):
                result = produced
            else:
                for item in produced:                 # 生成器：中间产出事件，最后一个是结果
                    if isinstance(item, NodeRunResult):
                        result = item
                    else:
                        yield item
            if result is None:
                raise NodeError("node finished without a result")
        except Exception as e:
            result = NodeRunResult(status=RunStatus.FAILED, error=str(e) or type(e).__name__, error_type=type(e).__name__)
        if result.status == RunStatus.FAILED:
            yield self.event(NodeRunFailed, result=result, error=result.error or "", start_at=start_at)
        else:
            yield self.event(NodeRunSucceeded, result=result, start_at=start_at)

    def _run(self) -> NodeRunResult | Iterator[Any]:
        raise NotImplementedError

    @classmethod
    def variable_selectors(cls, data) -> list[list[str]]:
        return []                                     # 这个节点会读取哪些变量（检查清单、单步调试要用）
```

和 graphon 的差别：我们用 `data_class` 类属性显式声明数据类，而不是从泛型参数里推断，更直白一些。

`self.event(cls, **kw)` 会自动填好 `node_id / node_type / title / execution_id / in_iteration_id / iteration_index`，节点里产出事件就不用重复写这些字段。

**为什么要有 `effective_execution_type`？** 配置了“异常分支”的普通节点，实际上有两个出口（`source` 和 `fail-branch`），引擎必须把它当作分支节点处理。graphon 在构建图时用 `_promote_fail_branch_nodes` 把这类节点提升为 BRANCH，我们用一个属性动态计算：

```python
@property
def effective_execution_type(self):
    if self.data.error_strategy == ErrorStrategy.FAIL_BRANCH and self.execution_type == ExecutionType.EXECUTABLE:
        return ExecutionType.BRANCH
    return self.execution_type
```

### 10.3.2 注册表

```python
# backend/app/workflow/nodes/registry.py
NODE_CLASSES: dict[str, type[Node]] = {}

def register_node(cls):
    NODE_CLASSES[cls.node_type] = cls
    return cls

def create_node(config: NodeConfig, ctx: RunContext) -> Node:
    cls = NODE_CLASSES.get(config.type)
    if cls is None:
        raise NodeError(f"unknown node type: {config.type}")
    return cls(config, ctx)
```

`nodes/__init__.py` 里 `from . import basic, code, if_else, iteration, llm, transform`，通过 import 的副作用完成注册。v1.0 的插件也是调用 `register_node` 来新增节点类型的（第 26 章）。

### 10.3.3 九种节点

| 节点 | 文件 | 执行类型 | 输出 | 实现要点 |
|---|---|---|---|---|
| Start | `basic.py` | ROOT | 每个输入字段 | 校验必填项，number 类型做转换，select 类型校验取值范围 |
| End | `basic.py` | RESPONSE | `outputs` 中声明的每一项 | `pool.get(value_selector)` |
| Answer | `basic.py` | RESPONSE | `answer` | `pool.render(answer)`；流式输出交给协调器 |
| LLM | `llm.py` | EXECUTABLE | `text`、`usage` | 渲染提示词 + 记忆；逐片 yield `NodeRunStreamChunk`；每片检查是否需要停止 |
| IF/ELSE | `if_else.py` | BRANCH | `result`、`selected_case_id` | 14 种比较运算（和 Dify 写法一致）；比较值也支持 `{{#变量#}}` |
| Code | `code.py` | EXECUTABLE | 声明的输出 | 子进程执行 `main()`；按声明的类型校验返回值 |
| HTTP 请求 | `transform.py` | EXECUTABLE | `status_code`、`body`、`headers` | URL、headers、body 都可以引用变量；4 种 body 格式 |
| 模板转换 | `transform.py` | EXECUTABLE | `output` | Jinja2 **沙箱环境** |
| 变量聚合 | `basic.py` | EXECUTABLE | `output` | 取第一个非空的变量（用于合并分支） |

挑几个讲。

**LLM 节点**：

```python
# backend/app/workflow/nodes/llm.py
def _run(self):
    messages = self.build_messages()                    # 渲染提示词 + 插入记忆（第 5 章）
    model = get_model(f"{self.data.model.provider}/{self.data.model.name}")
    text, usage = [], Usage()
    try:
        for chunk in model.invoke(messages, params=self.data.model.completion_params or None):
            if self.ctx.should_stop():
                break                                   # 协作式停止
            if chunk.delta:
                text.append(chunk.delta)
                yield self.event(NodeRunStreamChunk, selector=[self.id, "text"], chunk=chunk.delta)
            if chunk.usage:
                usage = chunk.usage
    except LLMError as e:
        raise NodeError(str(e)) from e
    yield NodeRunResult(
        process_data={"model": ..., "prompts": [{"role": m.role, "text": m.content} for m in messages]},
        outputs={"text": "".join(text), "usage": usage.to_dict()},
        total_tokens=usage.total_tokens,
    )
```

`process_data.prompts` 把**最终发给模型的提示词**记录下来。调试时，“我的变量到底有没有渲染进去”是最常见的问题，有了这条记录就能直接查看（第 17 章的追踪面板会展示它）。

**IF/ELSE 节点**：

```python
def evaluate(actual, op, expected) -> bool:
    match op:
        case "empty":        return actual in (None, "", [], {})
        case "contains":     return actual is not None and expected in actual
        case "start with":   return isinstance(actual, str) and actual.startswith(str(expected))
        case "is":           return str(actual) == str(expected)
        case ">":            return actual is not None and float(actual) > float(expected)
        ...

def _run(self):
    for case in self.data.cases:
        results = [evaluate(self.pool.get(c.variable_selector), c.comparison_operator,
                            self.pool.render(c.value) if isinstance(c.value, str) else c.value)
                   for c in case.conditions]
        matched = all(results) if case.logical_operator == "and" else any(results)
        if matched and results:
            return NodeRunResult(outputs={"result": True, "selected_case_id": case.case_id},
                                 edge_source_handle=case.case_id)
    return NodeRunResult(outputs={"result": False, "selected_case_id": "false"}, edge_source_handle="false")
```

**Code 节点**：在**独立的子进程**里运行用户代码，主进程和子进程之间用 JSON 通信：

```python
RUNNER = r"""
import json, sys
payload = json.loads(sys.stdin.read())
scope = {}
exec(payload["code"], scope)
result = scope["main"](**payload["inputs"])
sys.stdout.write("<<RESULT>>" + json.dumps(result, ensure_ascii=False, default=str))
"""
proc = subprocess.run([sys.executable, "-I", "-c", RUNNER], input=json.dumps(...),
                      capture_output=True, text=True, timeout=timeout)
```

输出前面加一个 `<<RESULT>>` 标记，是为了区分“用户代码里 `print` 出来的内容”和真正的结果。v1.0 会再加上资源限制和审计钩子（第 27 章）。

**模板转换节点**用 `jinja2.sandbox.SandboxedEnvironment`，它会拦截 `{{ ''.__class__.__mro__[1].__subclasses__() }}` 这类沙箱逃逸手法。

### 10.3.4 回复流协调器（ResponseCoordinator）

这是 graphon `ResponseStreamFilter` 的简化版，约 150 行，规则如下：

1. 回复节点（Answer，或只有一个输出的 End）的模板会被拆成片段：`"前缀|{{#llm.text#}}|后缀"` → `["前缀|", ["llm","text"], "|后缀"]`（`variables.split_template`）；
2. 对每个回复节点，DFS 出所有从根节点到它的路径，**只保留从分支节点出发的边**。原因是普通节点的出边一定会被走过，只有分支节点的出边才可能被跳过；
3. **激活条件**：节点没有被跳过，并且存在一条路径，路径上记录的分支边全部 TAKEN；
4. 激活之后**按片段顺序输出**：文本片段立即输出；变量片段如果是当前片段，且来源正在流式输出，就转发它的片段，否则等来源节点完成后输出完整的值；
5. 回复节点自己完成时，把剩下的片段全部输出。

```python
# backend/app/workflow/response.py（节选）
def on_event(self, event) -> list[ResponseChunk]:
    if isinstance(event, NodeRunStreamChunk):
        out = []
        for s in self._active():
            seg = s.segments[s.cursor] if s.cursor < len(s.segments) else None
            if isinstance(seg, list) and seg[:2] == event.selector[:2]:   # 正好轮到这个变量
                s.streamed.add(s.cursor)
                out.append(ResponseChunk(node_id=s.node_id, text=event.chunk, selector=seg))
        return out
    if isinstance(event, (NodeRunSucceeded, NodeRunException)):
        self.finished.add(event.node_id)
        ...                                      # 回复节点自己完成 → 全部输出
    for s in self._active():                     # 任何状态变化都可能让某个回复节点继续往前推进
        out += self._advance(s)
    return out

def _advance(self, s, flush=False):
    while s.cursor < len(s.segments):
        seg = s.segments[s.cursor]
        if isinstance(seg, str):
            out.append(ResponseChunk(node_id=s.node_id, text=seg))
        else:
            ready = flush or seg[0] in ("sys", "env", "conversation") or seg[0] in self.finished
            if not ready:
                break                            # 卡在一个还没完成的变量上：等待
            if s.cursor not in s.streamed:       # 没有流式输出过 → 一次性输出完整值
                out.append(ResponseChunk(node_id=s.node_id, text=value_to_text(self.pool.get(seg)), selector=seg))
        s.cursor += 1
```

引擎在 `_emit` 里把每个事件交给协调器，协调器产出的 `ResponseChunk` 事件跟在原事件后面一起往外发。转换器再把 `ResponseChunk` 变成 `text_chunk`（Workflow）或 `message`（Chatflow）。

和 graphon 相比，我们的简化在于：graphon 会处理多个回复节点之间的顺序（同一时刻只有一个回复节点在输出），我们允许多个激活的回复节点同时输出。这种情况只在多个 Answer 节点**并行**时才会出现，而且很少见。

## 10.4 运行与验证

```bash
cd code/mini-dify && git checkout v0.2 && cd backend
uv run pytest -q tests/test_engine.py -k "answer"
```

- `test_answer_streams_llm_tokens_in_template_order`：第一片是“前缀|”，最后一片是“|后缀”，中间是 LLM 的一个个字，拼起来恰好等于 Answer 的最终输出；
- `test_answer_on_untaken_branch_streams_nothing`：IF 选了 else，只输出 “B!”。

用 curl 直观感受一下：把默认 Chatflow 的 Answer 改成 `前缀：{{#llm.text#}}（完）`，运行后会看到 `message` 事件依次是 `前缀：`、`（`、`m`、……、`（完）`。

## 10.5 练习

1. **巩固**：为什么 Answer 节点的流式输出要由协调器来做，而不是让 Answer 节点自己去读 LLM 的流？（提示：Answer 节点要等所有上游完成后才会开始运行。）
2. **扩展**：实现“问题分类器”节点：执行类型为 BRANCH，用 LLM 把 `sys.query` 归入用户配置的几个类别之一，返回 `edge_source_handle=类别ID`。前端为它画出每个类别各一个出口。
3. **读源码**：读 graphon 的 `nodes/list_operator/node.py`，说说它支持哪些操作，再用 mini-dify 的节点基类实现一个简化版。

## 10.6 延伸阅读

- `graphon/nodes/parameter_extractor/`：用 LLM 从文本中抽取结构化参数（Function Calling 和提示词两种模式）
- `graphon/nodes/http_request/executor.py`：完整的 HTTP 节点（文件上传、各种鉴权方式、超时、SSL 配置）
