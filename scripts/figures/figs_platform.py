"""Figures for chapters 22, 23, 24, 25, 27."""

from svg import FAINT, INK, MUTED, Fig


def fig_chunking() -> Fig:
    f = Fig(980, 400, "两种分段：通用分段按长度切块并让相邻块重叠，防止关键句被切断；父子分段用小的子块做匹配、命中后返回它所属的大父块，兼顾检索精度和上下文完整。")
    f.title("分段：重叠 与 父子", "chunk_size 控制长度；overlap 让边界附近的内容在两块里都出现")
    # overlap row
    f.text(24, 95, "通用分段", size=12.5, anchor="start", weight="700")
    f.rect(120, 80, 820, 26, fill="#f8fafc", stroke="#cbd5e1", rx=4)
    f.text(530, 98, "原文 ……第三章 退款政策。购买后七天内可以无理由退款，超过七天需要提供质量问题证明。第四章……", size=11, color=MUTED)
    chunks = [(120, 330, "chunk 1"), (390, 330, "chunk 2"), (660, 280, "chunk 3")]
    for i, (x, w, label) in enumerate(chunks):
        y = 122 + (i % 2) * 34
        f.box(x, y, w, 26, label, tone="accent" if i != 1 else "teal", size=11)
    for x0, x1 in [(390, 450), (660, 720)]:
        f.rect(x0, 118, x1 - x0, 68, fill="#fef3c7", stroke="#d97706", rx=4, dashed=True)
        f.text((x0 + x1) / 2, 200, "overlap", size=10.5, color="#b45309")
    # parent child
    f.text(24, 255, "父子分段", size=12.5, anchor="start", weight="700")
    f.box(120, 232, 520, 46, "父块：第三章 退款政策。购买后七天内……超过七天需要提供质量问题证明。", tone="purple", size=11.5, bold=False)
    for i, t in enumerate(["子块 a：购买后七天内", "子块 b：可以无理由退款", "子块 c：超过七天需证明"]):
        f.box(120 + i * 175, 310, 165 if i < 2 else 170, 34, t, tone="neutral" if i != 2 else "ok", size=10.5, bold=False)
        f.arrow([(200 + i * 175, 310), (200 + i * 175, 278)], tone="purple", dashed=True)
    f.box(700, 300, 240, 54, "问：超过七天需要什么？", "向量 / BM25 命中 子块 c", tone="ok", size=12)
    f.arrow([(700, 327), (640, 327)], "匹配", tone="ok", label_dy=-8)
    f.arrow([(820, 300), (820, 255), (640, 255)], "返回整个父块", tone="purple", label_at=0.6)
    f.text(490, 385, "小块检索准（语义集中），大块上下文全：父子分段把“匹配单元”和“返回单元”分开。", size=12, color=MUTED)
    return f


def fig_hybrid() -> Fig:
    f = Fig(980, 345, "混合检索：同一个查询分别算向量相似度和 BM25 分数；BM25 没有上界，先除以最大值归一化到 0~1，再按权重相加排序。图中数字来自书中召回测试的真实结果：0.7×0.17 + 0.3×1.0 ≈ 0.42。")
    f.title("混合检索：两路打分 → 归一化 → 加权融合", "查询：“怎么退款”   向量权重 0.7 / 关键词权重 0.3")
    f.box(30, 160, 120, 50, "查询", "怎么退款", tone="accent")
    f.box(210, 90, 200, 56, "向量检索", "cos(查询向量, 分段向量)", tone="neutral", size=12)
    f.box(210, 220, 200, 56, "全文检索 BM25", "tf · idf · 长度归一", tone="neutral", size=12)
    f.arrow([(150, 175), (210, 118)], "embedding", label_dy=-4, size=10.5)
    f.arrow([(150, 195), (210, 248)], "分词（中文二元组）", label_dy=14, size=10.5)
    f.box(450, 220, 150, 56, "÷ max", "BM25 → [0, 1]", tone="warn", size=12)
    f.arrow([(410, 248), (450, 248)], "3.7, 1.2, 0…", size=10, label_dy=-8)
    f.box(640, 150, 140, 70, "加权求和", "0.7·v + 0.3·k", tone="purple", size=12)
    f.arrow([(410, 118), (710, 118), (710, 150)], "0.17, 0.30, 0.15…", tone="neutral", label_at=0.4, size=10)
    f.arrow([(600, 248), (710, 248), (710, 220)], "1.00, 0.32, 0…", tone="warn", label_at=0.35, size=10)
    # ranked list
    rows = [("第三章 退款政策", "0.7×0.17 + 0.3×1.00 = 0.42", "ok"), ("第一章 安装", "0.7×0.30 + 0.3×0.00 = 0.21", "neutral"), ("第二章 工作流", "0.7×0.15 + 0.3×0.00 = 0.11", "neutral")]
    for i, (t, sc, tone) in enumerate(rows):
        f.box(810, 100 + i * 52, 150, 42, t, sc, tone=tone, size=11, bold=i == 0)
    f.arrow([(780, 185), (810, 185)], tone="purple")
    f.text(490, 322, "示例中向量分数来自 mock 哈希向量（语义很弱），是关键词把正确答案顶到第一：这正是混合检索的价值。下两行为示意数值。", size=11.5, color=MUTED)
    return f


def fig_tenancy() -> Fig:
    f = Fig(1000, 400, "三类调用者用三种凭证进入平台：控制台用户用登录 token（每次从数据库确认成员和角色）、API 调用方用应用 API Key（只能调用该应用的已发布版本）、访客通过分享链接（应用需显式开启）。所有数据访问都带 tenant_id 过滤，跨租户访问返回 404。")
    f.title("三类调用者，三种凭证，一条隔离红线", None)
    callers = [
        ("控制台用户", "Bearer 登录 token\n{sub, tid, exp} + HMAC", "accent", "console_ctx → 成员 + 角色\neditor_ctx / admin_ctx"),
        ("API 调用方", "Bearer app-xxxx", "purple", "app_from_api_key → 一个应用\n只跑已发布版本"),
        ("访客", "/share/<site_code>", "teal", "site_enabled 才可用\n匿名 user = visitor-xxx"),
    ]
    for i, (who, cred, tone, check) in enumerate(callers):
        y = 70 + i * 100
        f.box(30, y, 150, 70, who, tone=tone, size=13)
        f.box(220, y + 8, 200, 54, cred.split("\n")[0], "\n".join(cred.split("\n")[1:]) or None, tone="neutral", size=11.5, mono=True, bold=False)
        f.box(470, y + 5, 250, 60, check.split("\n")[0], check.split("\n")[1], tone=tone, size=11.5, bold=False)
        f.arrow([(180, y + 35), (220, y + 35)], tone=tone)
        f.arrow([(420, y + 35), (470, y + 35)], tone=tone)
        f.arrow([(720, y + 35), (770, y + 35)], tone=tone)
    f.box(770, 70, 210, 270, "", tone="neutral", rx=12)
    f.text(875, 95, "数据访问层", size=12.5, weight="700")
    for i, t in enumerate(["apps", "datasets", "tool_providers", "provider_credentials"]):
        f.box(790, 108 + i * 47, 170, 40, t, "WHERE tenant_id = :tid", tone="neutral", size=11, mono=True, bold=False)
    f.text(875, 310, "RunContext.tenant_id 一路传到", size=11, color=MUTED)
    f.text(875, 326, "模型凭证 · 检索 · 工具", size=11, color=MUTED)
    f.box(30, 360 - 10, 690, 34, "别的租户的资源 → 404（不是 403：不泄露“它存在”）", tone="bad", size=12)
    return f


def fig_scale_out() -> Fig:
    f = Fig(1000, 460, "横向扩展：API 实例只负责 prepare、订阅事件、发送命令；job 经 Celery 队列交给任意 worker；worker 把事件 XADD 到每个任务一条的 Redis Stream，API 用 XREAD BLOCK 读取并推成 SSE；停止命令 RPUSH 到任务的命令列表，引擎轮询时原子地取走。")
    f.title("v1.0 横向扩展：三条通道都过 Redis", "EXECUTION_MODE=worker + REDIS_URL")
    for i in range(2):
        y = 75 + i * 175
        f.group(30, y, 240, 160, f"API 实例 #{i + 1}", tone="accent")
        f.box(50, y + 30, 205, 34, "prepare → job", tone="neutral", size=11.5)
        f.box(50, y + 72, 205, 34, "subscribe(task_id) → SSE", tone="accent", size=11.5)
        f.box(50, y + 114, 205, 34, "POST /stop → send(Abort)", tone="bad", size=11.5)
    f.group(370, 70, 260, 350, "Redis", tone="bad")
    f.box(390, 100, 220, 60, "Celery 队列", "mini_dify.run_workflow(job)", tone="neutral", size=12)
    f.box(390, 200, 220, 70, "Stream", "mini-dify:events:{task_id}\nXADD / XREAD BLOCK", tone="purple", size=12)
    f.box(390, 320, 220, 70, "List", "mini-dify:commands:{task_id}\nRPUSH / LRANGE+DEL", tone="bad", size=12)
    for i in range(3):
        y = 100 + i * 110
        f.box(740, y, 230, 70, f"Celery Worker #{i + 1}", "execute(job)：引擎 + 节点", tone="purple", size=12)
    f.arrow([(255, 122), (390, 128)], "send_task", label_at=0.5, size=10.5)
    f.arrow([(610, 130), (740, 133)], "取 job", label_at=0.5, size=10.5)
    f.arrow([(740, 240), (610, 235)], "XADD 事件", tone="purple", label_at=0.5, size=10.5)
    f.arrow([(390, 225), (255, 164)], "XREAD BLOCK", tone="purple", label_at=0.5, size=10.5)
    f.arrow([(390, 245), (255, 339)], "XREAD BLOCK", tone="purple", label_at=0.5, size=10.5)
    f.arrow([(255, 381), (390, 360)], "RPUSH", tone="bad", label_at=0.5, size=10.5)
    f.arrow([(610, 355), (740, 355)], "每 0.1s 取命令", tone="bad", label_at=0.5, size=10.5, dashed=True)
    f.text(500, 445, "任何一个 API 实例都能服务任何任务的 SSE 和停止；Stream 是日志而不是管道，先发布的事件不会丢。", size=12, color=MUTED)
    return f


def fig_ssrf() -> Fig:
    f = Fig(980, 330, "SSRF 防护必须在每一跳都检查：第一次请求访问公网域名，解析出公网 IP，检查通过；对方返回 302 跳到 169.254.169.254（云服务器元数据），跟随重定向时 httpx 的 request 事件钩子再次检查，发现是链路本地地址，拒绝。")
    f.title("SSRF：每一跳都要检查解析后的 IP", "mini-dify safe_client = httpx event_hooks['request']；Dify 交给 Squid 代理（DNS 在代理侧解析）")
    f.box(30, 130, 150, 60, "HTTP 节点", "用户配置的 URL", tone="neutral")
    f.box(250, 80, 190, 54, "check_url ①", "attacker.com → 203.0.113.7", tone="ok", size=12)
    f.box(520, 80, 190, 54, "attacker.com", "返回 302 Location:", tone="warn", size=12)
    f.box(250, 210, 190, 54, "check_url ②", "169.254.169.254", tone="bad", size=12)
    f.box(520, 210, 190, 54, "云元数据服务", "IAM 凭证……", tone="muted", size=12)
    f.box(770, 130, 180, 60, "SSRFError", "禁止访问内网地址", tone="bad")
    f.arrow([(180, 150), (250, 107)], "请求", size=10.5)
    f.arrow([(440, 107), (520, 107)], "公网 ✓", tone="ok")
    f.arrow([(615, 134), (615, 170), (345, 170), (345, 210)], "跟随重定向", tone="warn", label_at=0.5)
    f.arrow([(440, 237), (520, 237)], "✗ 不会发出", tone="muted", dashed=True)
    f.arrow([(440, 225), (770, 165)], "is_link_local", tone="bad", label_at=0.6)
    f.text(490, 305, "拦截：private · loopback · link-local · reserved · multicast · unspecified；协议只允许 http/https。剩余缺口：DNS 重绑定（用代理或固定已解析 IP 解决）。", size=11.5, color=MUTED)
    return f


FIGS = {
    "fig-22-chunking": fig_chunking,
    "fig-23-hybrid": fig_hybrid,
    "fig-24-tenancy": fig_tenancy,
    "fig-25-scale-out": fig_scale_out,
    "fig-27-ssrf": fig_ssrf,
}
