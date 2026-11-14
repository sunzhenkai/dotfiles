# Pi coding agent

[Pi](https://pi.dev/) 终端 coding harness 的安装与配置。**本仓库不声明 LLM provider、模型与密钥**；provider/模型选择请用 Pi 的 `/model`、`/login` 或本机 `~/.pi/agent/` 配置完成。

## 安装

```shell
dotf pi -i
```

会安装：

1. Pi CLI（官方 `install.sh` / `@earendil-works/pi-coding-agent`，需 Node.js ≥ 22.19）
2. 默认扩展包（幂等，已装则跳过）：
   - `npm:pi-goal-x` — 目标管理（/goal 规划 + 独立完成度 auditor；2026-09-27 替换 @ogulcancelik/pi-goal，后者已入退役表）
   - `npm:pi-subagents` — 子代理委派
   - `npm:pi-powerline-footer` — 可配置 status footer；仓库默认 `powerline.preset=full` + `cache_read.format=both`（上/下 token、缓存量与命中率）
   - `npm:pi-web-access` — 网页搜索 / 抓取 / PDF / 视频理解
   - `npm:pi-web-search` — provider 原生网页搜索（Gemini / xAI / OpenAI / Anthropic / DeepSeek / OpenCode 等，按当前模型走厂商自带搜索）。与 `pi-web-access` 同名注册 `web_search`，Pi 按加载顺序后者覆盖，故排在它之后、只保留这里的实现
   - `npm:@juicesharp/rpiv-ask-user-question` — 结构化提问工具
   - `npm:pi-background-tasks` — 后台任务 / 委派
   - `npm:pi-simplify` — 改动代码的简洁性审查
   - `npm:billion-context` — 上下文压缩（长任务省 token；2026-09-27 新增）
   - `npm:@langfuse/pi-observability-plugin` — trace 上报 Langfuse（需自备 Langfuse 实例与密钥）
   - `npm:@juicesharp/rpiv-todo` — 模型侧 todo 覆盖层，/reload 与 compaction 后仍在（2026-09-27 重新收编，原冲突对象 pi-agent-extensions 已退役）
   - `npm:pi-lens` — LSP / linter / 类型检查实时反馈
   - `npm:@gotgenes/pi-permission-system` — 权限强制护栏
   - `npm:@plannotator/pi-extension` — 交互式 plan 评审
   - `npm:@dietrichgebert/ponytail` — skill：抑制过度设计的「懒惰资深工程师」模式
   - `npm:@ff-labs/pi-fff` — 模糊文件 / 内容搜索
   - `npm:pi-btw` — `/btw` 并行侧对话（不打断主线程的临时问答）
   - `npm:pi-memory` — 长期记忆 / 每日日志 / scratchpad，落 `~/.pi/agent/memory/`；`memory_search` 等语义检索需额外装 `qmd`（`npm i -g @tobilu/qmd`），不装也能用其余工具
   - `npm:@narumitw/pi-worktree` — `/worktree` 交互式 git worktree 建/切/删/清理；默认根目录 `~/.worktrees`，要跟随本工作区约定可写 `~/.pi/agent/pi-worktree.json` 的 `worktreeRoot`（如 `~/code/worktrees`）

MCP 用 Pi 自带的 `mcp` 内置扩展，不再装 `pi-mcp-adapter`：服务写在 `~/.pi/agent/mcp.json`（项目级 `.pi/mcp.json` 需信任后生效），工具名形如 `mcp__<server>__<tool>`。两者同时存在会抢 `/mcp`，内置的那个会被顶掉。

验证：

```shell
pi --version
pi list
```

## 配置

```shell
dotf pi -c
```

会把仓库模板应用到本机（**不软链**，避免 `/settings`、`/login` 写回仓库；`settings.json` 走纯 producer 的目录级 merge）：

| 文件 | 行为 |
|------|------|
| `settings.json` | `packages` 取仓库默认与本机已装的**并集**；托管键（telemetry 等布尔、`powerline`）由仓库强制；其余键（`defaultModel`、`defaultProvider`、`theme`、`lastChangelogVersion` 等）保留本机 |
| `extensions/exit.ts` | 本地扩展：注册 `/exit` 命令退出 pi（`ctx.shutdown()`） |
| `extensions/compact-output.ts` | 本地扩展：`bash`/`grep`/`find`/`ls`（含 pi-fff 的 `ffgrep`/`fffind`/`fff-multi-grep`）折叠态只显示一行摘要（`✓ 12 行`、`✗ exit 1 · 2.3s`），失败附末 3 行，展开（ctrl+o）看全文；只换 `renderResult`，不影响模型收到的输出 |
| 其余文件 | 按源逐字同步 |

运行时目录（`npm/`、`sessions/`、`auth.json`、`mcp*.json`、`models*.json`、`trust.json` 等）在 `modules.yaml` 的 `preserve` 中，**不被接管也不被清理**。

并同步 skills 到 `~/.pi/agent/skills/`、commands → prompt templates 到 `~/.pi/agent/prompts/`。

## 使用

```shell
cd your-project
pi
```

交互界面可用 `/model`、`/login` 选择 provider 与模型；自定义模型见 `~/.pi/agent/models.json`（[文档](https://pi.dev/docs/latest/)）。

## tmux

`Prefix` + `p` 会在右侧打开 `pi`。
