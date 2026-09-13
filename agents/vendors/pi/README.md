# Pi coding agent

[Pi](https://pi.dev/) 终端 coding harness 的安装与配置。**本仓库不声明 LLM provider、模型与密钥**；provider/模型选择请用 Pi 的 `/model`、`/login` 或本机 `~/.pi/agent/` 配置完成。

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
| `settings.json` | 合并托管键（telemetry 等布尔项）；保留本地 `packages`、`theme` 等 |

并同步 skills 到 `~/.pi/agent/skills/`、commands → prompt templates 到 `~/.pi/agent/prompts/`。

## 使用

```shell
cd your-project
pi
```

交互界面可用 `/model`、`/login` 选择 provider 与模型；自定义模型见 `~/.pi/agent/models.json`（[文档](https://pi.dev/docs/latest/)）。

## tmux

`Prefix` + `p` 会在右侧打开 `pi`。
