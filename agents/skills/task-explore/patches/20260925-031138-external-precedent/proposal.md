# explore 与 design 在定方案前做外部参照

- target: agents/skills/task-explore
- mode: update
- patch: 20260925-031138-external-precedent
- risk: high
- status: proposed

## Intent

`design` 在写对比表之前做一次外部参照。`explore` 只在未知会改方案走向时做，做完再问剩下的决策。`chat` 只读本仓代码与任务里已有笔记。同一问题、出处仍对得上则沿用已有条目；问题变了、出处对不上、或当时是未找到，再做一次。上游方案里的假设仍是假设。两处公开原文做法相反时，两条都是事实，对比表可以把它们当作两个方案。

非目标：不新造阶段；不另建词汇表；不改 grilling 的禁止项；不改 decide / handoff / archive；不把 skill 改成自进化；不自动 sync、commit 或 push。

## Conflict check

- `explore` 仍只委托 `grilling`，仍禁止 `grill-with-docs` / `domain-modeling`，仍禁止写仓库根 `CONTEXT.md` 与 `docs/adr/`。外部参照是查公开资料，不写那些落点。
- 上游方案不再整段当成事实。已对上出处的事实与已知步骤仍不重问；假设保持为假设。
- `chat` 原「可只读查代码与资料」收成只读本仓与任务笔记，避免默认阶段离开本仓。
- `new` 登记上游方案时补上事实与假设，避免外部参照在立项时丢掉。
- 公开段落不写 MCP 服务器名、内部 URL、私有仓库。

## Rationale

task-wizard 的复杂档会把外部参照写进方案正文。探索若把假设升成事实，或每个 `chat` 都去检索，就和已确认的契约相反。用户已确认该契约，并明确让本轮改 task-explore。对外读取会改变 agent 行为，风险为 high。

## Files

- agents/skills/task-explore/SKILL.md — `explore` / `design` 指向外部参照；`chat` 留在本仓；`new` 登记事实与假设
- agents/skills/task-explore/references/phase-explore.md — 假设保持为假设；会改方案走向的未知先做外部参照
- agents/skills/task-explore/references/phase-design.md — 写对比表之前做一次
- agents/skills/task-explore/references/external-precedent.md — 一次尝试、出处、写入与沿用已有条目
- agents/skills/task-explore/references/task-template.md — 方案小节增加事实与假设
- agents/skills/task-explore/references/design-template.md — 设计稿增加外部参照一节

## Validation

- 应用前：`git apply --check --recount`
- 应用后：`git diff --check`；`python -m unittest agents/skills/task-explore/tests/test_task_explore_contract.py`（或该目录下的 unittest）；frontmatter `name` 仍为 `task-explore`；grilling 禁止项仍在
