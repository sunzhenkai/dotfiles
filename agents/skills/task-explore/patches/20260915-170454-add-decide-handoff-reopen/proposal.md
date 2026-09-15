# 补 decide / handoff / reopen，交接只给 taskflow

- target: agents/skills/task-explore
- patch: 20260915-170454-add-decide-handoff-reopen
- risk: medium
- status: proposed

## Intent

按已确认的 grill 结论补闭环：`decide` 冻结方案；`handoff` 只交接给 `taskflow`（写交接段后委托 `taskflow-new`，driver 名为 `{task-name}-driver`，成功后才 archive）；`reopen` 把归档探索任务搬回 `ongoing/`。区分 **探索任务** 与 **taskflow 任务**。

非目标：不改 taskflow 正文；不把实现/apply 做进本 skill；不写仓库 `CONTEXT.md`。

## Conflict check

- `taskflow` 禁止第二份进度账：handoff 后交付进度只认 driver checkbox，探索任务归档，不再并行记完成度。
- `taskflow-new` 默认从描述推断 `{task}`：handoff **必须沿用探索任务 slug**，不得重推断。
- 与现有 `archive` 冲突检查顺序一致：目标存在则先停。

## Rationale

探索闭环缺出口与回入口。用户已确认最小三阶段及 handoff→taskflow 的具体行为，可写进共享 skill 并用契约测试锁住。

## Files

- `agents/skills/task-explore/SKILL.md`
- `agents/skills/task-explore/references/phase-decide.md`
- `agents/skills/task-explore/references/phase-handoff.md`
- `agents/skills/task-explore/references/phase-design.md` — 交接下一步改为 decide/handoff
- `agents/skills/task-explore/references/task-template.md`
- `agents/skills/task-explore/references/index-template.md`
- `agents/skills/task-explore/tests/test_task_explore_contract.py`

## Validation

- 应用前：`git apply --check --recount` 本 patch
- 应用后：`git diff --check -- agents/skills/task-explore`；`python3 -m pytest -q agents/skills/task-explore/tests`
