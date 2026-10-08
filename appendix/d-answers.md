# 附录 D 练习参考答案

> 巩固题给出完整答案；扩展题给出实现要点或思路；读源码题给出定位和结论。答案不唯一，能讲清楚“为什么”就行。

## 第 1 章

1. Chat 和 Chatflow 的区别：① Chat 的逻辑固定（提示词 → LLM），Chatflow 可以是任意 DAG；② Chatflow 用 Answer 节点流式回复，并且可以有多个 Answer 分布在不同分支上；③ Chatflow 可以使用会话变量、知识检索、代码、工具等节点，每轮对话都对应一次工作流运行（会留下运行记录）。
2. 开始节点设置 text、language 两个输入；LLM 的 user 提示词写 `把下面内容翻译成{{#start.language#}}：{{#start.text#}}`；不开启记忆；结束节点输出 `llm.text`。
3. `MessageBasedAppGenerator` 会创建 Conversation 和 Message 记录，并按“消息”的方式组织输出（`message` / `message_end` 事件）。Workflow 是一次性运行，没有会话，它的产物是 `workflow_runs` 记录，所以不继承它。

## 第 2 章

1. 浏览器 → nginx → api（保存文件，创建 Document，状态为 waiting）→ 把 Celery 任务投递到 Redis 的 dataset 队列 → worker 取出任务：从存储读取文件 → 提取 / 清洗 / 分段 → 调用 embedding（经由 plugin_daemon 访问模型）→ 写入向量库 + 写入 document_segments → 更新状态为 completed。前端轮询 api 获取状态。
2. ping 大约每 10 秒出现一次，用来在长时间没有数据时保持连接，防止代理或负载均衡因为空闲超时而断开。
3. 扩展有依赖关系：Celery 的配置、任务执行需要数据库会话和 app 上下文，所以 `ext_database` 必须先初始化。具体顺序以 `app_factory.py` 中的列表为准。

## 第 3 章

1. HTTP 线程（准备环境、读取队列、写回 SSE）、工作线程（Runner + 引擎）、引擎的 Worker 线程池（执行节点）。job：HTTP 线程 → 工作线程；事件：节点 → 引擎 → Runner → 队列 → HTTP 线程；命令：stop 接口 → 命令通道 → 引擎。
2. 会看到在 3 秒的 sleep 期间，每秒出现一个 `{"event": "ping"}`。
3. 收尾时会保存工作流的运行日志（`_save_workflow_app_log`）、保存节点输出（草稿变量），并且关闭 TTS 等资源，然后再发出 `workflow_finished` 事件。

## 第 4 章

1. 因为业务代码只关心“完整的工具调用”。如果改成每一片都带增量，所有调用方都要自己按 index 拼接 id、name、arguments，还要判断什么时候拼完了。把拼接收敛到 Provider 里，只需要做一次。
2. 要点：请求体是 `{model, system, messages, tools, stream: true, max_tokens}`；流式事件里 `content_block_delta` 的 `text_delta` 是文字增量，`input_json_delta` 是工具参数的增量，需要按 content block 的 index 拼接；`message_delta` 里有 usage 和 stop_reason。注册方式是 `register_provider(AnthropicProvider())`。
3. 遇到限流（RateLimit）时，把当前凭证冷却一段时间，然后换下一组凭证继续重试；遇到授权错误（Authorization）时，说明凭证本身无效，同样要标记，但换凭证的语义不同。具体以源码中的分支为准：一个是暂时不可用，一个是永久不可用。

## 第 5 章

1. 失败的那一轮可能只有问题没有回答，或者回答只生成了一半。把它写进历史，下一轮模型就会看到一个残缺的上下文，可能出现重复回答、自相矛盾等问题。
2. 在循环里同时计数：`if used + cost > max_tokens or len(kept) >= max_messages: break`。面板的记忆配置项里加一个 size 输入框，绑定到 `memory.window.size`。
3. 消息之间通过 `parent_message_id` 形成一棵树。从最新的一条消息开始，沿着 parent 链往回走，得到的就是当前分支；其他分支（重新生成前的旧回答）不在这条链上。

## 第 6 章

1. 用 `httpx.stream` 读取，按 `\n\n` 切分并把剩余部分留在 buffer 中，解析 `data:` 行，对 `event == "message"` 的事件拼接 `answer` 字段。
2. 服务端为每个事件分配递增的 id，写成 `id: N` 行，并且保留最近的事件（v1.0 的 Redis Stream 天然就是这样）；客户端重连时带上 `Last-Event-ID` 请求头；服务端从 N+1 开始继续推送。
3. 阻塞模式返回的 JSON 包含 `task_id`、`workflow_run_id`，以及一个 data 对象（id、status、outputs、error、elapsed_time、total_tokens、total_steps……），基本上就是 `workflow_finished` 事件 data 字段的内容。

## 第 7 章

1. 环境变量也是工作流定义的一部分。如果 hash 只基于图，A 改了环境变量、B 改了图，B 保存时 hash 依然匹配，就会悄悄覆盖掉 A 对环境变量的修改。
2. `GET` 接口查询所有 `version != draft` 的记录，按时间倒序；`restore` 接口把指定版本的 graph 和环境变量复制到草稿上，并且重新计算 hash（这是一次正常的保存，需要校验乐观锁）。
3. 版本不兼容时有几种结果：完全兼容，直接导入；需要确认（例如次版本号更高），导入状态为 pending，等用户确认；完全不兼容，直接失败。以源码中的枚举为准。

## 第 8 章

1. 写入只能使用两段，保证“一个节点的一个输出”是变量池里的最小单元，所有权清楚。如果允许写入 `body.total`，就会出现 body 是一个字典、但其中某个字段被单独改写的情况，并发写入时容易互相覆盖，而且引擎写入输出时也没法整体替换。
2. 实现要点：运行前加载会话变量；变量赋值节点产出一个“变量更新”事件，引擎在 dispatcher 线程中执行 `pool.add(("conversation", name), value)`；一个 Layer 在 `on_graph_end` 时把 `conversation` 命名空间写回数据库。
3. 文件变量可以访问 name、size、extension、mime_type、url、transfer_method、type 等属性，以源码中的 `FILE_ATTRIBUTES` 为准。

## 第 9 章

1. x=1 时 IF 选择 false：先跳过 IF→大数这条边，大数的入边全部被跳过，于是大数被标记为 SKIPPED，继续跳过 大数→聚合；聚合的入边中还有一条是 UNKNOWN（再处理→聚合），停止传播。然后走 IF→小数（TAKEN），小数就绪。小数完成后，小数→再处理 TAKEN，再处理就绪。再处理完成后，再处理→聚合 TAKEN，聚合的入边为 {SKIPPED, TAKEN}，就绪。聚合完成后结束节点就绪，结束节点完成后运行结束。
2. 要点：节点产出 `PauseRequested` 事件 → 引擎把这个节点的状态重置为 UNKNOWN，记入 deferred 列表，并把 `_stopping` 的语义改为 paused；运行结束时返回 `GraphRunPaused`，附带可以序列化的状态（变量池快照、节点和边的状态、deferred 列表）。`resume(state)` 时重建图，恢复这些状态，然后重新提交 deferred 中的节点。
3. graphon 只在节点结束这类时机检查命令，好处是不会频繁访问 Redis，坏处是长时间运行的节点期间感知不到停止命令（只能靠节点内部协作）。mini-dify 每 0.1 秒检查一次，响应更快，但使用 Redis 实现时会产生大量轮询请求（可以通过调大检查间隔来折中）。

## 第 10 章

1. Answer 节点要等它的所有上游节点都完成之后才会运行，这时候 LLM 早就输出完了。流式输出必须在 LLM **运行期间**进行，所以只能由一个观察整个引擎事件流的组件（协调器）来负责。
2. 要点：数据包括类别列表 `[{id, name}]` 和查询变量；用 LLM 让模型输出类别 ID（可以用 JSON 模式或者 Function Calling）；返回 `edge_source_handle=类别ID`；执行类型设为 BRANCH；前端的 `sourceHandles` 为每个类别生成一个出口。
3. list_operator 支持过滤、排序、取前 N 个、按序号提取等操作。实现时把每种操作写成一个纯函数，作用在 `pool.get(variable)` 取出的列表上即可。

## 第 11 章

1. 如果写入直接写到父池，并行的几轮会同时写入同一个 `line_llm.text`，后写的覆盖先写的，每一轮读到的可能是别的轮次的值，输出也会错乱。
2. 要点：数据包括 `loop_count`、`break_conditions`（复用 IF 的条件结构）和 `loop_variables`；每一轮创建一个子池，放入循环变量和 index，运行子引擎；结束后从子池中读出新的循环变量值，带入下一轮；满足退出条件或达到最大次数就停止。
3. 一轮结束时：记录这一轮的输出（按序号）；如果还有没开始的项，并且没有达到失败终止的条件，就启动下一轮帧；如果所有帧都结束了，就整理输出（按序号排序，可选展平），把结果交给迭代节点完成。

## 第 12 章

1. partial-succeeded 告诉调用方：“结果拿到了，但中间有降级”。如果没有这个状态，调用方会误以为一切正常（把默认值当成真实结果使用），或者误以为运行失败了而丢弃一个可用的结果。
2. 在 `_on_failed` 中计算 `delay = interval * (2 ** attempts) * random.uniform(0.8, 1.2)`。
3. 保存的内容包括：变量池、图的执行状态（节点和边的状态、未完成的节点）、就绪队列、容器帧、回复流过滤器的进度。恢复时用它们重建 `GraphRuntimeState`，再以 `resume=True` 启动引擎。

## 第 13 章

1. 好处：引擎保持纯粹，可以作为独立的包复用（graphon）；存储方式可以替换（同步写入、异步写入、日志型存储）；同样的机制还能用来做追踪和执行限制；测试引擎时不需要数据库。
2. 要点：在 `on_graph_start` 时创建 trace；当 `NodeRunSucceeded` 事件的 node_type 是 llm 时，用 process_data 中的 prompts 和 outputs 中的 text、usage 创建一个 generation；上报操作放进 `queue.Queue`，由后台线程批量发送。
3. 异步仓储依靠“同一个节点执行的记录总是 upsert 到同一行”，加上任务按顺序执行或者带版本号，来保证最终一致。具体以源码为准，重点看它怎样处理“完成记录先于开始记录写入”的情况。

## 第 14 章

1. 由端点组成的 ID 天然去重：同一对端点和出口不会重复连线，删除和查找也很直接。随机 ID 会导致同一条连线被重复添加，序列化后也不稳定。
2. 要点：左侧列表的元素设置 `draggable` 和 `onDragStart(e => e.dataTransfer.setData('type', t))`；画布处理 `onDragOver(preventDefault)` 和 `onDrop` 事件，调用 `screenToFlowPosition({x, y})` 把屏幕坐标转换成画布坐标，然后 addBlock。判断落点是否在某个迭代节点的矩形范围内，如果是，就设置 parentId，并把坐标转换成相对于父节点的坐标。
3. 边中点的“+”按钮会打开节点选择器，选中后插入新节点：删掉原来的边，新建两条边（源 → 新节点 → 目标）。

## 第 15 章

1. 运行状态会被保存进草稿；每次运行都会触发自动保存；不同用户看到的运行状态会互相干扰；DSL 导出里也会带上这些运行状态。
2. 用 `window.addEventListener('pagehide', ...)`，在回调里调用 `fetch(url, {method:'POST', keepalive:true, headers, body})`。注意 body 的大小限制是 64KB，大图需要压缩或者只发送差量。
3. 协作模式下，请求体会带上 `_is_collaborative`，服务端在这种情况下跳过 hash 校验，冲突改由协作层（CRDT 或同步服务）来解决。

## 第 16 章

1. 例如，LLM 节点引用了下游代码节点的输出。LLM 运行的时候，代码节点还没有运行，变量池里不存在这个值，渲染出来是空字符串。
2. 要点：VarPicker 展示对象类型变量的子字段（来自代码节点声明的输出结构，或者人工声明的 schema），选中后生成 `[node, var, field]` 这样的 selector。字段名需要满足正则 `[a-zA-Z_][a-zA-Z0-9_]*`；像 `content-type` 这样含连字符的字段名，在模板里无法引用，只能用在结构化的 value_selector 中。
3. 搜索按变量名和节点标题做模糊匹配；类型过滤按 VarType 进行，并且会递归处理对象类型的子字段。

## 第 17 章

1. 同一个节点在迭代中会执行多次（甚至并行执行），节点 ID 不能唯一标识某一次执行。
2. 打开单步调试表单时，调用 `workflow-runs?limit=1` 拿到最近一次运行，再取它的 node-executions；对每个需要的 selector，从对应节点执行记录的 outputs 中取值，作为输入框的默认值。
3. 每一轮单独显示状态、错误和耗时；并行迭代时，按轮次记录开始和结束时间，单独展示。

## 第 18 章

1. 拿掉工具，强制模型基于已有的信息给出回答，避免达到最大轮数后直接报错，或者模型在工具之间无限循环。
2. 要点：边接收边累积，维护一个状态机：思考中 → 遇到 ``` 进入代码块 → 遇到 ``` 结束代码块。思考中的文字作为 AgentChunk 或 thought 推送；代码块结束后解析 JSON；如果 action 是 Final Answer，再对 action_input 做逐字推送。
3. chat 版把 scratchpad 作为 assistant 消息或者追加在 user 消息里；completion 版把所有内容（指令、历史、问题、scratchpad）拼成一整段 prompt。原因是 chat 模型和 completion 模型的输入格式不同。

## 第 19 章

1. 模型能读懂错误信息，并且自行修正（换个参数、换一个工具、或者告诉用户“查不到”）。直接抛异常会让整个 Agent 失败。**应该中止的情况**：错误意味着继续执行会造成伤害（凭证失效后不断重试、预算已经超限），或者已经出现了安全事件。
2. Provider 的配置里增加 auth 字段：`{type: api_key | bearer, in: header | query, name, value}`；value 用 `encrypt()` 加密保存，接口只返回掩码；ApiTool 调用时把凭证注入到请求头或查询串。
3. 二进制或文件类型的工具结果会被保存为工具文件（`ToolFileManager`），生成访问链接，然后作为消息附件返回；给模型的 Observation 里只放一段描述性的文字。

## 第 20 章

1. 通知没有 id，发送方不期待任何回复。如果 Server 对通知回复了一条消息，按我们的 StdioTransport 实现，这条消息会被当作“id 不匹配的消息”跳过，不会出错，但会浪费一次读取。如果实现不严谨（比如直接取下一行作为响应），就会错位。
2. 在 initialize 的响应里声明 `capabilities.resources`；`resources/list` 返回 `[{uri: "minidify://runs/<id>", name, mimeType: "application/json"}]`；`resources/read` 按 uri 查询运行记录，返回 `contents: [{uri, mimeType, text}]`。
3. 流程：发现授权服务器的元数据（`.well-known`）→ 动态客户端注册 → 授权码 + PKCE，让用户在浏览器中授权 → 回调时用授权码换取 access_token 和 refresh_token → 加密保存 → 调用时带上 token，过期就刷新。

## 第 21 章

1. Agent 的工作就是“随机应变”，工具出错是它需要处理的情况之一；而工作流的步骤是人确定的，出错应该交给人配置的错误策略处理，并且让编排者看到。
2. 要点：注入一个 `final_output` 工具，它的 parameters 是用户配置的输出 schema；FC Runner 收到对这个工具的调用时，把它的参数当作最终结果，结束循环；Agent 节点把这些参数展开写进 outputs，下游节点就可以直接引用其中的字段。
3. `enter()` 按照依赖图的拓扑顺序创建各层的实例，并注入依赖，依次执行各层的进入钩子；退出时按相反的顺序执行退出钩子，并收集每层的 runtime_state 作为快照。具体以源码为准。

## 第 22 章

1. 50：分段过小，语义不完整，相邻分段之间丢失上下文，检索出来的片段模型看不懂；2000：一个分段里混杂了多个主题，向量被稀释，检索不准，而且很占上下文窗口。
2. 要点：对每个 chunk 调用 LLM 生成 N 个问答对；存储时，content 存问题，parent_content（或者另一个字段）存答案；检索时匹配问题，返回答案。
3. `from_encoder` 把长度函数替换成 token 计数（用 embedding 模型的 tokenizer），所以 chunk_size 和 overlap 的单位就变成了 token。

## 第 23 章

1. BM25 的分数没有上限，量级可能远大于余弦相似度，不归一化的话，加权求和时关键词分数会完全压倒向量分数，权重参数也就失去了意义。
2. 两路检索各自取前 K 个，按排名累加 `1/(60+rank)`。优点：不需要归一化，对两路分数的分布不敏感；缺点：丢失了分数的绝对大小信息（第一名领先很多和只领先一点，得分是一样的）。
3. 路由模式把每个知识库包装成一个“工具”，描述就是知识库的描述，然后用 Function Calling 或 ReAct 让模型选出一个。

## 第 24 章

1. 不放角色，这样角色变更可以立即生效。返回 404 而不是 403，可以避免泄露“这个资源存在”的信息。
2. 先校验 TenantMember 中存在 `(account, tenant_id)` 这条记录，然后用新的 tid 签发 token，前端替换 token 并刷新页面。
3. 同一个 token 的并发校验请求，只有一个会去查数据库，其他请求等待这一次的结果（借助锁或者 future），这样大量并发的缓存未命中就不会同时打到数据库上。

## 第 25 章

1. Pub/Sub：如果 worker 在 HTTP 线程真正开始订阅之前就发布了事件，这些事件会丢失（开头的 workflow_started 等）。Stream：事件写进了日志，订阅时从头读取，一条都不会丢。
2. 在 `execute` 开头用一条 SQL 原子地抢占：`UPDATE workflow_runs SET status='executing' WHERE id=:id AND status='running'`。如果 `rowcount == 0`，说明这次运行已经被别的 worker 抢走了，直接返回。
3. 每个租户维护一个“已使用的执行时间”，每次调度时优先选择用得最少的租户（借鉴 CFS 的 vruntime 思想），防止大租户长期独占 worker。

## 第 26 章

1. 读取 `os.environ` 拿到 SECRET_KEY 和各种 API Key；直接连接数据库，读取所有租户的数据；`os.system` 执行任意命令；修改平台的模块（猴子补丁），影响其他插件和核心逻辑。
2. 要点：用子进程启动插件，以 JSON-RPC 方式通信（`register` 由插件声明自己有哪些工具，`tools/call` 用来调用）；平台侧的 PluginToolProxy 在 invoke 时转发调用请求。这样每个插件可以有自己的虚拟环境，崩溃也只影响它自己。
3. 反向调用请求里带有租户和用户的上下文，平台据此查询这个租户的模型凭证，并记录用量和计费。

## 第 27 章

1. 例如：初始 URL `https://attacker.com/r` 解析出来是公网地址，检查通过；服务器返回 `302 Location: http://169.254.169.254/latest/meta-data/`，如果跟随重定向时不再检查，就会访问到云服务器的元数据。
2. 在 `PersistenceLayer._jsonable` 之前递归遍历 inputs / outputs / process_data，把等于这些敏感环境变量值的字符串替换成 `******`（按值匹配比按键名匹配更可靠）。
3. 用 Redis 的 `INCR` + `EXPIRE` 实现固定窗口限流，或者用 Lua 脚本实现令牌桶；写成 FastAPI 的依赖，按 API Key 或 IP 取 key；超出限制时返回 429，并带上 `Retry-After` 头。
4. 被禁止的关键系统调用大致包括：创建网络连接的 socket / connect（除非允许网络）、execve / fork / clone（创建进程）、mount / ptrace / chroot 等特权调用、以及大部分文件写操作。具体以 dify-sandbox 的白名单为准。

## 第 28 章

1. Webhook 的发送方通常有很短的超时（GitHub 是 10 秒），而工作流可能要运行几分钟；同步等待会导致超时，发送方还会因此重试，造成重复执行。返回 202 表示“已收到，稍后处理”，语义正好对应。
2. 每次计算并存储 `next_run_at`；轮询时查询 `next_run_at <= now` 的计划，用一条带条件的 `UPDATE ... SET next_run_at = :new WHERE id=:id AND next_run_at=:old` 来认领，`rowcount == 1` 才投递任务。这样多个实例同时运行也是安全的。
3. 在 nginx 前面加一个 Caddy（会自动申请证书），或者在 nginx 中配置 certbot；用 `openssl rand -hex 32` 生成 SECRET_KEY，写进 `.env`，并且限制这个文件的访问权限。
