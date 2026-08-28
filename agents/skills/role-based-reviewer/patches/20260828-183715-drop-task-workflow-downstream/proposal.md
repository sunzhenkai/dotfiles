# 下游建议从 task-workflow 改为 taskflow

- target: agents/skills/role-based-reviewer
- patch: 20260828-183715-drop-task-workflow-downstream
- risk: medium
- status: proposed

## Intent

角色审查的「下一步建议」不再指向已删除的 task-workflow，改为现存的 taskflow。非目标：不改变只读门禁或角色分工。

## Conflict check

none：仅替换下游 skill 名，不扩大本 skill 职责。

## Rationale

指向不存在的 skill 会让审查收尾给出无法执行的建议。

## Files

- `agents/skills/role-based-reviewer/references/constraints.md`

## Validation

- 应用前：git apply --check --recount
- 应用后：constraints.md 不再出现 task-workflow
