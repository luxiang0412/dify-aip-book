# 第 6 章 流式输出与事件协议

> 本章目标：掌握 SSE 协议和它在 AI 平台里的用法；读懂 Dify 的事件协议；在服务端和浏览器端各写一份流式实现，并避开常见的坑。
> 前置：第 3、4 章。对应代码：mini-dify **v0.1** `backend/app/sse.py`、`frontend/src/lib/sse.ts`。

## 6.1 问题：为什么必须流式

一个 LLM 回答 500 字大约需要 10 秒。如果等全部生成完再返回，用户要盯着空白屏幕等 10 秒；如果边生成边推送，第一个字在 0.5 秒内就能出现。**首字延迟**（TTFT, Time To First Token）是 AI 产品体验最重要的指标之一。

工作流把这个问题放大了：一次运行可能要跑十几个节点、几分钟。用户需要看到的不只是文字，还有“现在跑到哪个节点了”“哪个节点失败了”。所以平台要推送的是一串**结构化事件**，而不只是一串文字。

## 6.2 SSE 协议速览

Server-Sent Events 是 HTML 标准的一部分，本质上就是**一个永远不结束的 HTTP 响应**：

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

data: {"event": "node_started", ...}

data: {"event": "text_chunk", "data": {"text": "你"}}

event: ping

data: {"event": "workflow_finished", ...}

```

规则：

- 每个事件由若干行 `字段: 值` 组成，**以一个空行（`\n\n`）结束**；
- 常用字段：`data`（内容，可以多行）、`event`（事件类型）、`id`（断线重连时使用）、`retry`（重连间隔）；
- 以 `:` 开头的行是注释，常用来做心跳。

**Dify 的约定**：几乎只用 `data:` 字段，**事件类型放在 JSON 里面**（`{"event": "node_started", ...}`），心跳则用 `event: ping`（`api/core/app/apps/base_app_generator.py:324-326`）。把事件类型放进 JSON 有一个好处：客户端只需要处理“一行 JSON”这一种格式，SDK 写起来更简单。

### 为什么不用 WebSocket？

| | SSE | WebSocket |
|---|---|---|
| 方向 | 服务端 → 客户端 | 双向 |
| 协议 | 普通 HTTP | 需要协议升级 |
| 代理 / 网关 / CDN 兼容性 | 好（就是 HTTP） | 经常需要单独配置 |
| 鉴权 | 普通的 header / cookie | 握手阶段处理，较麻烦 |
| 一次请求对应一次运行 | 天然 | 要自己做请求和响应的匹配 |

AI 平台的模式是“发一个请求，收一串事件”，SSE 正好对口。需要反向通信时（比如“停止”），另发一个普通 HTTP 请求就行（第 3 章 3.9）。Dify 也有 WebSocket 服务（`api_websocket`），但只用在多人协同编辑这类真正需要双向通信的场景。

## 6.3 Dify 的事件协议

### 6.3.1 事件清单

`api/core/app/entities/task_entities.py:62` `class StreamEvent`：

| 分组 | 事件 | 何时发出 |
|---|---|---|
| 心跳/错误 | `ping`、`error` | 每 10 秒 / 出错 |
| 消息（Chat 系） | `message`、`message_end`、`message_file`、`message_replace`、`tts_message`、`tts_message_end` | 回复的文字片段 / 结束（带 usage）/ 文件 / 内容审核后替换 / 语音 |
| Agent | `agent_thought`、`agent_message` | Agent 每一步思考 / Agent 的回复文字 |
| 工作流 | `workflow_started`、`workflow_finished`、`workflow_paused` | 运行开始 / 结束 / 等待人工输入而暂停 |
| 节点 | `node_started`、`node_finished`、`node_retry` | 每个节点 |
| 容器 | `iteration_started/next/completed`、`loop_started/next/completed` | 迭代 / 循环的每一轮 |
| 文字 | `text_chunk`、`text_replace`、`reasoning_chunk` | 工作流输出文字 / 替换 / 推理模型的思考过程 |
| 其他 | `agent_log`、`human_input_required`、`human_input_form_filled`、`human_input_form_timeout` | Agent 节点日志 / 人工介入 |

### 6.3.2 事件结构

所有事件共享一个“信封”：

```json
{
  "event": "node_finished",
  "task_id": "用于停止任务",
  "workflow_run_id": "运行 ID",
  "data": { ... 事件本身的数据 ... }
}
```

`node_finished.data` 的主要字段（`NodeFinishStreamResponse`，`task_entities.py:424`）：

```json
{
  "id": "节点执行 ID",
  "node_id": "画布上的节点 ID",
  "node_type": "llm",
  "title": "LLM",
  "index": 2,
  "inputs": {...},
  "process_data": {"prompts": [...]},
  "outputs": {"text": "..."},
  "status": "succeeded | failed | exception",
  "error": null,
  "elapsed_time": 1.23,
  "execution_metadata": {"total_tokens": 123, ...}
}
```

Chatflow 用 `message` 事件推送回复文字（字段名是 `answer`），Workflow 用 `text_chunk`（字段是 `data.text`）。这是历史原因：Chat 系应用比工作流出现得早，它的协议沿用到了 Chatflow。

### 6.3.3 流式和阻塞两种模式

Service API 的请求体里有 `response_mode: "streaming" | "blocking"`。阻塞模式下服务端照样跑一遍流式流程，只是在服务端把事件收集完，最后返回一个 JSON（`generate_response_converter.py`）。**内部只有一种执行方式**，阻塞只是外面多包的一层。

## 6.4 从零实现：服务端

### 6.4.1 SSE 帮助函数

```python
# backend/app/sse.py
def sse_line(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

def sse_response(events: Iterable[dict]) -> StreamingResponse:
    def body():
        for event in events:
            yield sse_line(event)
    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

两个 header 都很关键：

- `Cache-Control: no-cache`：不要让任何中间层缓存这个响应；
- `X-Accel-Buffering: no`：告诉 nginx **不要缓冲**。nginx 默认会攒满一个缓冲区再转发，结果就是用户看到的文字一大块一大块地蹦出来。v1.0 的 nginx 配置里同样写了 `proxy_buffering off;`（第 28 章）。

`ensure_ascii=False` 让中文直接以 UTF-8 输出，而不是转成 `你`，抓包调试时可读性好得多。

### 6.4.2 同步生成器 + FastAPI

v0.1 的聊天接口是一个**同步**的生成器：

```python
@router.post("/api/chat-messages")
def chat(req: ChatRequest):              # 注意：不是 async def
    return sse_response(_generate(req))

def _generate(req) -> Iterator[dict]:
    ...
    for chunk in get_model(req.model).invoke(messages):    # 阻塞地读取模型的流
        if chunk.delta:
            yield {"event": "message", "answer": chunk.delta, **base}
    yield {"event": "message_end", "metadata": {"usage": ...}, **base}
```

`StreamingResponse` 遇到同步迭代器时，会把每次 `next()` 放到线程池里执行，所以不会阻塞事件循环。这和 Dify 的 Flask + gevent/线程模型在原理上是一样的：**每个流式请求占用一个线程**。这对 AI 平台来说是可以接受的，因为真正的瓶颈在模型那边，而不在线程数上。

### 6.4.3 错误也是事件

```python
try:
    for chunk in get_model(req.model).invoke(messages):
        ...
except LLMError as e:
    yield {"event": "error", "message": str(e), "status": 500, **base}
    return
```

流一旦开始，HTTP 状态码就已经是 200，没法再改了。所以**流中途发生的错误只能作为一个事件发送**。客户端必须处理 `error` 事件，不能只看状态码。

## 6.5 从零实现：浏览器端

```ts
// frontend/src/lib/sse.ts
export async function ssePost(url, body, onEvent, signal?, headers = {}) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
    signal,                                     // 用于“停止接收”
  })
  if (!resp.ok || !resp.body) {
    onEvent({ event: 'error', message: `HTTP ${resp.status}: ${await resp.text()}` })
    return
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })     // ← 坑 1
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''                            // ← 坑 2
    for (const block of blocks)
      for (const line of block.split('\n'))
        if (line.startsWith('data: ')) {
          try { onEvent(JSON.parse(line.slice(6))) } catch { /* 忽略坏行 */ }
        }
  }
}
```

这十几行代码里藏着两个经典的坑：

**坑 1：多字节字符被切断。** 网络分包不关心字符边界，一个中文字符的 3 个 UTF-8 字节可能分散在两个包里。`decoder.decode(value, { stream: true })` 会把不完整的字节留到下一次再解码。如果不加 `stream: true`，你会时不时看到 `�`。

**坑 2：一个事件被切成两半。** 一次 `read()` 拿到的数据可能在 JSON 中间结束。所以要按 `\n\n` 切分，**最后一段（可能不完整）留在 buffer 里**，等下一次读取再拼接。

Dify 的 `web/service/base.ts` 里有同样的处理（它按 `\n` 切行，并用 `bufferObj` 状态做累积）。

### 停止接收 ≠ 停止运行

```ts
abort.current = new AbortController()
await ssePost(url, body, onEvent, abort.current.signal)
// 用户点“停止”：
abort.current.abort()
```

`abort()` 只是让浏览器**不再接收**这条连接上的数据。服务端的运行要不要继续，取决于服务端怎么设计。

- v0.1 的聊天接口：连接断开后，`StreamingResponse` 下一次写入时失败，生成器被关闭，模型调用也就跟着停了；
- 工作流（v0.2 起）：运行在独立的工作线程里，**连接断开后运行会继续**，结果照样落库。要真正停止，必须调用 `/workflow-runs/tasks/{task_id}/stop`（第 3 章 3.9，第 12 章）。

这是有意为之的设计：用户刷新一下页面，不应该把一个跑了 5 分钟的工作流也一起杀掉。

## 6.6 运行与验证

```bash
cd code/mini-dify && git checkout v0.1
cd backend && uv run uvicorn app.main:app --port 5001
# 另一个终端
curl -N -X POST localhost:5001/api/chat-messages -H 'Content-Type: application/json' -d '{"query":"你好"}'
```

`-N` 关闭 curl 的输出缓冲，你会看到事件一行一行地出现：

```
data: {"event": "message", "answer": "（", "conversation_id": "...", "message_id": "..."}

data: {"event": "message", "answer": "m", ...}
...
data: {"event": "message_end", "metadata": {"usage": {"prompt_tokens": 9, "completion_tokens": 10, "total_tokens": 19}, "latency": 0.31}, ...}
```

再启动前端（`cd frontend && npm install && npm run dev`），打开 http://localhost:3000 ，看浏览器里的流式效果。用 DevTools 的 Network 面板查看这个请求的 EventStream 标签页。

## 6.7 练习

1. **巩固**：用 Python 的 httpx 写一个 SSE 客户端，打印出所有 `message` 事件拼接后的完整回答。注意处理坑 2。
2. **扩展**：给 SSE 加上 `id:` 字段（事件序号），并实现“断线续传”：客户端重连时带上 `Last-Event-ID`，服务端从那个位置继续推送。（提示：v1.0 的 Redis Stream 天然支持从指定位置读取，见第 25 章。）
3. **读源码**：读 Dify 的 `api/core/app/apps/workflow/generate_response_converter.py`，看阻塞模式下返回的 JSON 结构，和流式模式下的 `workflow_finished` 事件做个对比。

## 6.8 延伸阅读

- WHATWG HTML 标准中的 Server-sent events 章节
- `web/service/base.ts`：Dify 前端完整的 `ssePost`，包括错误处理和 401 时刷新 token
- Dify API 文档（应用的“访问 API”页）：Service API 的流式事件说明
