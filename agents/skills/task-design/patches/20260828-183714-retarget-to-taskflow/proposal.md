# 把设计环节从已删除的 task-workflow 改挂到 taskflow

- target: agents/skills/task-design
- patch: 20260828-183714-retarget-to-taskflow
- risk: medium
- status: proposed

## Intent

task-design 不再依赖 task-workflow 的 resolve/status/task-* 命令。改为绑定 `{task}-driver`，产物写入 driver 的 design/ 目录，下游走 openspec-propose。非目标：不改设计文档骨架的章节结构，不把本 skill 改成 task-grill。

## Conflict check

与 taskflow / task-grill 职责不冲突：grill 做结构化访谈收敛，本 skill 仍只写设计文档。不再引用已删除的 task-workflow。

## Rationale

父工作流移除后，继续指令 task-new/task-explore/taskctl 会让 Agent 调用不存在的能力。改挂到现存的 taskflow 链路后，设计写法可继续复用。

## Files

- `agents/skills/task-design/SKILL.md`
- `agents/skills/task-design/agents/openai.yaml`
- `agents/skills/task-design/references/design-template.md`

## Validation

- 应用前：git apply --check --recount
- 应用后：frontmatter name=task-design；无 task-workflow / task-new 引用；{{slash:openspec-propose}} 仍在
