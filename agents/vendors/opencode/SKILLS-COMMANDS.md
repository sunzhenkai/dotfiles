# Generated skills/commands — do not edit by hand

由仓库根目录 `agents/skills|commands` 经 `scripts/agents/sync.sh opencode` 生成，
安装到 **`~/.config/opencode/{skills,commands}/`**（home 真实目录，与其他 agent 一致）。

本目录 `agents/vendors/opencode/` 只保留手写内容（人格 `agents/`、`plugins.json`、`opencode.json` 模板等），
**不再**存放 sync 生成的 skills/commands，也**不再**整目录软链到 `~/.config/opencode`。

```shell
dotf opencode -c                 # 安装手写配置 + 托管 providers
opencode -m kimi/kimi-for-coding               # 仅本次会话
opencode -m deepseek/deepseek-v4-pro           # 仅本次会话
dotf agents -c --tool opencode   # 同步 skills + MCP
scripts/agents/sync.sh opencode
```

五家 provider 写在 `opencode.json` 里，会话内用 `/models` 或 `opencode -m` 切换。`dotf` 不提供 LLM provider 切换入口。

MiniMax / 智谱 / SCNet 按 Responses（`@ai-sdk/openai`）；DeepSeek 官方也支持 Responses，但 OpenCode 内置定义走 OpenAI-compatible Chat；Kimi 官方是 Chat。

**MCP**：`~/.config/opencode/opencode.json` 的 `mcp` 字段由统一 `agents` sync 合并；安装托管 providers 时不会覆盖 `mcp`。
可选 `--also-repo-templates` 同步更新本目录仓库模板。请改 `agents/env/mcp/` 后重新 sync。

详见 `agents/env/README.md`。
