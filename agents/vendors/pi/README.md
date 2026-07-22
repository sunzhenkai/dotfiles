# Pi coding agent

[Pi](https://pi.dev/) 终端 coding harness 的安装与配置。

## 安装

```shell
dotf pi -i
```

会安装：

1. Pi CLI（官方 `install.sh` / `@earendil-works/pi-coding-agent`，需 Node.js ≥ 22.19）
2. 默认扩展包（幂等，已装则跳过）：
   - `npm:@ogulcancelik/pi-goal` — 目标管理
   - `npm:@virdis/subagents` — 子代理委派

验证：

```shell
pi --version
pi list
```

## 配置

```shell
dotf pi -c
```

会把仓库内 `agents/vendors/pi/settings.json` 安装到 `~/.pi/agent/settings.json`：

- 目标不存在 → 直接写入
- 目标已存在 → **跳过覆盖**（避免抹掉 `/settings`、`/login` 本地状态）

并同步 skills 到 `~/.pi/agent/skills/`、commands → prompt templates 到 `~/.pi/agent/prompts/`。

Pi **无内置 MCP**；统一 `agents` sync 对 Pi MCP 记为 `skip`（与 Codex 同类降级）。

如需强制用仓库版本覆盖 settings，先自行备份后删除 `~/.pi/agent/settings.json`，再执行 `dotf pi -c`。

## 首次使用

```shell
cd your-project
pi
```

交互界面可用 `/model`、`/login` 选择 provider；自定义模型见 `~/.pi/agent/models.json`（[文档](https://pi.dev/docs/latest/)）。

## 踩坑：MiniMax 国内站 vs 海外站（401）

> **专题全文**（含 curl 排查、Codex/Pi/openviking）:  
> `repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`

Pi 内置两套 provider，**端点与环境变量不同**：

| Provider | 端点 | 环境变量 |
|----------|------|----------|
| `minimax`（海外） | `https://api.minimax.io/anthropic` | `MINIMAX_API_KEY` |
| `minimax-cn`（国内） | `https://api.minimaxi.com/anthropic` | `MINIMAX_CN_API_KEY` |

本机 key / Codex 走国内站。Pi 若默认 `minimax` → 稳定 `401 invalid api key`（key 没坏，区域错了）。

推荐（国内 key）：

1. `~/.pi/agent/settings.json`：`defaultProvider: "minimax-cn"`、`defaultModel: "MiniMax-M3"`
2. 鉴权任选：`export MINIMAX_CN_API_KEY="$MINIMAX_API_KEY"`，或 `auth.json` 里 `minimax-cn.key = "$MINIMAX_API_KEY"`，或 `/login` → MiniMax CN

```shell
pi --provider minimax-cn --model MiniMax-M3 -p --no-session --no-tools '只回复：ok'
```

## tmux

`Prefix` + `p` 会在右侧打开 `pi`。
