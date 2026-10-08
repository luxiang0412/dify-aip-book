# Lab 3：mini-dify v0.3 —— 可视化编排 + 一键运行 + 实时追踪

> 目标：在浏览器里拖拽编排工作流、配置节点、自动保存、运行并实时看到每个节点的状态，支持迭代容器、分支、单步调试和 Chatflow 预览。
> 起点 `v0.2`，终点 `v0.3`。`git diff v0.2 v0.3 --stat` 可以看到，几乎所有改动都在 `frontend/` 里。

## 依赖

```bash
cd frontend
npm install @xyflow/react zustand immer
```

## 文件清单与构建顺序

| 顺序 | 文件 | 章节 | 说明 |
|---|---|---|---|
| 1 | `src/workflow/types.ts` | 14 | `BlockType`、`NodeData`（`_` 前缀约定）、`TraceItem`…… |
| 2 | `src/workflow/blocks.ts` | 14、16 | `BLOCKS` 注册表、`outputVars`、`sourceHandles`、`systemVars` |
| 3 | `src/workflow/availableVars.ts` | 16 | `ancestors`、`availableVars`、`childVars` |
| 4 | `src/lib/api.ts` | — | fetch 封装，`ApiError` |
| 5 | `src/workflow/store.ts` | 15 | Zustand store：图数据、选中、保存状态、运行状态、撤销栈；`serializeGraph` |
| 6 | `src/workflow/hooks/useSyncDraft.ts` | 15 | 防抖保存 + hash + 保存后刷新检查清单 |
| 7 | `src/workflow/hooks/useWorkflowRun.ts` | 17 | 事件 → 状态 |
| 8 | `src/workflow/components/CustomNode.tsx` | 14 | 普通节点 + 迭代容器 |
| 9 | `src/workflow/components/Canvas.tsx` | 14 | ReactFlow、边着色、撤销快捷键 |
| 10 | `src/workflow/components/BlockSelector.tsx` | 14 | 左侧节点列表 |
| 11 | `src/workflow/components/fields.tsx` | 16 | `VarPicker`、`PromptEditor`、`NamedVarList`、`Field` |
| 12 | `src/workflow/components/panels.tsx` | 16 | 9 种节点的面板 |
| 13 | `src/workflow/components/NodePanel.tsx` | 12、16、17 | 面板外壳 + 失败处理 + 单步调试 |
| 14 | `src/workflow/components/RunPanel.tsx` | 17 | 运行 / 追踪 / 历史，Chatflow 预览 |
| 15 | `src/pages/AppListPage.tsx`、`WorkflowEditorPage.tsx` | — | 应用列表（创建、导入 DSL、删除）；编辑器页（顶栏、环境变量弹窗、发布） |
| 16 | `src/main.tsx`、`src/styles.css` | — | 路由与样式 |

后端只有两处小改动：`validate_graph` 加入每个节点的配置检查（第 16 章）；新增 `examples/batch-translate.yml`。

## 关键交互的验收

用 v0.3 跑通下面这个场景（写作时用无头 Chrome 自动执行过一遍）：

1. 工作室 → 导入 DSL → 选择 `examples/batch-translate.yml`；
2. 画布上出现 10 个节点：开始 → 按行拆分（代码）→ 行数 ≤ 5？（条件分支）→ [逐行处理（并行迭代，内含 迭代开始 → 处理一行(LLM)）] → 合并结果（模板）→ 汇总分支（变量聚合）→ 结束；ELSE 分支 → 行数过多（模板）→ 汇总分支；
3. 运行，输入三行文本；
4. 预期结果：状态 succeeded；“行数过多”节点保持灰色（被跳过）；追踪里的“逐行处理”展开后有 3 轮，每轮包含“迭代开始”和“处理一行”两个节点。

![迭代 + 分支的运行结果与追踪](./images/lab3-iteration-trace.png)

## 验收清单

- [ ] `npm run build` 通过（TypeScript 严格模式）
- [ ] 新建 Workflow / Chatflow 应用后，画布上有对应的默认图
- [ ] 添加节点会自动连线；IF/ELSE 有多个出口；迭代可以放入子节点；不能跨容器连线
- [ ] 修改后自动保存，在两个标签页同时编辑会出现冲突提示
- [ ] 检查清单能实时显示“未连接”“有未设置的变量”等问题
- [ ] 运行时节点实时变色，走过的边变绿，文字流式出现
- [ ] 追踪能展开查看 inputs、process_data、outputs；迭代按轮次分组
- [ ] 历史标签页能回看之前的运行
- [ ] 单步调试可用
- [ ] Chatflow 预览支持多轮对话，第二轮能体现记忆

## 写作时踩到的坑（真实记录）

1. **检查清单通过了，运行却失败**：新加的代码节点的输入没有选择变量，检查清单却显示通过。修复方法是在后端校验中加入“变量引用必须已设置并且指向存在的节点”（第 16 章）。
2. **UI 测试脚本里的时序问题**：自动化测试在 Chatflow 第二轮回答还没流完的时候就去读取文本，读到了半截内容。修复方法是先等待“停止”按钮出现（说明开始运行了），再等待“发送”按钮重新出现（说明运行结束了）。**这个 bug 出在测试脚本里，不在产品里。** 但它提醒我们：流式 UI 的测试一定要等待一个明确的“结束”信号。
3. **favicon 的 404**：浏览器会自动请求 `/favicon.ico`。在 `index.html` 里加上 `<link rel="icon" href="data:," />` 就可以了。

## 下一步

到这里，mini-dify 已经是一个完整可用的“工作流平台”了。Part V 会加入 Agent：让模型**自己决定**下一步做什么。
