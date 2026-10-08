"""Figures for the core chapters (3, 8, 9)."""

from svg import FAINT, MUTED, Fig


def fig_three_threads() -> Fig:
    f = Fig(940, 500, "一次运行涉及三类线程：HTTP 线程只读队列并写回 SSE；工作线程跑引擎；节点在引擎的线程池里并行执行。job、事件、命令三条通道把它们连起来。")
    f.title("一次运行里的三类线程", "运行的生命周期与 HTTP 连接解耦：浏览器断开，运行照样完成")
    f.raw('<g transform="translate(0,24)">')
    # lanes
    lanes = [("HTTP 线程（API）", 90), ("工作线程（Runner + 引擎）", 230), ("节点 Worker 线程池", 370)]
    for name, y in lanes:
        f.rect(150, y - 40, 770, 92, fill="#fafafa", stroke="#eef0f3", rx=10)
        f.text(24, y + 10, name, size=12, anchor="start", weight="600", color=MUTED)
    # http lane
    f.box(170, 70, 150, 50, "POST /run", "prepare：建记录、生成 ID", tone="neutral")
    f.box(360, 70, 170, 50, "listen()", "q.get(timeout=10)", tone="accent", mono=False)
    f.box(570, 70, 160, 50, "写回 SSE", "data: {...}\\n\\n", tone="neutral")
    f.box(770, 70, 130, 50, "POST /stop", "另一个请求", tone="bad")
    f.arrow([(320, 95), (360, 95)])
    f.arrow([(530, 95), (570, 95)], "每个事件")
    # queue between lanes
    f.box(360, 160, 170, 34, "事件队列 / Redis Stream", tone="purple", size=11)
    f.arrow([(445, 160), (445, 120)], "取出", tone="purple", label_dx=22, label_dy=4)
    # worker lane
    f.box(170, 210, 150, 50, "engine.run()", "dispatcher 循环", tone="accent")
    f.box(570, 210, 160, 50, "Layer", "持久化 / 执行限制", tone="teal")
    f.box(770, 210, 130, 50, "命令通道", "AbortCommand", tone="bad")
    f.arrow([(245, 120), (245, 210)], "job", tone="neutral", label_dx=16, label_dy=4)
    f.arrow([(320, 228), (400, 228), (420, 194)], "转换后的事件", tone="purple", label_at=0.35)
    f.arrow([(320, 248), (570, 248)], "on_event", tone="teal", label_at=0.75)
    f.arrow([(835, 120), (835, 210)], "send", tone="bad", label_dx=18, label_dy=4)
    f.arrow([(770, 245), (750, 245), (750, 284), (300, 284), (300, 262)], "每 0.1s 轮询", tone="bad", dashed=True, label_at=0.25)
    # node lane
    xs = [190, 330, 470]
    for i, x in enumerate(xs):
        f.box(x, 350, 110, 46, f"node.run()", ["开始", "LLM", "HTTP"][i], tone="neutral", size=12)
    f.box(620, 350, 280, 46, "submit(就绪节点)", "ThreadPoolExecutor 并行执行", tone="neutral", size=12)
    f.arrow([(230, 260), (230, 350)], "submit", label_dx=22, label_dy=4)
    f.arrow([(385, 350), (385, 318), (270, 318), (270, 262)], "事件：Started / Chunk / Succeeded", tone="accent", label_at=0.12, label_dx=95, label_dy=18)
    f.raw('</g>')
    f.text(470, 485, "三条通道：job（往下）· 事件（往上）· 命令（从外面进来）。把它们换成 Celery + Redis，API 和执行端就能分机部署（第 25 章）。", size=12, color=MUTED)
    return f


def _mini_graph(f: Fig, ox: int, oy: int, states: dict, nodes_state: dict, caption: str, step: str):
    """Example B graph: start -> if -> (true) big -> agg; (false) small -> small2 -> agg; agg -> end."""
    pos = {
        "开始": (ox + 10, oy + 70), "IF": (ox + 90, oy + 70), "大数": (ox + 180, oy + 25),
        "小数": (ox + 180, oy + 115), "再处理": (ox + 255, oy + 115), "聚合": (ox + 340, oy + 70), "结束": (ox + 420, oy + 70),
    }
    W, H = 62, 30
    tone_of = {"unknown": "neutral", "taken": "ok", "skipped": "muted", "running": "accent"}
    edges = [("开始", "IF", "e1"), ("IF", "大数", "true"), ("IF", "小数", "false"), ("小数", "再处理", "e4"),
             ("大数", "聚合", "e5"), ("再处理", "聚合", "e6"), ("聚合", "结束", "e7")]
    for a, b, k in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        st = states.get(k, "unknown")
        tone = {"unknown": "neutral", "taken": "ok", "skipped": "muted"}[st]
        p1 = (x1 + W, y1 + H / 2)
        p2 = (x2, y2 + H / 2)
        mid = (p1[0] + p2[0]) / 2
        pts = [p1, (mid, p1[1]), (mid, p2[1]), p2] if p1[1] != p2[1] else [p1, p2]
        f.arrow(pts, tone=tone, dashed=(st == "skipped"), sw=2 if st == "taken" else 1.4)
        if k in ("true", "false"):
            f.text(mid - 5, p2[1] + (-6 if k == "true" else 14), k, size=10, anchor="end", color=MUTED)
    for n, (x, y) in pos.items():
        st = nodes_state.get(n, "unknown")
        f.box(x, y, W, H, n, tone=tone_of[st], size=12, bold=st != "skipped")
    f.text(ox, oy - 8, step, size=13, anchor="start", weight="700")
    f.text(ox + 26, oy - 8, caption, size=12, anchor="start", color=MUTED)


def fig_edge_states() -> Fig:
    f = Fig(1040, 640, "例 B（x=99）的逐步推演：边有 UNKNOWN / TAKEN / SKIPPED 三种状态；IF 选 true 后，未选分支一路跳过直到汇合节点，聚合节点在一条入边 TAKEN、一条 SKIPPED 时就绪。")
    f.title("边的三态 + 就绪规则 + 跳过传播（第 9 章例 B，x = 99）", "就绪 = 入边全部有结论（无 UNKNOWN）且至少一条 TAKEN")
    _mini_graph(f, 30, 110, {"e1": "taken"}, {"开始": "taken", "IF": "running"},
                "开始完成：开始→IF 变 TAKEN，IF 就绪并运行", "① ")
    _mini_graph(f, 540, 110, {"e1": "taken", "false": "skipped", "e4": "skipped", "e6": "skipped", "true": "taken"},
                {"开始": "taken", "IF": "taken", "小数": "skipped", "再处理": "skipped", "大数": "running"},
                "IF 选 true：先跳过 false 分支，传播到聚合时停下", "② ")
    _mini_graph(f, 30, 330, {"e1": "taken", "false": "skipped", "e4": "skipped", "e6": "skipped", "true": "taken", "e5": "taken"},
                {"开始": "taken", "IF": "taken", "小数": "skipped", "再处理": "skipped", "大数": "taken", "聚合": "running"},
                "大数完成：聚合入边 {TAKEN, SKIPPED} → 就绪", "③ ")
    _mini_graph(f, 540, 330, {"e1": "taken", "false": "skipped", "e4": "skipped", "e6": "skipped", "true": "taken", "e5": "taken", "e7": "taken"},
                {"开始": "taken", "IF": "taken", "小数": "skipped", "再处理": "skipped", "大数": "taken", "聚合": "taken", "结束": "taken"},
                "结束完成：未完成集合为空 → 运行结束", "④ ")
    # legend
    y = 560
    f.line(30, y - 22, 1010, y - 22, color="#eef0f3")
    items = [("neutral", "UNKNOWN：还没决定", False), ("ok", "TAKEN：已走过 / 已调度", False), ("muted", "SKIPPED：在未选分支上", True)]
    x = 40
    for tone, lab, dashed in items:
        f.arrow([(x, y), (x + 46, y)], tone=tone, dashed=dashed, sw=2 if tone == "ok" else 1.4)
        f.text(x + 56, y + 4, lab, size=12, anchor="start")
        x += 250
    f.box(x + 10, y - 13, 24, 24, "", tone="accent")
    f.text(x + 44, y + 4, "正在运行", size=12, anchor="start")
    f.text(520, 604, "注意 ②：再处理→聚合 被跳过后，聚合还有一条入边是 UNKNOWN（大数→聚合），所以传播在这里停下；聚合没有被跳过。", size=12, color=MUTED)
    return f


def fig_blackboard() -> Fig:
    f = Fig(980, 400, "两种传数据的方式对比：沿边传递时，结束节点想用开始节点的数据就得让中间每个节点转手；共享变量池（Dify 的选择）里，边只表示顺序，任何节点按 selector 直接读取上游输出。")
    f.title("数据怎么在节点间流动：沿边传递 vs 共享变量池", None)
    # left: along edges
    f.group(20, 60, 450, 300, "方案 A：沿边传递（数据流图）", tone="neutral")
    xs = [40, 145, 250, 355]
    names = ["开始", "HTTP", "LLM", "结束"]
    for x, n in zip(xs, names):
        f.box(x, 110, 90, 40, n, tone="neutral")
    payloads = ["{query}", "{query, body}", "{query, body, text}"]
    for i, p in enumerate(payloads):
        f.arrow([(xs[i] + 90, 130), (xs[i + 1], 130)], tone="neutral")
        f.text((xs[i] + 90 + xs[i + 1]) / 2 + 45 * 0, 180 + i * 22, f"{names[i]} → {names[i+1]}：{p}", size=11.5, color="#b45309", mono=True)
    f.text(245, 270, "结束节点要用 query → 中间每个节点都得转手", size=12, color="#b45309", weight="600")
    f.text(245, 292, "节点之间强耦合；改一个节点的输出会波及下游所有节点", size=12, color=MUTED)
    f.text(245, 330, "（Node-RED、n8n 的 items 模型）", size=11, color=FAINT)
    # right: blackboard
    f.group(500, 60, 460, 300, "方案 B：共享变量池（Dify / mini-dify）", tone="accent")
    xs2 = [520, 625, 730, 835]
    for x, n in zip(xs2, names):
        f.box(x, 110, 90, 40, n, tone="neutral")
    for i in range(3):
        f.arrow([(xs2[i] + 90, 130), (xs2[i + 1], 130)], tone="muted")
    f.text(730, 100, "边只表示执行顺序", size=11, color=MUTED)
    f.box(540, 250, 400, 84, "", tone="accent", rx=10)
    f.text(560, 270, "VariablePool", size=12, anchor="start", weight="700", color="#1e3a8a")
    pool = ["start.query", "http.body", "llm.text", "sys.user_id"]
    for i, p in enumerate(pool):
        f.box(555 + i * 96, 282, 88, 40, p, tone="neutral", size=11, mono=True, bold=False)
    # writes and reads
    f.arrow([(565, 150), (599, 282)], "写", tone="ok", label_at=0.45, label_dx=-8)
    f.arrow([(670, 150), (695, 282)], "写", tone="ok", label_at=0.45, label_dx=-8)
    f.arrow([(760, 282), (765, 150)], "读", tone="accent", label_at=0.6, label_dx=10)
    f.arrow([(880, 150), (887, 282)], "读 llm.text", tone="accent", label_at=0.5, label_dx=22)
    return f


FIGS = {
    "fig-03-three-threads": fig_three_threads,
    "fig-08-blackboard": fig_blackboard,
    "fig-09-edge-states": fig_edge_states,
}
