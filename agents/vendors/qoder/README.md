# Qoder CLI

[Qoder CLI](https://docs.qoder.com/) 终端 Agent 的安装与配置（**opt-in**：不随 `dotf agents -i` / `--all` 默认安装）。

## 安装

```shell
dotf qoder -i
```

## 配置

```shell
dotf qoder -c
```

确保 `~/.qoder/` 就绪；若尚无 `settings.json` 则写入骨架（已存在则跳过，避免覆盖本机状态）。

共享 skills / commands / MCP：

```shell
dotf agents -c --tool qoder
# 或
scripts/agents/sync.sh qoder
```

| 目标 | 路径 |
|------|------|
| Skills | `~/.qoder/skills/` |
| Commands | `~/.qoder/commands/` |
| MCP | merge `mcpServers` → `~/.qoder/settings.json` |

`agents/vendors/qoder/settings.json` 中的 `mcpServers` 段为 **agents/env 生成物**；请改 `agents/env/mcp/` 后重新 sync。
