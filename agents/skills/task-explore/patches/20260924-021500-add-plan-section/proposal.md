# 新增「方案」小节：承接上游（含 task-wizard）步骤级方案

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-021500-add-plan-section
- risk: medium
- status: proposed

## Intent

现状缺口：task-wizard 路由到 task-explore 后，`TASK.md` 只有「目标」一个入口，`new` 只「填已知目标」；`task-template.md` 章节里没有步骤 / 阻塞点 / 坑的落点；`explore` 只问预期目标、成功标准、范围、约束、未知，不问步骤。于是上游 task-wizard 的步骤级产物（步骤、阻塞点、坑）在 `new` 时无处可写、在 `explore` 时不被问，直接丢失。

改动：给 `TASK.md` 增 `## 方案` 小节（步骤 / 阻塞点 / 坑），并把它接进 `new` 与 `explore`：

1. `references/task-template.md` — 骨架在「现状」与「进展」之间加 `## 方案`（步骤 / 阻塞点 / 坑）；头部说明补：输入含现成方案时把目标、步骤、阻塞点、坑逐条登记进该小节，不只填目标。
2. `SKILL.md` 的 `new` 第 3 步 — 明确「输入含现成方案（含上游 task-wizard 的步骤级方案）时，把步骤、阻塞点、坑一并登记进「方案」小节，不丢上游产物」。
3. `references/phase-explore.md` — 加一步：`TASK.md` 方案小节已有上游方案时先当既有事实复核，不重问已知步骤，grill 只针对未覆盖项；方案随后按 explore / design 结论更新回该小节。原第 5/6/7 步顺延为 6/7/8。

非目标：不动 `decide` / `handoff` / `archive` / `reopen` / `split`；不改 `INDEX.md` 模板；不改子任务机制与落点约束。

## Conflict check

- `tests/test_task_explore_contract.py`（19 项）不触及「方案」小节，已本地跑通；本改动新增文本不影响其断言的任何字符串。
- `phase-explore.md` 原有「只委托 `grilling`」「禁止 `grill-with-docs` / `domain-modeling`」契约保留；新增步骤只加复核既有方案，不引入新委托。
- 与 `phase-design.md` 不重叠：`设计` 是探索期产出方案稿，`方案` 小节是 `TASK.md` 内承接上游/已有方案的落点，二者互补（design 落 `design/`，小节落主文档）。
- 与 `decide` 的「决策」小节不重叠：决策冻结采纳方案，方案小节承载步骤细节与阻塞点 / 坑。

## Rationale

按 writing-for-agents：上游产物必须有单一落点，否则跨 skill 交接必然蒸发。`方案` 小节与目标 / 现状并列，是「已知」的一部分；grill 只拷问未覆盖项，避免重复劳动。改动局部、可逆、无脚本。

## Files

- agents/skills/task-explore/references/task-template.md — 加 `## 方案` 小节与头部说明
- agents/skills/task-explore/SKILL.md — `new` 第 3 步补登记上游方案
- agents/skills/task-explore/references/phase-explore.md — 加既有方案复核步骤并顺延编号

## Validation

- 应用前：`git apply --check --recount`（已通过）
- 应用后：`git diff --check`；`python3 agents/skills/task-explore/tests/test_task_explore_contract.py` 全绿；frontmatter `name` 与目录名一致
