"""Figures for chapters 0, 1, 4, 6, 10, 11, 12, 15, 16, 18, 20."""

from svg import FAINT, INK, MUTED, Fig, text_width


def fig_overview() -> Fig:
    f = Fig(1040, 430, "mini-dify 总体架构：浏览器通过 HTTP + SSE 访问 API；API 把运行作为 job 交给执行端；引擎调度节点，节点调用模型、工具、知识库；事件经队列或 Redis Stream 回到 API。")
    f.title("mini-dify 总体架构（v1.0）", "和 Dify 同构：API 只收请求、推事件；执行在线程或 Celery Worker 里")
    f.group(20, 70, 210, 330, "浏览器（React）", tone="accent")
    for i, (n, s) in enumerate([("画布编辑器", "React Flow + Zustand"), ("运行 / 追踪面板", "消费 SSE 事件"), ("聊天 · 分享页", "Chatflow / WebApp")]):
        f.box(40, 105 + i * 95, 170, 70, n, s, tone="neutral")
    f.group(270, 70, 230, 330, "API 进程（FastAPI）", tone="neutral")
    for i, (n, s) in enumerate([("控制台 API", "/api/*（登录 + 租户）"), ("开放接口", "/v1 · /web · /mcp · webhook"), ("App Generator", "prepare → 派发 → 订阅")]):
        f.box(290, 105 + i * 95, 190, 70, n, s, tone="accent" if i == 2 else "neutral")
    X = 600
    f.group(X - 20, 70, 440, 330, "执行端（线程 或 Celery Worker）", tone="purple")
    f.box(X, 105, 170, 70, "GraphEngine", "边状态 · 并行 · 分支", tone="purple")
    f.box(X, 200, 170, 70, "节点", "LLM · Agent · Tool · RAG\nCode · HTTP · 迭代", tone="neutral", size=12)
    f.box(X, 300, 170, 70, "Layers", "持久化 · 执行限制", tone="teal")
    f.box(X + 220, 105, 180, 50, "模型", "mock / OpenAI 兼容", tone="neutral", size=12)
    f.box(X + 220, 170, 180, 50, "工具 / MCP", "内置 · OpenAPI · 工作流", tone="neutral", size=12)
    f.box(X + 220, 235, 180, 50, "知识库", "向量 + BM25", tone="neutral", size=12)
    f.box(X + 220, 300, 180, 70, "SQLite / Postgres", "运行记录 · 应用 · 文档", tone="neutral", size=12)
    f.arrow([(210, 140), (290, 140)], "HTTP", tone="accent")
    f.arrow([(290, 330), (210, 330)], "SSE 事件流", tone="accent")
    f.arrow([(480, 320), (530, 320), (530, 130), (X, 130)], "job", tone="neutral", label_at=0.88)
    f.arrow([(X, 155), (556, 155), (556, 345), (480, 345)], "事件", tone="purple", label_at=0.93, dashed=True)
    f.arrow([(X + 85, 175), (X + 85, 200)])
    f.arrow([(X + 170, 220), (X + 220, 130)], tone="muted")
    f.arrow([(X + 170, 235), (X + 220, 195)], tone="muted")
    f.arrow([(X + 170, 250), (X + 220, 260)], tone="muted")
    f.arrow([(X + 170, 335), (X + 220, 335)], "写", tone="teal")
    return f


def fig_app_forms() -> Fig:
    f = Fig(1000, 360, "五种应用形态都可以画成图：Completion 是一条直线，Chat 多了记忆，Agent 是 LLM 和工具之间的循环，Workflow 是任意 DAG，Chatflow 是 DAG 加记忆和流式回复节点。")
    f.title("五种形态，都是图", "越往右，控制流越丰富；Agent 的控制流由模型决定，其余由人画好")
    cols = [("Completion", 20), ("Chat", 210), ("Agent Chat", 400), ("Workflow", 590), ("Chatflow", 790)]
    for name, x in cols:
        f.text(x + 90, 95, name, size=13, weight="700")
    # completion
    def node(x, y, label, tone="neutral", w=70):
        f.box(x, y, w, 30, label, tone=tone, size=11.5)
    node(40, 130, "输入"); node(40, 190, "LLM", "accent"); node(40, 250, "输出")
    f.arrow([(75, 160), (75, 190)]); f.arrow([(75, 220), (75, 250)])
    # chat
    node(230, 130, "问题"); node(230, 190, "LLM", "accent"); node(230, 250, "回答")
    node(325, 190, "记忆", "teal", 60)
    f.arrow([(265, 160), (265, 190)]); f.arrow([(265, 220), (265, 250)])
    f.arrow([(325, 205), (300, 205)], "历史", tone="teal", label_dy=-8, size=10)
    # agent
    node(420, 130, "问题"); node(420, 190, "LLM", "accent"); node(420, 250, "回答")
    node(515, 190, "工具", "warn", 60)
    f.arrow([(455, 160), (455, 190)]); f.arrow([(455, 220), (455, 250)], "完成", size=10, label_dx=18)
    f.arrow([(490, 197), (515, 197)], tone="warn")
    f.arrow([(515, 213), (490, 213)], tone="warn")
    f.text(545, 240, "循环", size=10, color="#b45309")
    # workflow
    node(645, 120, "开始", w=60); node(605, 175, "HTTP", w=60); node(685, 175, "检索", w=60)
    node(645, 230, "LLM", "accent", 60); node(645, 280, "结束", w=60)
    f.arrow([(665, 150), (640, 175)]); f.arrow([(690, 150), (712, 175)])
    f.arrow([(640, 205), (665, 230)]); f.arrow([(712, 205), (690, 230)]); f.arrow([(675, 260), (675, 280)])
    # chatflow
    node(840, 120, "开始", w=60); node(805, 175, "IF", w=50); node(880, 175, "LLM", "accent", 60)
    node(805, 235, "回复A", "ok", 55); node(880, 235, "回复B", "ok", 60); node(945, 175, "记忆", "teal", 45)
    f.arrow([(860, 150), (835, 175)]); f.arrow([(830, 205), (830, 235)]); f.arrow([(845, 190), (880, 190)])
    f.arrow([(910, 205), (910, 235)]); f.arrow([(945, 190), (940, 190)], tone="teal")
    f.text(500, 345, "Dify 的方向：把引擎做成通用的图执行引擎；前三种形态在产品层保留简化配置，底层复用同一套模型 / 记忆 / 工具组件。", size=12, color=MUTED)
    return f


def fig_toolcall_stitch() -> Fig:
    f = Fig(1040, 380, "工具调用的参数是分片到达的：同一个 index 的 id、name、arguments 片段需要按顺序拼接，流结束时才得到完整、可解析的 ToolCall。Provider 层负责拼接，业务代码只拿到最后一片里的完整结果。")
    f.title("流式工具调用：按 index 拼接参数分片", "OpenAI 兼容接口的 delta.tool_calls 实际长这样")
    rows = [
        ('{"delta":{"content":"好的"}}', "文字 → 立刻 yield LLMChunk(delta)", "accent"),
        ('{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"calculator","arguments":""}}]}', "slot[0] ← id, name", "warn"),
        ('{"tool_calls":[{"index":0,"function":{"arguments":"{\\"expre"}}]}', 'slot[0].arguments += \'{"expre\'', "warn"),
        ('{"tool_calls":[{"index":0,"function":{"arguments":"ssion\\": \\"1+1\\"}"}}]}', "slot[0].arguments += 'ssion\": \"1+1\"}'", "warn"),
        ('{"finish_reason":"tool_calls"}  ·  {"usage":{...}}  ·  [DONE]', "收尾：组装完整 ToolCall", "ok"),
    ]
    for i, (raw, act, tone) in enumerate(rows):
        y = 80 + i * 46
        f.text(30, y + 18, "data:", size=11, anchor="start", color=FAINT, mono=True)
        f.box(70, y, 620, 32, raw, tone="neutral", size=10.5, mono=True, bold=False)
        f.arrow([(690, y + 16), (716, y + 16)], tone=tone)
        f.text(724, y + 20, act, size=11.5, anchor="start", color=INK)
    f.box(600, 322, 420, 34, 'ToolCall(call_1, calculator, \'{"expression": "1+1"}\')', tone="ok", size=11, mono=True, bold=False)
    f.arrow([(810, 302), (810, 322)], tone="ok")
    return f


def fig_sse_buffer() -> Fig:
    f = Fig(960, 330, "网络分包不认事件边界也不认字符边界：一次 read 可能停在 JSON 中间、甚至一个汉字的 UTF-8 字节中间。客户端要用流式解码，并按空行切分、把最后一段不完整的内容留在 buffer 里。")
    f.title("SSE 客户端的两个坑：包边界 ≠ 事件边界 ≠ 字符边界", None)
    # stream bytes
    events = ['data: {"event":"text_chunk","text":"你"}', 'data: {"event":"text_chunk","text":"好"}', 'data: {"event":"workflow_finished"}']
    x = 30
    spans = []
    for e in events:
        w = text_width(e, 11) + 30
        f.box(x, 80, w, 34, e, tone="neutral", size=11, mono=True, bold=False)
        f.text(x + w + 2, 102, "\\n\\n", size=10, anchor="start", color=FAINT, mono=True)
        spans.append((x, w))
        x += w + 28
    # packet cuts
    cuts = [spans[0][0] + spans[0][1] * 0.78, spans[1][0] + spans[1][1] * 0.45, spans[2][0] + spans[2][1] * 0.6]
    for i, cx in enumerate(cuts):
        f.line(cx, 66, cx, 128, color="#dc2626", sw=2, dashed=True)
        f.text(cx, 62, f"read() #{i + 1} 结束", size=10.5, color="#dc2626")
    f.text(cuts[0], 146, "切在“你”的 3 个 UTF-8 字节中间", size=11, color="#b91c1c")
    f.text(cuts[1], 146, "切在 JSON 中间", size=11, color="#b91c1c")
    # fix
    f.group(30, 175, 900, 130, "正确的处理", tone="ok")
    f.box(50, 210, 260, 70, "流式解码", "decode(value, { stream: true })\n不完整的字节留到下次再解", tone="ok", size=12)
    f.box(350, 210, 260, 70, "按空行切分", "blocks = buffer.split('\\n\\n')\nbuffer = blocks.pop()  # 残片留着", tone="ok", size=12)
    f.box(650, 210, 260, 70, "每个完整 block", "取 data: 行 → JSON.parse\n→ 按 event 分发", tone="ok", size=12)
    f.arrow([(310, 245), (350, 245)], tone="ok")
    f.arrow([(610, 245), (650, 245)], tone="ok")
    return f


def fig_response_stream() -> Fig:
    f = Fig(980, 380, "回复流协调器按模板顺序输出：文本片段立即输出；当前片段是正在流式输出的 LLM 变量时转发它的 token；后面的变量即使先完成也要等前面的片段输出完；回复节点完成时冲刷剩余片段。")
    f.title("回复流：按 Answer 模板顺序输出", "模板：  翻译：{{#llm1.text#}}  ／  来源：{{#http.body#}}")
    segs = [("翻译：", "text", 60), ("{{#llm1.text#}}", "var", 230), ("／ 来源：", "text", 80), ("{{#http.body#}}", "var", 200)]
    x = 140
    xs = []
    for s, kind, w in segs:
        f.box(x, 80, w, 30, s, tone="accent" if kind == "var" else "neutral", size=11.5, mono=kind == "var", bold=False)
        xs.append((x, w))
        x += w + 10
    f.text(30, 100, "片段（cursor →）", size=11.5, anchor="start", color=MUTED)
    # time axis
    f.arrow([(140, 330), (920, 330)], "时间", tone="neutral", label_at=0.97, label_dy=-8)
    lanes = [("llm1", 165), ("http", 215), ("用户看到", 275)]
    for n, y in lanes:
        f.text(30, y + 5, n, size=12, anchor="start", weight="600", color=MUTED)
    # llm1 streaming 160..600, http done at 300
    f.rect(170, 155, 430, 20, fill="#eff6ff", stroke="#2563eb", rx=4)
    for i in range(12):
        f.line(180 + i * 35, 158, 180 + i * 35, 172, color="#2563eb", sw=1)
    f.text(385, 150, "流式产生 token", size=10.5, color="#2563eb")
    f.rect(170, 205, 140, 20, fill="#f8fafc", stroke="#64748b", rx=4)
    f.circle(310, 215, 5, tone="ok")
    f.text(318, 200, "http 先完成", size=10.5, anchor="start", color="#16a34a")
    # output lane
    f.box(150, 262, 60, 28, "翻译：", tone="ok", size=11, bold=False)
    f.rect(214, 262, 386, 28, fill="#f0fdf4", stroke="#16a34a", rx=6)
    f.text(407, 281, "llm1 的 token 逐个转发（当前片段正好是它）", size=11, color="#14532d")
    f.box(606, 262, 80, 28, "／ 来源：", tone="ok", size=11, bold=False)
    f.box(690, 262, 210, 28, "http.body 完整值（一次性）", tone="ok", size=11, bold=False)
    f.line(310, 225, 310, 262, color="#d97706", sw=1.5, dashed=True)
    f.text(316, 248, "此时 cursor 还在 llm1：http 的值先等着", size=10.5, anchor="start", color="#b45309")
    f.text(490, 365, "若 Answer 在未选中的 IF 分支上：路径上的分支边不全是 TAKEN → 协调器一个字也不输出。", size=12, color=MUTED)
    return f


def fig_iteration_scope() -> Fig:
    f = Fig(940, 360, "迭代的每一轮使用一个子变量池：读取先查自己再回落到外层池，写入只写自己。并行的几轮各自写 sq.y 互不覆盖，最后按序号收集成输出数组。")
    f.title("迭代的子作用域：读回落、写隔离", "items = [3, 1, 2]，并行 3 轮，循环体：sq = item × item")
    f.box(280, 75, 380, 60, "外层变量池", "start.*  ·  make.items = [3, 1, 2]  ·  sys.*", tone="accent", size=13)
    for i, (item, val) in enumerate([(3, 9), (1, 1), (2, 4)]):
        x = 60 + i * 290
        f.box(x, 200, 240, 74, f"第 {i} 轮子池", f"loop.item = {item} · loop.index = {i}\nsq.y = {val}", tone="neutral", size=12.5)
        f.arrow([(x + 120, 200), (x + 120 + (470 - (x + 120)) * 0.35, 135)], "读回落", tone="accent", dashed=True, label_at=0.5, size=10.5)
        f.text(x + 120, 292, "写入只留在本轮", size=11, color="#16a34a")
    f.box(300, 310, 340, 34, "output = [9, 1, 4]（按 index 收集，与完成顺序无关）", tone="ok", size=12)
    return f


def fig_error_flow() -> Fig:
    f = Fig(1100, 380, "节点失败后的处理顺序：先看是否还能重试；重试用完后按错误策略处理：无策略则终止整个运行；默认值策略用默认输出继续走所有出边；异常分支策略只走 fail-branch 出口。后两者让节点以 exception 结束，运行最终为 partial-succeeded。")
    f.title("节点失败之后：重试 → 错误策略", "graphon ErrorHandler.handle_node_failure / mini-dify GraphEngine._on_failed")
    f.box(30, 160, 130, 50, "NodeRunFailed", tone="bad")
    f.box(210, 150, 150, 70, "还能重试？", "retry_enabled 且\n次数 < max_retries", tone="neutral", size=13)
    f.arrow([(160, 185), (210, 185)])
    f.box(210, 280, 150, 56, "NodeRunRetry", "等 retry_interval 后\n重新入队", tone="warn", size=12)
    f.arrow([(285, 220), (285, 280)], "是", tone="warn", label_dx=12, label_dy=4)
    f.arrow([(210, 308), (95, 308), (95, 210)], "再跑一次", tone="warn", dashed=True, label_at=0.4)
    f.box(410, 150, 150, 70, "error_strategy？", tone="neutral", size=13)
    f.arrow([(360, 185), (410, 185)], "否", label_dy=-8)
    outs = [
        ("None（默认）", "终止整个运行", "GraphRunFailed", "bad", 80),
        ("default-value", "输出 = 默认值 + error_message\n照常走所有出边", "节点 exception → partial-succeeded", "warn", 175),
        ("fail-branch", "输出 error_message / error_type\n只走 “fail-branch” 出口", "节点 exception → partial-succeeded", "warn", 285),
    ]
    for label, desc, result, tone, y in outs:
        f.arrow([(560, 185), (600, 185), (600, y + 28), (620, y + 28)], tone="bad" if tone == "bad" else "warn")
        f.text(624, y - 6, label, size=11, anchor="start", color="#b91c1c" if tone == "bad" else "#b45309", mono=True)
        f.box(620, y, 230, 56, desc.split("\n")[0], "\n".join(desc.split("\n")[1:]) or None, tone=tone, size=12)
        f.text(860, y + 33, result, size=11, anchor="start", color="#7f1d1d" if tone == "bad" else "#78350f")
    return f


def fig_optimistic_lock() -> Fig:
    f = Fig(940, 340, "乐观锁：两个标签页都基于 hash h1 编辑；A 先保存成功，服务端 hash 变为 h2；B 带着旧的 h1 保存，服务端发现不匹配返回 409，提示刷新，从而避免 B 悄悄覆盖 A 的修改。")
    f.title("草稿的乐观锁：带着 hash 保存", "Dify unique_hash / WorkflowHashNotEqualError；mini-dify sync_draft")
    lanes = [("标签页 A", 110), ("服务端草稿", 190), ("标签页 B", 270)]
    for n, y in lanes:
        f.text(30, y + 5, n, size=12.5, anchor="start", weight="600", color=MUTED)
        f.line(130, y, 910, y, color="#e5e7eb", sw=1.5)
    f.box(150, 176, 70, 28, "hash h1", tone="neutral", size=11)
    f.arrow([(185, 176), (185, 124)], "加载", tone="neutral", label_dx=18, label_dy=4, size=10)
    f.arrow([(185, 204), (185, 256)], "加载", tone="neutral", label_dx=18, label_dy=4, size=10)
    f.box(300, 96, 150, 28, "编辑 → 保存(h1)", tone="accent", size=11)
    f.arrow([(375, 124), (375, 176)], "h1 == h1 ✓", tone="ok", label_dx=34, label_dy=4, size=10.5)
    f.box(340, 176, 70, 28, "hash h2", tone="ok", size=11)
    f.arrow([(375, 176), (375, 124)], tone="ok") if False else None
    f.box(560, 256, 150, 28, "编辑 → 保存(h1)", tone="accent", size=11)
    f.arrow([(635, 256), (635, 204)], "h1 ≠ h2 ✗", tone="bad", label_dx=34, label_dy=4, size=10.5)
    f.box(600, 176, 70, 28, "仍是 h2", tone="ok", size=11)
    f.box(740, 256, 160, 28, "409：请刷新后再编辑", tone="bad", size=11)
    f.arrow([(710, 270), (740, 270)], tone="bad")
    f.text(470, 325, "保存成功会返回新 hash；请求进行中又有修改时保持“未保存”状态，等下一次防抖保存。", size=12, color=MUTED)
    return f


def fig_available_vars() -> Fig:
    f = Fig(960, 380, "选中节点能引用的变量 = 它的祖先节点的输出（沿入边反向遍历）+ 若在迭代里则还有迭代的 item/index 和迭代外部的祖先 + 系统变量和环境变量；下游和无关分支上的节点不可选。")
    f.title("可用变量 = 祖先节点的输出", "沿入边反向 DFS（Dify getBeforeNodesInSameBranchIncludeParent / mini-dify availableVars）")
    def n(x, y, label, tone, w=86):
        f.box(x, y, w, 34, label, tone=tone, size=12)
    n(30, 170, "开始", "ok"); n(150, 120, "HTTP", "ok"); n(150, 220, "IF", "ok"); n(270, 245, "检索", "muted")
    f.group(390, 80, 330, 170, "迭代（parentId 子图）", tone="purple")
    n(410, 140, "迭代开始", "ok", 86); n(530, 140, "LLM", "accent", 86); n(640, 200, "代码", "muted", 70)
    n(760, 150, "汇总", "muted"); n(870, 150, "结束", "muted", 70)
    for a, b, tone in [((116, 187), (150, 137), "ok"), ((116, 187), (150, 237), "ok"), ((236, 245), (270, 260), "muted"), ((236, 137), (390, 160), "ok")]:
        f.arrow([a, b], tone=tone)
    f.arrow([(496, 157), (530, 157)], tone="ok"); f.arrow([(616, 165), (640, 210)], tone="muted")
    f.arrow([(720, 167), (760, 167)], tone="muted"); f.arrow([(846, 167), (870, 167)], tone="muted")
    f.text(573, 128, "选中", size=11, color="#2563eb", weight="700")
    f.box(30, 300, 640, 62, "", tone="accent", rx=10)
    f.text(46, 322, "LLM 节点的变量选择器里会出现：", size=12, anchor="start", weight="700", color="#1e3a8a")
    f.text(46, 346, "迭代.item / 迭代.index（当前项） · 开始.* · HTTP.body … · IF.result … · sys.* · env.*", size=12, anchor="start", mono=False)
    f.text(690, 322, "不会出现：代码（下游）、汇总 / 结束（迭代之后）、", size=11.5, anchor="start", color=MUTED)
    f.text(690, 342, "检索（另一条分支，不是 LLM 的祖先）", size=11.5, anchor="start", color=MUTED)
    return f


def fig_fc_vs_react() -> Fig:
    f = Fig(980, 420, "两种 Agent 策略的同一次调用：Function Calling 由模型 API 返回结构化 tool_calls，结果以 tool 消息回填；ReAct 由提示词约定文本格式，平台在 Observation 前截停、解析 JSON、把结果写进 scratchpad 再让模型继续。")
    f.title("同一个问题，两种 Agent 策略", "问：1234 × 5678 等于多少？  工具：calculator(expression)")
    for x, title, tone in [(20, "Function Calling（结构化 tool_calls）", "accent"), (500, "ReAct（文本格式 + 解析）", "purple")]:
        f.group(x, 70, 460, 330, title, tone=tone)
    fc = [
        ("→ 模型", "messages + tools=[calculator 的 JSON Schema]", "neutral"),
        ("← 模型", "tool_calls=[{id: call_1, name: calculator,\n  arguments: {\"expression\": \"1234*5678\"}}]", "accent"),
        ("平台", "执行 calculator → \"1234*5678 = 7006652\"", "warn"),
        ("→ 模型", "追加 assistant(tool_calls) + tool(call_1, 结果)", "neutral"),
        ("← 模型", "最终回答（不再有 tool_calls）", "ok"),
    ]
    rc = [
        ("→ 模型", "system: ReAct 模板（工具列表 + 格式）\nstop=[\"Observation:\"]", "neutral"),
        ("← 模型", "Thought: 用计算器\nAction: ```{\"action\": \"calculator\", ...}```", "purple"),
        ("平台", "解析 JSON → 执行 → 写入 scratchpad：\nObservation: 1234*5678 = 7006652", "warn"),
        ("→ 模型", "Question + scratchpad（含 Observation）", "neutral"),
        ("← 模型", "Action: {\"action\": \"Final Answer\", ...}", "ok"),
    ]
    for x0, rows in [(30, fc), (510, rc)]:
        for i, (who, what, tone) in enumerate(rows):
            y = 95 + i * 60
            f.text(x0 + 8, y + 26, who, size=11.5, anchor="start", weight="600", color=MUTED)
            lines = what.split("\n")
            f.box(x0 + 62, y, 378, 48, lines[0], "\n".join(lines[1:]) or None, tone=tone, size=11, bold=False, mono=True)
    return f


def fig_mcp() -> Fig:
    f = Fig(940, 420, "MCP 的四条消息：initialize 握手、initialized 通知（无回复）、tools/list 拿到工具及 JSON Schema、tools/call 调用工具；同样的 JSON-RPC 消息可以走 stdio（子进程的一行一条）或 Streamable HTTP（每条一个 POST，回复可为 JSON 或 SSE）。")
    f.title("MCP：JSON-RPC 2.0 上的四条消息", None)
    f.box(60, 60, 200, 40, "MCP 客户端", "mini-dify / Dify / Claude Desktop", tone="accent", size=12)
    f.box(680, 60, 200, 40, "MCP Server", "你的服务 / 工作流", tone="purple", size=12)
    f.line(160, 100, 160, 380, color="#93c5fd", sw=2, dashed=True)
    f.line(780, 100, 780, 380, color="#c4b5fd", sw=2, dashed=True)
    msgs = [
        (130, "→", 'initialize {protocolVersion, capabilities, clientInfo}', "accent"),
        (165, "←", '{protocolVersion, capabilities: {tools: {}}, serverInfo}', "purple"),
        (210, "→", 'notifications/initialized   （通知：没有 id，不回复）', "muted"),
        (255, "→", 'tools/list', "accent"),
        (290, "←", '{tools: [{name, description, inputSchema}]}', "purple"),
        (335, "→", 'tools/call {name, arguments}', "accent"),
        (370, "←", '{content: [{type: "text", text}], isError}', "purple"),
    ]
    for y, d, label, tone in msgs:
        pts = [(165, y), (775, y)] if d == "→" else [(775, y), (165, y)]
        f.arrow(pts, tone=tone, dashed=tone == "muted")
        f.text(470, y - 6, label, size=11.5, mono=True, color=INK if tone != "muted" else MUTED)
    f.text(470, 405, "传输：stdio（子进程，一行一条 JSON）· Streamable HTTP（POST；回复 JSON 或 SSE；Mcp-Session-Id 头）", size=11.5, color=MUTED)
    return f


FIGS = {
    "fig-00-overview": fig_overview,
    "fig-01-app-forms": fig_app_forms,
    "fig-04-toolcall-stitch": fig_toolcall_stitch,
    "fig-06-sse-buffer": fig_sse_buffer,
    "fig-10-response-stream": fig_response_stream,
    "fig-11-iteration-scope": fig_iteration_scope,
    "fig-12-error-flow": fig_error_flow,
    "fig-15-optimistic-lock": fig_optimistic_lock,
    "fig-16-available-vars": fig_available_vars,
    "fig-18-fc-vs-react": fig_fc_vs_react,
    "fig-20-mcp": fig_mcp,
}
