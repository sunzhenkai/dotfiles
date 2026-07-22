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

> **踩坑**：`@virdis/subagents@0.1.0` 自带 skill 的 frontmatter 为 `name: @virdis/subagents`，YAML 无法解析，交互启动会报 `[Skill conflicts]`。`dotf pi -i` 会在安装后把它幂等改成 `name: pi-subagents`。已装过的机器也可直接再跑一次 `dotf pi -i`。

## 配置

```shell
dotf pi -c
```

会把仓库模板应用到本机（**不软链**，避免 `/settings`、`/login` 写回仓库）：

| 文件 | 行为 |
|------|------|
| `settings.json` | 合并托管键（`defaultProvider` / `defaultModel` / telemetry 等）；保留本地 `packages`、`theme` 等 |
| `auth.json` | 仅当缺少 `minimax-cn` 时写入 `"key": "$MINIMAX_API_KEY"`（环境变量引用，无真实密钥） |

并同步 skills 到 `~/.pi/agent/skills/`、commands → prompt templates 到 `~/.pi/agent/prompts/`。

Pi **无内置 MCP**；统一 `agents` sync 对 Pi MCP 记为 `skip`（与 Codex 同类降级）。

仓库默认（可跨机器复用，与 Codex 同源约定）：

- `defaultProvider: "minimax-cn"`
- `defaultModel: "MiniMax-M3"`
- 鉴权读 `MINIMAX_API_KEY`（经 `auth.json` 展开；也可另设 `MINIMAX_CN_API_KEY`）

海外站：把 `defaultProvider` 改为 `minimax`，或启动后 `/model` 切换。不要把本机 AWS/Bedrock 密钥写进仓库。

## 首次使用

```shell
# shell / ~/.envrc（与 Codex 相同变量即可）
export MINIMAX_API_KEY="..."

cd your-project
pi
```

交互界面可用 `/model`、`/login` 选择 provider；自定义模型见 `~/.pi/agent/models.json`（[文档](https://pi.dev/docs/latest/)）。

## 踩坑：AWS_* 误选 Bedrock（403 UnrecognizedClientException）

环境里若有 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`（常用于 S3/其他服务），且 **未** 设置 `defaultProvider`，Pi 会自动选 `amazon-bedrock`，非 Bedrock 密钥会报：

```text
UnrecognizedClientException: 403: ...
```

本仓库通过 `defaultProvider=minimax-cn` 固定默认，避免被 AWS_* 带偏。需要 Bedrock 时再显式 `/model` 或改 settings。

## 踩坑：MiniMax 国内站 vs 海外站（401）

> **专题全文**（含 curl 排查、Codex/Pi/openviking）:  
> `repos/codeup/agent-data/knowledge/snippets/minimax-cn-vs-intl.md`

Pi 内置两套 provider，**端点与环境变量不同**：

| Provider | 端点 | 环境变量 / auth |
|----------|------|-----------------|
| `minimax`（海外） | `https://api.minimax.io/anthropic` | `MINIMAX_API_KEY` |
| `minimax-cn`（国内） | `https://api.minimaxi.com/anthropic` | `MINIMAX_CN_API_KEY`，或 `auth.json` 的 `$MINIMAX_API_KEY` |

本库约定：`MINIMAX_API_KEY` 为国内站 key（与 Codex 一致）。Pi 若落到海外 `minimax` → 常见 `401 invalid api key`（key 没坏，区域错了）。

```shell
pi --provider minimax-cn --model MiniMax-M3 -p --no-session --no-tools '只回复：ok'
# 或依赖 settings 默认：
pi -p --no-session --no-tools '只回复：ok'
```

## tmux

`Prefix` + `p` 会在右侧打开 `pi`。
