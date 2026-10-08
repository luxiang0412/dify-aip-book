# 第 14 章 React Flow 画布

> 本章目标：用 React Flow 做出工作流画布：自定义节点、多出口的分支节点、容器（子流程）、连线规则、点击添加节点；读懂 Dify 画布的组织方式。
> 前置：第 7 章（图的 JSON）。对应代码：mini-dify **v0.3** `frontend/src/workflow/components/Canvas.tsx`、`CustomNode.tsx`、`BlockSelector.tsx`、`blocks.ts`。

## 14.1 问题：画布要做什么

画布是用户和工作流打交道的主要界面。它至少要支持这些操作：

- 显示节点和连线，支持拖拽、缩放、平移；
- 每种节点有自己的样式和摘要信息；
- 分支节点有**多个出口**（IF、ELIF、ELSE、异常）；
- 容器节点（迭代）**里面还能放节点**；
- 连线要有规则：不能连自己、不能跨容器连线；
- 添加、删除节点，删除节点时把相关的边一起删掉；
- 运行时显示每个节点的状态，走过的边要高亮。

从零写这些需要几千行代码。好在 **React Flow** 已经解决了画布本身的所有难题（坐标变换、拖拽、连线吸附、视口、小地图），我们只需要关心**业务层面**的部分。

> 包名说明：Dify 使用的是 `reactflow`（v11）。从 v12 起，这个库改名为 `@xyflow/react`，API 基本一致。mini-dify 使用的是 v12。

## 14.2 React Flow 的核心概念

```tsx
<ReactFlow
  nodes={nodes}               // [{id, type, position, data, parentId?, style?}]
  edges={edges}               // [{id, source, sourceHandle, target, targetHandle}]
  nodeTypes={{ custom: CustomNode, iteration: IterationNode }}   // node.type → 组件
  onNodesChange={...}         // 拖拽、选中、删除…… → changes 数组
  onEdgesChange={...}
  onConnect={...}             // 用户从一个 Handle 拖到另一个 Handle
/>
```

- **受控模式**：节点和边的数据保存在你自己的状态里；React Flow 只负责**报告变化**（`onNodesChange(changes)`），由你调用 `applyNodeChanges(changes, nodes)` 把变化应用上去，然后再传回给它渲染；
- **Handle**：节点上的连接点。`type="source"` 表示出口，`type="target"` 表示入口；每个 Handle 有一个 `id`，**连线时会成为边的 `sourceHandle` / `targetHandle`**，这正是第 7 章里分支能够工作的关键；
- **子流程（Sub Flow）**：节点设置了 `parentId` 后，它的坐标就相对于父节点计算；设置 `extent: 'parent'` 后，它就不能被拖出父节点的范围。

## 14.3 Dify 是怎么做的

### 14.3.1 画布入口

```tsx
// web/app/components/workflow/index.tsx:111
const nodeTypes = {
  [CUSTOM_NODE]: CustomNode,                    // 所有业务节点共用这一个组件
  [CUSTOM_NOTE_NODE]: CustomNoteNode,           // 便签
  [CUSTOM_SIMPLE_NODE]: CustomSimpleNode,
  [CUSTOM_ITERATION_START_NODE]: CustomIterationStartNode,
  [CUSTOM_LOOP_START_NODE]: CustomLoopStartNode,
  ...
}
const edgeTypes = { [CUSTOM_EDGE]: CustomEdge }
...
<ReactFlow
  nodeTypes={nodeTypes} edgeTypes={edgeTypes}                    // 736
  onNodeDragStart={...} onNodeDrag={...} onNodeDragStop={...}
  onNodeClick={handleNodeClick} onNodeContextMenu={...}
  onConnect={handleNodeConnect} onConnectStart={...} onConnectEnd={...}   // 749
  onEdgesChange={handleEdgesChange} ...
  deleteKeyCode={null}                                           // 765：禁用默认的删除行为，由自己的快捷键处理
  multiSelectionKeyCode={null}
  panOnDrag={controlMode === ControlMode.Hand || [1]}           // 指针模式 / 手型模式
/>
```

所有业务节点都只用 **一个** React 组件 `CustomNode`，由它按 `data.type` 再分派：

```tsx
// web/app/components/workflow/nodes/index.tsx
const CustomNode = (props: NodeProps) => {
  const NodeComponent = NodeComponentMap[nodeData.type]!     // llm → nodes/llm/node.tsx
  return <BaseNode {...props}><NodeComponent /></BaseNode>   // BaseNode 负责标题、状态、Handle 等公共部分
}
```

### 14.3.2 每种节点一个目录

```
web/app/components/workflow/nodes/llm/
├── node.tsx            画布上显示的卡片内容（摘要）
├── panel.tsx           右侧配置面板
├── default.ts          默认值、校验（checkValid）、元信息
├── use-config.ts       面板的状态和逻辑
├── types.ts            这个节点 data 的 TS 类型
└── components/         面板里用到的子组件
```

`default.ts` 是前端的“节点注册表”：

```ts
// web/app/components/workflow/nodes/llm/default.ts（节选）
const nodeDefault: NodeDefault<LLMNodeType> = {
  metaData,                                    // 排序、分类、类型
  defaultValue: {                              // 新建节点时的初始 data
    model: { provider: '', name: '', mode: 'chat', completion_params: { temperature: 0.7 } },
    prompt_template: [{ role: 'system', text: '' }],
    context: { enabled: false, variable_selector: [] },
    vision: { enabled: false },
  },
  checkValid(payload, t, ...) { ... },        // 检查清单用到的校验（第 16 章）
}
```

**前端自己知道每种节点的默认值、输出变量和校验规则**，并不依赖后端下发这些信息（后端也有 `default-workflow-block-configs` 接口，但只用于少数节点）。这样做的好处是：编辑器的交互完全在本地完成，不需要等待网络请求。

### 14.3.3 连线规则

```ts
// web/app/components/workflow/hooks/use-nodes-interactions.ts:499 handleNodeConnect（节选）
if (targetNode?.parentId !== sourceNode?.parentId) return     // 不允许跨容器连线
...
const newEdge = {
  id: `${source}-${sourceHandle}-${target}-${targetHandle}`,  // 边 ID 由端点决定，天然去重
  type: CUSTOM_EDGE, source, sourceHandle, target, targetHandle,
  data: { sourceType, targetType, isInIteration, iteration_id: ..., ... },
  zIndex: targetNode?.parentId ? NESTED_ELEMENT_Z_INDEX : 0,   // 容器内的边要画在容器上层
}
setEdges(newEdges)
handleSyncWorkflowDraft()                                      // 每次修改后都触发自动保存（第 15 章）
saveStateToHistory(WorkflowHistoryEvent.NodeConnect, ...)      // 记录一步撤销历史（第 15 章）
```

## 14.4 从零实现

### 14.4.1 节点注册表：blocks.ts

和 Dify 的 `default.ts` 对应，只是集中写在一个文件里：

```ts
// frontend/src/workflow/blocks.ts
export const BLOCKS: Record<BlockType, BlockDef> = {
  llm: {
    label: 'LLM', icon: '✦', color: '#6366f1', addable: true,
    defaultData: () => ({
      model: { provider: 'mock', name: 'echo', completion_params: {} },
      prompt_template: [{ role: 'system', text: 'You are a helpful assistant.' }, { role: 'user', text: '' }],
    }),
  },
  'if-else': {
    label: '条件分支', icon: '⑂', color: '#0891b2', addable: true,
    defaultData: () => ({ cases: [{ case_id: 'true', logical_operator: 'and', conditions: [] }] }),
  },
  ...
}

// 节点右侧的出口：分支节点每个 case 一个，最后是 ELSE；配置了异常分支的节点再加一个“异常”
export function sourceHandles(data: NodeData) {
  if (data.type === 'end' || data.type === 'answer') return []
  let handles = [{ id: 'source' }]
  if (data.type === 'if-else') {
    handles = data.cases.map((c, i) => ({ id: c.case_id, label: i === 0 ? 'IF' : `ELIF ${i}` }))
    handles.push({ id: 'false', label: 'ELSE' })
  }
  if (data.error_strategy === 'fail-branch') handles.push({ id: 'fail-branch', label: '异常' })
  return handles
}
```

`outputVars(node)`（每种节点会输出哪些变量）也放在这里，第 16 章会用到。

### 14.4.2 一个组件渲染所有节点

```tsx
// frontend/src/workflow/components/CustomNode.tsx
function CustomNodeImpl({ data, selected }: NodeProps<WFNode>) {
  const def = BLOCKS[data.type]
  const handles = sourceHandles(data)
  const isRoot = data.type === 'start' || data.type === 'iteration-start'
  return (
    <div className={`wf-node ${selected ? 'selected' : ''} status-${data._status ?? 'idle'}`}>
      {!isRoot && <Handle type="target" position={Position.Left} id="target" />}
      <div className="wf-node-header">
        <span className="wf-node-icon" style={{ background: def?.color }}>{def?.icon}</span>
        <span className="wf-node-title">{data.title}</span>
        {data._status && <span className={`wf-badge ${data._status}`}>{STATUS_LABEL[data._status]}</span>}
      </div>
      {summary(data) && <div className="wf-node-summary">{summary(data)}</div>}
      {handles.length > 1 ? (
        <div className="wf-node-branches">
          {handles.map((h) => (
            <div key={h.id} className="wf-node-branch">       {/* 每个分支一行，Handle 放在这一行的右侧 */}
              {h.label}
              <Handle type="source" position={Position.Right} id={h.id} />
            </div>
          ))}
        </div>
      ) : (
        handles.map((h) => <Handle key={h.id} type="source" position={Position.Right} id={h.id} />)
      )}
    </div>
  )
}
export const CustomNode = memo(CustomNodeImpl)
```

几个要点：

- 一个节点上有多个 source Handle 时，**每个 Handle 都要有不同的 id**，否则连线时分不清是从哪个出口连出来的；
- 用 CSS 类 `status-running / succeeded / failed` 控制边框颜色，`data._status` 由运行事件写入（第 17 章）；
- `memo` 必不可少：React Flow 拖拽时会频繁触发重新渲染，节点组件应该只在自己的 props 变化时才重新渲染。

迭代容器是另一个组件 `IterationNode`：它渲染一个带虚线边框的大框，子节点由 React Flow 根据 `parentId` 自动画在里面。

### 14.4.3 画布组件

```tsx
// frontend/src/workflow/components/Canvas.tsx
const nodeTypes = { custom: CustomNode, iteration: IterationNode }   // 定义在组件外面，避免每次渲染都重新创建

export default function Canvas() {
  const nodes = useWorkflowStore((s) => s.nodes)
  const edges = useWorkflowStore((s) => s.edges)
  ...
  // 运行时给边上色：两端都运行过的边显示为绿色，指向正在运行节点的边显示为动画
  const styledEdges = useMemo(() => {
    const status = new Map(nodes.map((n) => [n.id, n.data._status]))
    return edges.map((e) => {
      const s = status.get(e.source), t = status.get(e.target)
      return { ...e, animated: t === 'running',
               style: s && s !== 'running' && t ? { stroke: '#16a34a', strokeWidth: 2 } : undefined }
    })
  }, [nodes, edges])

  return (
    <ReactFlow nodes={nodes} edges={styledEdges} nodeTypes={nodeTypes}
      onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
      onNodeClick={(_, n) => select(n.id)} onPaneClick={() => select(null)}
      deleteKeyCode={['Backspace', 'Delete']} fitView fitViewOptions={{ maxZoom: 1 }} minZoom={0.2}>
      <Background gap={16} />
      <Controls />
      <MiniMap pannable zoomable />
    </ReactFlow>
  )
}
```

`nodeTypes` 一定要定义在组件外面。如果在组件内部定义，每次渲染都会生成一个新对象，React Flow 会在控制台警告，并且会重新挂载所有节点。

### 14.4.4 添加节点：BlockSelector + addBlock

左侧是节点列表，点击后由 store 的 `addBlock(type)` 处理（简化版的 Dify “在选中节点后添加”逻辑）：

```ts
// frontend/src/workflow/store.ts（addBlock 节选）
// 放置规则：
//  - 选中的是迭代节点 → 加到迭代内部，并从内部最右边的节点连线过来
//  - 选中的是普通节点 → 加在它右边 300px 处（同一个父容器），并从它连线过来
//  - 什么都没选中 → 加在整张图的最右侧
if (selected?.data.type === 'iteration' && type !== 'iteration') { parentId = selected.id; ... }
else if (selected) { parentId = selected.parentId; position = { x: selected.position.x + 300, y: selected.position.y }; ... }

const newNodes = [{ id, type: type === 'iteration' ? 'iteration' : 'custom', position, data,
                    ...(parentId ? { parentId, extent: 'parent' } : {}) }]
if (type === 'iteration') {
  const startId = `${id}start`                                  // 和 Dify 一样：迭代自带一个“迭代开始”节点
  data.start_node_id = startId
  newNodes[0].style = { width: 620, height: 260 }
  newNodes.push({ id: startId, type: 'custom', parentId: id, extent: 'parent',
                  position: { x: 24, y: 70 }, deletable: false, data: { type: 'iteration-start', title: '迭代开始' } })
}
```

React Flow 的子流程有一个**硬性要求**：节点数组里，**父节点必须排在子节点前面**。所以新建迭代时先 push 迭代节点本身，再 push 它的“迭代开始”节点。

### 14.4.5 连线与删除规则

```ts
onConnect: (c) => {
  const src = nodes.find((n) => n.id === c.source), tgt = nodes.find((n) => n.id === c.target)
  if (!src || !tgt || c.source === c.target) return                     // 不能连自己
  if ((src.parentId ?? null) !== (tgt.parentId ?? null)) return         // 不能跨容器连线（和 Dify 一样）
  get().pushHistory()
  const sourceHandle = c.sourceHandle ?? 'source'
  set({ edges: addEdge({ ...c, sourceHandle, targetHandle: 'target',
                         id: `${c.source}-${sourceHandle}-${c.target}` }, edges), saveState: 'dirty' })
},

onNodesChange: (changes) => {
  const filtered = changes.filter((c) => {                              // 不允许删除开始节点和迭代开始节点
    if (c.type !== 'remove') return true
    const n = get().nodes.find((x) => x.id === c.id)
    return n && n.data.type !== 'start' && n.data.type !== 'iteration-start'
  })
  let nodes = applyNodeChanges(filtered, get().nodes)
  const removed = new Set(filtered.filter((c) => c.type === 'remove').map((c) => c.id))
  if (removed.size) nodes = nodes.filter((n) => !n.parentId || !removed.has(n.parentId))   // 删除迭代时连同子节点一起删
  const ids = new Set(nodes.map((n) => n.id))
  set({ nodes, edges: get().edges.filter((e) => ids.has(e.source) && ids.has(e.target)) })  // 清掉悬空的边
},
```

## 14.5 运行与验证

```bash
cd code/mini-dify && git checkout v0.3
# 启动后端和前端，打开 http://localhost:3000
```

1. 创建一个 Workflow 应用，画布上会出现默认的三个节点；
2. 点选 LLM 节点，再点左侧的“条件分支”：新节点出现在 LLM 右侧并自动连上线；
3. 从条件分支的 IF 和 ELSE 两个出口分别拖线到两个新节点上；
4. 添加一个“迭代”，选中它后再点“LLM”，LLM 会被放进迭代内部；
5. 选中一个节点，按 Backspace 删除，相关的边也会一起消失；试着删除开始节点，会发现删不掉。

写作时用无头浏览器自动执行了以上操作。“选中 LLM → 点击代码执行”之后，节点数变为 4、边数变为 3，状态显示“已保存”。

## 14.6 练习

1. **巩固**：为什么边的 ID 要由 `source + sourceHandle + target` 组成？如果用随机 ID，会出现什么问题？
2. **扩展**：实现从左侧列表**拖拽**节点到画布上（提示：`onDragOver` / `onDrop` + `screenToFlowPosition`）。再实现“拖入迭代容器的范围内时，自动成为它的子节点”。
3. **读源码**：读 Dify 的 `web/app/components/workflow/custom-edge.tsx`，看边的中点处的“+”按钮是怎么实现“在两个节点之间插入新节点”的。

## 14.7 延伸阅读

- React Flow 文档：Custom Nodes、Handles、Sub Flows、Controlled vs Uncontrolled
- `web/app/components/workflow/hooks/use-nodes-interactions.ts`：Dify 全部的节点交互逻辑（约 2000 行），包括粘贴、复制、对齐辅助线等
