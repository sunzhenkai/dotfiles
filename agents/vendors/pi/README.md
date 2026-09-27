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
   - `npm:pi-mcp-adapter` — MCP 接入
   - `npm:pi-powerline-footer` — 可配置 status footer；仓库默认 `powerline.preset=full` + `cache_read.format=both`（上/下 token、缓存量与命中率）
   - `npm:pi-web-access` — 网页搜索 / 抓取 / PDF / 视频理解
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
