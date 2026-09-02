# Generated skills/commands — do not edit by hand

由仓库根目录 `agents/skills|commands` 经 `scripts/agents/sync.sh opencode` 生成，
安装到 **`~/.config/opencode/{skills,commands}/`**（home 真实目录，与其他 agent 一致）。

本目录 `agents/vendors/opencode/` 只保留手写内容（人格 `agents/`、`plugins.json`、`opencode.json` 模板等），
**不再**存放 sync 生成的 skills/commands，也**不再**整目录软链到 `~/.config/opencode`。

```shell
dotf opencode -c                 # 安装手写配置 + 托管 providers
dotf opencode -f                 # 列出可用 provider
dotf opencode -f company         # 切换默认 model（隐含 -c；全家仍保留）
opencode -m company/vanchin/deepseek-v4-pro-0813   # 仅本次会话
dotf agents -c --tool opencode   # 同步 skills + MCP
scripts/agents/sync.sh opencode
```

`dotf opencode -f` **不是**排他 overlay：六家 provider 始终写在 `opencode.json` 里，`/models` 可随时切。`-f` 只改默认 `model` 指针，记在 `~/.config/opencode/.dotf-profile`。

company 走 Chat Completions（`@ai-sdk/openai-compatible`），地址/密钥运行时读 `{env:COMPANY_BASE_URL}` / `{env:COMPANY_API_KEY}`，不入库。MiniMax / NativeX / 智谱 / SCNet 按 Responses（`@ai-sdk/openai`）；Kimi 官方是 Chat。

**MCP**：`~/.config/opencode/opencode.json` 的 `mcp` 字段由统一 `agents` sync 合并；安装托管 providers 时不会覆盖 `mcp`。
可选 `--also-repo-templates` 同步更新本目录仓库模板。请改 `agents/env/mcp/` 后重新 sync。

详见 `agents/env/README.md`。
