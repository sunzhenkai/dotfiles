# 图表（archify）

镜像里的结构图、流程图、时序、数据流、状态机 **委托 skill `archify`**，不要用手绘 SVG/Mermaid 冒充 archify 产物，也不要把 archify 的 schema 或渲染器拷进本 Skill。

- 上游： [tt-a1i/archify](https://github.com/tt-a1i/archify)（入口 `archify/SKILL.md`）
- 安装：`dotf agents -c` 会按 `agents/skills-defaults.yaml` 装到 `~/.agents/skills`；环境还没有时也可手动 `npx skills add tt-a1i/archify -g -y --copy`
- 类型：`architecture` | `workflow` | `sequence` | `dataflow` | `lifecycle`
- 产物：自包含 HTML，放到 `<spec_root>/diagrams/<slug>.html`；JSON 候选与 HTML 同目录、同 slug（如 `<slug>.json`），便于下次差分。只有 JSON、没有 HTML，不算交付。
- `diagrams/INDEX.md`：图 / 类型 / 回答什么问题 / 链到**已经存在的** `.html`。init 骨架可以是空表。禁止把 INDEX 写成待办清单，禁止链到 archify 的 Skill 目录。

## 何时画

仅当表格说不清关系时：系统上下文、模块地图、部署/进程拓扑、切片主路径、对照实现差分、状态机、一次请求调用链、数据管道。overview 与切片页用一句话说明「看哪张图」，不要在 Markdown 里再画一遍。

识别出需要某张图，就等于**本轮必须交付**该图的 HTML。详尽模式尤其如此：已经列出序列图 / 架构图 / 状态机 / 数据流候选，却不 `deliver`，视为 build 未完成。

## 执行

1. 读本文件后 **加载并遵循已安装的 `archify` Skill**（不要用本文件代替其 schema/validate/deliver）。宿主会话的 skill 列表里没有 `archify` **不等于未安装**：`Read ~/.agents/skills/archify/SKILL.md`（或 `dotf agents -c` 装到的同等路径），在本轮同一会话按其流程写 JSON、`validate`、`deliver`。
2. 图中的组件、调用、状态必须能追溯到当前镜像的 SOURCE / 模块 / 切片；禁止为好看而发明拓扑。
3. 在 archify Skill 根目录执行（输出路径用镜像里的绝对或相对路径）：

   ```bash
   node bin/archify.mjs validate <type> <spec_root>/diagrams/<slug>.json --json
   node bin/archify.mjs deliver <type> <spec_root>/diagrams/<slug>.json <spec_root>/diagrams/<slug>.html --json
   ```

   质量档次、参数以 archify Skill 为准。非零退出不得称为已交付。
4. **未安装**的唯一判定：找不到 `archify/SKILL.md`，或找不到可执行的 `bin/archify.mjs`（`node` 跑该文件失败也算）。此时在**对用户的完成摘要**里写明缺口，INDEX 用表格列关系兜底，保持空骨架或已有 HTML。不要生成假 HTML。
5. 禁止把「未安装」兜底用在 CLI 实际存在的环境。尤其禁止写「详细模式暂未生成图表」「后续可用 archify 生成」这类占位，以及只抄「同 slug JSON 候选存放在同目录」却不落文件。

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
