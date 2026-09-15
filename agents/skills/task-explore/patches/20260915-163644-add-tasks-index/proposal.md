# 增加 tasks/INDEX.md 派生索引

- target: agents/skills/task-explore
- patch: 20260915-163644-add-tasks-index
- risk: medium
- status: proposed

## Intent

在 `tasks/` 根维护 `INDEX.md`，供任务快速检索与查看（绑定列表、`resume`、归档查找）。单任务真相仍是各目录 `TASK.md`；索引是派生视图，必须在 `new` / `save` / `archive` 时同步，漂移则按目录重建。

非目标：不新增阶段、不引入脚本、不把进展日志写入索引、不改 `taskflow`、不把索引当成可手改的第二份账本。

## Conflict check

- 与「产物只写当前任务目录」冲突：改为允许唯一根级文件 `tasks/INDEX.md`。
- 与 `taskflow`「不写索引」不冲突：那是 OpenSpec checkbox 纪律，本 skill 已有独立 `tasks/` 工作区。
- 双源风险：用「TASK.md 为真相、INDEX 派生、漂移重建」约束。

## Rationale

长周期与归档按日期分目录后，只扫文件夹无法快速查看标题与一句话目标。一份短 Markdown 表对人和 agent 都可检索，且不改变阶段模型。

## Files

- `agents/skills/task-explore/SKILL.md` — 布局、绑定、new/save/archive/resume 同步索引
- `agents/skills/task-explore/references/index-template.md` — 索引骨架
- `agents/skills/task-explore/references/task-template.md` — save 时同步索引的一句说明

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/task-explore`；frontmatter `name` 与目录名一致；引用文件存在
