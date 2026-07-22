# Pi coding agent

[Pi](https://pi.dev/) 终端 coding harness 的安装与配置。

## 安装

```shell
dotf pi -i
```

等价于官方脚本：

```shell
curl -fsSL https://pi.dev/install.sh | sh
```

包名：`@earendil-works/pi-coding-agent`（需 Node.js ≥ 22.19）。验证：

```shell
pi --version
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

## tmux

`Prefix` + `p` 会在右侧打开 `pi`。
