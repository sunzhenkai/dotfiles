# MCP 生成物

`~/.config/opencode/opencode.json` 的 `mcp` 段由 `agents/env` 生成并合并。
仓库内 `agents/vendors/opencode/opencode.json` 为模板（可用 `--also-repo-templates` 更新）。

请编辑 `agents/env/mcp/` 后运行：

```shell
scripts/agents/sync.sh opencode
```

或：

```shell
scripts/agents/sync.sh opencode --env-only --profile browser
```
