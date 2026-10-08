import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const c = (file: string, text: string) => ({ text, link: `/chapters/${file}` })

export default withMermaid(
  defineConfig({
    lang: 'zh-CN',
    title: '从 Dify 到 Mini-Dify',
    description: '从零构建 AI 平台与 Agent Workflow：读 Dify 源码，写一个能跑的 mini-dify',
    base: '/dify-aip-book/',
    cleanUrls: true,
    lastUpdated: true,
    srcExclude: ['code/**', 'node_modules/**'],
    rewrites: { 'README.md': 'index.md' },
    ignoreDeadLinks: [/^https?:\/\/localhost/],  // the book links to local dev servers (localhost:3000 etc.)
    markdown: {
      lineNumbers: false,
      config: (md) => {
        // The book is full of Dify template syntax like {{#sys.query#}}. VitePress compiles
        // markdown as Vue templates, so bare `{{` in prose would be treated as interpolation.
        // Escape the braces in plain text and inline code (fenced blocks are already v-pre).
        const esc = (html: string) => html.replace(/\{\{/g, '&#123;&#123;').replace(/\}\}/g, '&#125;&#125;')
        for (const rule of ['text', 'code_inline'] as const) {
          const orig = md.renderer.rules[rule]!
          md.renderer.rules[rule] = (tokens, idx, opts, env, self) => esc(orig(tokens, idx, opts, env, self))
        }
      },
    },
    themeConfig: {
      nav: [
        { text: '开始阅读', link: '/chapters/00-how-to-read' },
        { text: '源码地图', link: '/appendix/a-source-map' },
        { text: '配套代码', link: 'https://github.com/luxiang0412/mini-dify' },
      ],
      sidebar: [
        { text: 'Part 0 导读', items: [c('00-how-to-read', '0. 本书怎么读')] },
        {
          text: 'Part I 全景',
          items: [
            c('01-five-app-forms', '1. LLM 应用的五种形态'),
            c('02-dify-architecture', '2. Dify 架构鸟瞰'),
            c('03-one-workflow-run', '3. 一次运行的完整生命周期 ★'),
          ],
        },
        {
          text: 'Part II 模型层 → v0.1',
          items: [
            c('04-model-abstraction', '4. 模型抽象'),
            c('05-prompt-and-memory', '5. Prompt、模板与记忆'),
            c('06-streaming-sse', '6. 流式输出与事件协议'),
            c('lab-1-streaming-chat', 'Lab 1 流式聊天'),
          ],
        },
        {
          text: 'Part III 工作流引擎 → v0.2',
          items: [
            c('07-workflow-dsl', '7. 数据模型与 DSL'),
            c('08-variable-pool', '8. 变量池 ★'),
            c('09-graph-engine', '9. 图执行引擎 ★★'),
            c('10-nodes', '10. 节点体系'),
            c('11-iteration', '11. 迭代与循环'),
            c('12-robustness', '12. 健壮性'),
            c('13-persistence-observability', '13. 持久化与可观测'),
            c('lab-2-workflow-engine', 'Lab 2 工作流引擎'),
          ],
        },
        {
          text: 'Part IV 前端画布 → v0.3',
          items: [
            c('14-react-flow-canvas', '14. React Flow 画布'),
            c('15-editor-state', '15. 编辑器状态管理'),
            c('16-panels-and-variables', '16. 面板与变量选择器 ★'),
            c('17-run-and-debug', '17. 运行与调试'),
            c('lab-3-visual-editor', 'Lab 3 可视化编排'),
          ],
        },
        {
          text: 'Part V Agent → v0.4',
          items: [
            c('18-agent-principles', '18. ReAct 与 Function Calling'),
            c('19-tools', '19. 工具体系'),
            c('20-mcp', '20. MCP 协议'),
            c('21-agent-in-workflow', '21. Agent 节点与新运行时'),
            c('lab-4-agent-tools-mcp', 'Lab 4 工具、Agent、MCP'),
          ],
        },
        {
          text: 'Part VI RAG → v0.5',
          items: [
            c('22-indexing-pipeline', '22. 索引管线'),
            c('23-retrieval', '23. 检索与上下文注入'),
            c('lab-5-rag', 'Lab 5 知识库 RAG'),
          ],
        },
        {
          text: 'Part VII 平台化 → v1.0',
          items: [
            c('24-tenancy-and-api', '24. 多租户与开放 API'),
            c('25-async-and-scale', '25. 异步与横向扩展'),
            c('26-plugins', '26. 插件系统'),
            c('27-security', '27. 安全'),
            c('28-triggers-and-deploy', '28. 触发器与部署'),
            c('lab-6-platform', 'Lab 6 平台化与部署'),
          ],
        },
        {
          text: '附录',
          items: [
            { text: 'A 源码阅读地图', link: '/appendix/a-source-map' },
            { text: 'B 术语表', link: '/appendix/b-glossary' },
            { text: 'C 横向对比', link: '/appendix/c-comparison' },
            { text: 'D 练习答案', link: '/appendix/d-answers' },
            { text: '最初的大纲', link: '/OUTLINE' },
          ],
        },
      ],
      outline: { level: [2, 3], label: '本页目录' },
      search: {
        provider: 'local',
        options: { translations: { button: { buttonText: '搜索', buttonAriaLabel: '搜索' } } },
      },
      socialLinks: [{ icon: 'github', link: 'https://github.com/luxiang0412/dify-aip-book' }],
      docFooter: { prev: '上一章', next: '下一章' },
      lastUpdated: { text: '最后更新' },
      editLink: { pattern: 'https://github.com/luxiang0412/dify-aip-book/edit/main/:path', text: '在 GitHub 上编辑此页' },
      footer: { message: '配套代码：github.com/luxiang0412/mini-dify', copyright: '参照 langgenius/dify @ f3ecedab56' },
    },
  }),
)
