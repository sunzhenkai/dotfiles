# 把 explore / design 阶段详情拆到 references

- target: agents/skills/task-explore
- patch: 20260915-163832-split-heavy-phases
- risk: medium
- status: proposed

## Intent

把内容最长的 `explore`、`design` 阶段从 `SKILL.md` 挪到 `references/phase-*.md`。主文件只保留路由、绑定、索引与短步骤；进入对应阶段再加载该 phase。行为不变。

非目标：不改阶段语义、落点或门禁；不把短阶段（chat / resume / new / save / archive）拆出；不改 `design-template.md` 正文。

## Conflict check

- 引用保持一层：`SKILL.md` 链到 `phase-explore.md` / `phase-design.md`；`phase-design.md` 在落盘时再链 `design-template.md`。
- 与其它 Skill 职责无冲突。

## Rationale

`design` 约占主文件四分之一，`chat`/`resume` 默认路径用不到。拆出后默认加载更短，需要时再读对应 phase。

## Files

- `agents/skills/task-explore/SKILL.md` — 加载表 + explore/design 改为短入口
- `agents/skills/task-explore/references/phase-explore.md` — 新增
- `agents/skills/task-explore/references/phase-design.md` — 新增

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/task-explore`；frontmatter `name` 与目录名一致；新引用文件存在；`SKILL.md` 不再内嵌设计对比表/交接模板
