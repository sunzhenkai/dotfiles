# Result

- target: agents/skills/task-explore
- mode: update
- patch: 20260924-021500-add-plan-section
- risk: medium
- status: applied
- applied-at: 2026-09-24T02:30:00+08:00

## Validation

- `git apply --check --recount`: pass
- `git apply --recount`: pass
- `git diff --check -- agents/skills/task-explore`: pass
- target tests: `python3 agents/skills/task-explore/tests/test_task_explore_contract.py` → Ran 19 tests, OK（19/19）
- 落点核对：`TASK.md` 骨架现为 目标 / 非目标 / 现状 / **方案（步骤·阻塞点·坑）** / 进展 / 决策 / …
- privacy check: pass
- mode check: pass（纯 update，未新增自进化目录；未改历史 patches）

## Notes

用户明确批准并指示 apply。改动：

- `references/task-template.md`：新 `## 方案` 小节（步骤 / 阻塞点 / 坑）+ 头部说明「输入含现成方案时逐条登记该小节，不要只填目标」。
- `SKILL.md` `new` 第 3 步：登记上游（含 task-wizard）步骤级方案的硬约束。
- `references/phase-explore.md`：新增第 3 步「已有上游方案先当既有事实复核、不重问已知步骤」，原 5/6/7 顺延 6/7/8。

未触及 decide / handoff / archive / reopen / split、INDEX 模板、子任务机制。

## 未做

未 sync（`dotf agents -c`）、未 commit、未 push——待 B 完成后一并处理。
