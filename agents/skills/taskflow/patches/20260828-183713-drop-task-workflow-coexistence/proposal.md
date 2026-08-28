# 去掉与已删除 task-workflow 的并存互斥描述

- target: agents/skills/taskflow
- patch: 20260828-183713-drop-task-workflow-coexistence
- risk: medium
- status: proposed

## Intent

不再把 taskflow 描述成与 task-workflow（taskctl + tasks/ 台账）并存但互斥的两套工作流。触发：task-workflow 已从共享 skills 移除。非目标：不改变 driver/checkbox/委托 openspec-* 的行为。

## Conflict check

与 one-driver-change 的「不建 tasks/ 台账」边界不冲突；删掉的 eval 只约束已不存在的另一套命令族。

## Rationale

task-workflow 移除后，并存互斥句会指向不存在的 skill，误导路由。不另建账本的约束仍由现有 one-driver-change 等 case 覆盖。

## Files

- `agents/skills/taskflow/SKILL.md`
- `agents/skills/taskflow/evals/cases.yaml`

## Validation

- 应用前：git apply --check --recount
- 应用后：frontmatter name=taskflow；不再出现 task-workflow；evals 仍为合法 YAML
