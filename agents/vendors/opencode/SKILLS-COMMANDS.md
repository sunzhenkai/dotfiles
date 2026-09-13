# Generated skills/commands — do not edit by hand

由仓库根目录 `agents/skills|commands` 经 `scripts/agents/sync.sh opencode` 生成，
安装到 **`~/.config/opencode/{skills,commands}/`**（home 真实目录，与其他 agent 一致）。

本目录 `agents/vendors/opencode/` 只保留手写内容（人格 `agents/`、`plugins.json`、`opencode.json` 模板等），
**不再**存放 sync 生成的 skills/commands，也**不再**整目录软链到 `~/.config/opencode`。

**本仓库不声明 LLM provider 与模型**；provider/模型请在本机配置或 OpenCode 登录流程中设置。

```shell
dotf opencode -c                       # 安装手写配置
scripts/modules/agents/sync.sh opencode  # 同步 skills
```
