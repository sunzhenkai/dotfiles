# Result

- target: agents/skills/task-wizard
- mode: update
- patch: 20260924-023000-pin-plan-handoff
- risk: medium
- status: applied
- applied-at: 2026-09-24T02:35:00+08:00

## Validation

- `git apply --check --recount`: pass
- `git apply --recount`: pass
- `git diff --check -- agents/skills/task-wizard`: pass
- frontmatter `name: task-wizard` 与目录名一致；复杂档衔接句含 `TASK.md` 的「方案」小节落点
- privacy check: pass
- mode check: pass（纯 update）

## Notes

用户明确批准并指示 apply。改动：

- 路由表「复杂」档：衔接句补「把本方案正文登记进 `TASK.md` 的「方案」小节（步骤 / 阻塞点 / 坑）」。
- 要点末条拆为两条：`task-explore` 一条写全正文范围（目标 / 事实 / 假设 / 步骤 / 阻塞点 / 坑 / 不做的事）+ 落点 + 边界（只作输入、不下新任务名、不重演探索）；OpenSpec / taskflow 一条保留原文。

与 A（task-explore `20260924-021500-add-plan-section`）配套：A 建「方案」小节与 `new` 登记要求，B 从上游把同一落点写硬，名称一致。

## 未做

未 sync（`dotf agents -c`）、未 commit、未 push——与 A 一并处理。
