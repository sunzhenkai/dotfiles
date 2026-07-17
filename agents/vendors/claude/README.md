# Claude Desktop Configuration

此配置用于 Claude Desktop 连接到智谱AI API。

## 安装

1. 在 shell 配置中设置 `ZHIPU_API_KEY`（如 `~/.envrc`）。
2. 运行：`dotf -c claude` 或 `bash scripts/config.sh claude`。

## 配置文件

- `~/.claude/settings.json` — 主配置（安装时可用 `ZHIPU_API_KEY` 填充）
- `~/.claude.json` — 应用状态；MCP 也会合并到此
- `~/.claude/.mcp.json` — MCP（由 **agents/env** 生成）

## MCP 来源

仓库内 `claude/.mcp.json` 是 **agents/env 生成物 / 薄模板**，请勿手写多源漂移。

真相源：`agents/env/mcp/servers.yaml` + profiles。

本目录位于 `agents/vendors/claude/`（工具专属配置）。

```shell
dotf -c agents
scripts/agents/sync.sh claude
```

占位符保持 `${ZHIPU_API_KEY}`。skills/commands 仍由 `agents/` 同步。
