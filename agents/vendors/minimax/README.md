# MiniMax CLI

[MiniMax CLI](https://github.com/MiniMax-AI/cli)（`mmx`）媒体生成 CLI（text/image/video/speech/music）的安装与配置。

## 安装

```shell
dotf minimax -i
# 或随 agents 工具包
dotf agents -i
```

安装 npm 全局包 `mmx-cli`（bin: `mmx`）。

## 配置

```shell
dotf minimax -c
```

仅确保 `~/.mmx/` 目录就绪（可用 `MMX_CONFIG_DIR` 覆盖）。

**凭证不由 dotfiles 管理**：`~/.mmx/config.json` 由 `mmx auth login` 生成，含 OAuth/API key，
config 脚本绝不写入或覆盖该文件。

## 不参与共享同步

mmx 无 MCP 配置入口，也无 skills/commands 目录布局：

| 目标 | 状态 |
|------|------|
| Skills / Commands | 不同步（无此布局） |
| MCP | skip（见 `agents/env/manifest.yaml` 的 `unsupported.minimax`） |
