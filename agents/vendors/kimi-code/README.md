# Kimi Code CLI

[Kimi Code CLI](https://www.kimi.com/code/docs/en/) 终端 Agent 的安装与配置。

## 安装

```shell
dotf kimi-code -i
```

等价于官方脚本：

```shell
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
```

安装后二进制在 `~/.kimi-code/bin`（zsh `paths.zsh` 已自动加入 `PATH`），验证：

```shell
kimi --version
```

## 配置

```shell
dotf kimi-code -c
```

会把仓库内 `agents/vendors/kimi-code/config.toml` 安装到 `~/.kimi-code/config.toml`：

- 目标不存在 → 直接写入
- 目标已存在 → **跳过覆盖**（避免抹掉 `/login` 写入的凭证）

并同步 skills 到 `~/.kimi-code/skills/`、MCP 到 `~/.kimi-code/mcp.json`（commands 当前 skip）。

MCP HTTP 鉴权使用 `bearerTokenEnvVar`（如 `ZHIPU_API_KEY`），**不要**在 headers 里写 `${ZHIPU_API_KEY}`——Kimi 不会展开该占位符。

如需强制用仓库版本覆盖 config，先自行备份后删除 `~/.kimi-code/config.toml`，再执行 `dotf kimi-code -c`。

## 首次使用

```shell
cd your-project
kimi
```

在交互界面执行：

```
/login
```

可选择 Kimi Code OAuth，或填入 Platform API Key。

## tmux

`Prefix` + `v` 会在右侧打开 `kimi`。
