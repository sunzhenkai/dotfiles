# 复杂路由钉死落点：任务描述逐字带方案正文，登记进 TASK.md「方案」小节

- target: agents/skills/task-wizard
- mode: update
- patch: 20260924-023000-pin-plan-handoff
- risk: medium
- status: proposed

## Intent

承接 A（task-explore 侧 20260924-021500-add-plan-section，已应用），补齐 wizard 侧交接契约。现状缺口：路由说明只写「把方案正文作为任务描述原文带入」，未点名落点，也未说 wizard 应止于「带入」；下游 task-explore `new` 若未收到完整正文，步骤 / 阻塞点 / 坑仍会丢。

改动两处：

1. 路由表「复杂」档衔接句 — 补「把本方案正文登记进 `TASK.md` 的「方案」小节（步骤 / 阻塞点 / 坑）」，把落点点名到位。
2. 要点最后一条 — 拆成两条：`task-explore` 一条把正文范围扩到「目标 / 事实 / 假设 / 步骤 / 阻塞点 / 坑 / 不做的事」并点名落点 + 边界（只作输入，不下新任务名、不重演探索）；OpenSpec / taskflow 一条保留原文。

非目标：不改三档信号、触发条件、输出模板、原则、边界；不改简单 / 中等档衔接。

## Conflict check

- 与 A 一致：A 已给 `TASK.md` 建「方案」小节并在 `new` 第 3 步要求登记上游方案；本条从上游侧把同一事实写硬，落点名称与 A 完全一致（「方案」小节、步骤 / 阻塞点 / 坑），不产生第二份定义。
- 与 task-explore 的 `new` 契约一致：task-explore 自己归纳 `{task-name}`（不追问），故本条写「不下新任务名」正是提醒 wizard 不要越权命名。
- task-wizard 无契约测试；本改动只动两行文本，不影响任何被钉字符串。

## Rationale

按 writing-for-agents：跨 skill 交接的可靠性取决于上游指针的措辞，落点必须点名到章节，否则「带入」无约束力。把范围写全（含事实 / 假设 / 不做的事）让下游拿到完整输入，避免只剩目标。

## Files

- agents/skills/task-wizard/SKILL.md — 复杂档衔接句补落点；末条要点拆为 task-explore / OpenSpec·taskflow 两条并写全正文范围

## Validation

- 应用前：`git apply --check --recount`（已通过）
- 应用后：`git diff --check`；frontmatter `name` 与目录名一致；渲染路由表确认复杂档含落点
