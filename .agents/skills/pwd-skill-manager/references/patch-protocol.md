# Patch Protocol（本仓增量）

记录格式、字段与状态规则以仓库内 `agents/skills/skill-upgrader/references/patch-protocol.md` 为准。本文件只列出套壳额外要求。

## 额外要求

1. `target` 必须写成 `agents/skills/<skill-name>`（仓库相对路径），不要用安装副本路径。
2. `change.patch` 必须能从仓库根被 `git apply --check --recount` 校验；`a/`、`b/` 后路径必须以 `agents/skills/<skill-name>/` 为前缀。
3. 只修改该目标 Skill 的生产内容；不包含历史 `patches/`、`.agents/skills/`、agent 镜像、绝对路径或临时文件。
4. `proposal.md` 的 `status` 保持 `proposed`；最终状态写入 `result.md`。
5. 已生成的 patch 目录是审计记录。proposed 且尚未应用时可修正 `change.patch`；一旦发生应用尝试，后续修复创建新 patch 目录。
