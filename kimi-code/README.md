# Kimi Code CLI

[Kimi Code CLI](https://www.kimi.com/code/docs/en/) 终端 Agent 的安装与配置。

## 安装

```shell
dotf -i kimi-code
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
dotf -c kimi-code
```

会把仓库内 `kimi-code/config.toml` 安装到 `~/.kimi-code/config.toml`：

- 目标不存在 → 直接写入
- 目标已存在 → **跳过覆盖**（避免抹掉 `/login` 写入的凭证）

如需强制用仓库版本覆盖，先自行备份后删除 `~/.kimi-code/config.toml`，再执行 `dotf -c kimi-code`。

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
