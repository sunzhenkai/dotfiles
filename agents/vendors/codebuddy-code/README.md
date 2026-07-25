# CodeBuddy Code CLI

[CodeBuddy Code](https://www.codebuddy.ai/docs/cli/installation) 终端 Agent 的安装与配置（**opt-in**：不随 `dotf agents -i` / `--all` 默认安装）。

模块名 `codebuddy-code`，CLI 二进制为 `codebuddy`（`dotf codebuddy` 为别名）。

## 安装

```shell
dotf codebuddy-code -i
# 或
dotf codebuddy -i
```

## 配置

```shell
dotf codebuddy-code -c
```

确保 `~/.codebuddy/` 就绪。共享 skills / commands / MCP：

```shell
dotf agents -c --tool codebuddy-code
# 或
scripts/agents/sync.sh codebuddy-code
```

| 目标 | 路径 |
|------|------|
| Skills | `~/.codebuddy/skills/` |
| Commands | `~/.codebuddy/commands/` |
| MCP | `~/.codebuddy/.mcp.json` |

`agents/vendors/codebuddy-code/.mcp.json` 为 **agents/env 生成物**；请改 `agents/env/mcp/` 后重新 sync。
