# 图表（archify）

镜像里的结构图、流程图、时序、数据流、状态机 **委托 skill `archify`**，不要用手绘 SVG/Mermaid 冒充 archify 产物，也不要把 archify 的 schema 或渲染器拷进本 Skill。

- 上游： [tt-a1i/archify](https://github.com/tt-a1i/archify)（入口 `archify/SKILL.md`）
- 安装：`dotf agents -c` 会按 `agents/skills-defaults.yaml` 装到 `~/.agents/skills`；环境还没有时也可手动 `npx skills add tt-a1i/archify -g -y --copy`
- 类型：`architecture` | `workflow` | `sequence` | `dataflow` | `lifecycle`
- 产物：自包含 HTML，放到 `<spec_root>/diagrams/<slug>.html`；JSON 候选与 HTML 同目录、同 slug（如 `<slug>.json`），便于下次差分
- `diagrams/INDEX.md`：图 / 类型 / 回答什么问题 / 链接

## 何时画

仅当表格说不清关系时：系统上下文、模块地图、部署/进程拓扑、切片主路径、对照实现差分、状态机。overview 与切片页用一句话说明「看哪张图」，不要在 Markdown 里再画一遍。

## 执行

1. 读本文件后 **加载并遵循已安装的 `archify` Skill**（不要用本文件代替其 schema/validate/deliver）。
2. 图中的组件、调用、状态必须能追溯到当前镜像的 SOURCE / 模块 / 切片；禁止为好看而发明拓扑。
3. 按 archify 做 `validate` 再 `deliver`；非零退出不得称为已交付。
4. 环境没有 archify 或 `node bin/archify.mjs`：在交付里写明缺口，用表格兜底，不要生成假 HTML。

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
