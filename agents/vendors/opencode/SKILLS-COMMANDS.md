# Generated skills/commands — do not edit by hand

由仓库根目录 `agents/skills|commands` 经 `scripts/agents/sync.sh opencode` 生成，
安装到 **`~/.config/opencode/{skills,commands}/`**（home 真实目录，与其他 agent 一致）。

本目录 `agents/vendors/opencode/` 只保留手写内容（`opencode.json` 模板），
**不再**存放 sync 生成的 skills/commands，也**不再**整目录软链到 `~/.config/opencode`。

插件声明在 `opencode.json` 的 v2 原生键 `plugins`（`opencode plugin add` 的落点）；
`dotf` 部署时 `plugins` 数组按「vendor 在前、本机新增在后」求并集，两侧互不覆盖。

**本仓库不声明 LLM provider 与模型**；provider/模型请在本机配置或 OpenCode 登录流程中设置。

```shell
dotf opencode -c                       # 安装手写配置
scripts/modules/agents/sync.sh opencode  # 同步 skills
```
