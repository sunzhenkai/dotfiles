# 图表（archify）

镜像里的结构图、流程图、时序、数据流、状态机 **委托 skill `archify`**，不要用手绘 SVG/Mermaid 冒充 archify 产物，也不要把 archify 的 schema 或渲染器拷进本 Skill。

- 上游： [tt-a1i/archify](https://github.com/tt-a1i/archify)（入口 `archify/SKILL.md`）
- 安装：`dotf agents -c` 会按 `agents/skills-defaults.yaml` 装到 `~/.agents/skills`；环境还没有时也可手动 `npx skills add tt-a1i/archify -g -y --copy`
- 类型：`architecture` | `workflow` | `sequence` | `dataflow` | `lifecycle`
- 产物：自包含 HTML，放到 `<spec_root>/diagrams/<slug>.html`；JSON 候选与 HTML 同目录、同 slug（如 `<slug>.json`），便于下次差分。只有 JSON、没有 HTML，不算交付。
- `diagrams/INDEX.md`：图 / 类型 / 回答什么问题 / 链到**已经存在的** `.html`。init 骨架可以是空表。禁止把 INDEX 写成待办清单，禁止链到 archify 的 Skill 目录。

## 何时画

图表是解释复杂关系的手段，不是完成度装饰。候选包括：系统上下文、模块地图、部署/进程拓扑、切片主路径、对照实现差分、状态机、一次请求调用链、数据管道。

按请求来源决策：

- 用户明确要求某张图或“把架构/流程可视化”时：该图属于本轮交付，按 archify 流程生成 HTML；依赖缺失则明确报告阻塞。
- Agent 主动发现图表可能有帮助时：先比较表格/短流程是否已经足够。一个明显高价值、低额外成本的图可随 build 交付；多个图或高成本图先给候选、价值和范围，请用户选择。
- 用户没有要求且文字已清楚时：省略图表，不写占位，也不把“没有图”当作 build 失败。

overview 与切片页只链接已存在的图，不在 Markdown 里重复绘制。

## 执行

1. 读本文件后 **加载并遵循已安装的 `archify` Skill**（不要用本文件代替其 schema/validate/deliver）。宿主会话的 skill 列表里没有 `archify` **不等于未安装**：`Read ~/.agents/skills/archify/SKILL.md`（或 `dotf agents -c` 装到的同等路径），在本轮同一会话按其流程写 JSON、`validate`、`deliver`。
2. 图中的组件、调用、状态必须能追溯到当前镜像的 SOURCE / 模块 / 切片；禁止为好看而发明拓扑。
3. 在 archify Skill 根目录执行（输出路径用镜像里的绝对或相对路径）：

   ```bash
   node bin/archify.mjs validate <type> <spec_root>/diagrams/<slug>.json --json
   node bin/archify.mjs deliver <type> <spec_root>/diagrams/<slug>.json <spec_root>/diagrams/<slug>.html --json
   ```

   质量档次、参数以 archify Skill 为准。非零退出不得称为已交付。
4. 用户要求图表时，**未安装**的判定是找不到 `archify/SKILL.md`、找不到 `bin/archify.mjs`，或 node 无法运行。此时在完成摘要写明阻塞，INDEX 保持空表或已有 HTML；不要生成假 HTML。
5. Agent 候选若本轮不做，不要往 INDEX 或正文写“暂未生成”占位；只在对话中说明取舍。已经承诺交付的图必须有 HTML，不能只留 JSON。

## 与切面的对应

| 要回答的问题 | 优先类型 |
|--------------|----------|
| 系统与邻接、信任边界 | `architecture`（链到 `context/`） |
| 模块、边界、依赖 | `architecture` |
| 进程、部署、网络 | `architecture`（链到 `runtime/`） |
| 切片或发布步骤 | `workflow` |
| 一次请求/调用链 | `sequence` |
| 管道、血缘、存储 | `dataflow`（链到 `data/`） |
| 状态、重试、终态 | `lifecycle` |
