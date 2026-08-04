# Generated skills/commands — do not edit by hand

由仓库根目录 `agents/skills|commands` 经 `scripts/agents/sync.sh opencode` 生成，
安装到 **`~/.config/opencode/{skills,commands}/`**（home 真实目录，与其他 agent 一致）。

本目录 `agents/vendors/opencode/` 只保留手写内容（人格 `agents/`、`plugins.json`、`opencode.json` 模板等），
**不再**存放 sync 生成的 skills/commands，也**不再**整目录软链到 `~/.config/opencode`。

```shell
dotf opencode -c                 # 安装手写配置到 ~/.config/opencode
dotf agents -c --tool opencode   # 同步 skills + MCP
scripts/agents/sync.sh opencode
```

**MCP**：`~/.config/opencode/opencode.json` 的 `mcp` 字段由统一 `agents` sync 合并；
可选 `--also-repo-templates` 同步更新本目录仓库模板。请改 `agents/env/mcp/` 后重新 sync。

详见 `agents/env/README.md`。
